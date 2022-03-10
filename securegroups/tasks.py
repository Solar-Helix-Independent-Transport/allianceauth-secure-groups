import logging

from celery import shared_task, chain
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models.expressions import Col
from django.utils import timezone
from datetime import timedelta
from allianceauth.notifications import notify
from .models import GroupUpdateWebhook, SmartGroup, GracePeriodRecord
from . import app_settings
import requests
import json

if app_settings.discord_bot_active():
    import aadiscordbot
    from discord import Embed, Color

logger = logging.getLogger(__name__)


def send_discord_dm(user, title, message, color):
    if app_settings.discord_bot_active():
        try:
            e = Embed(title=title,
                      description=message,
                      color=color)
            aadiscordbot.tasks.send_message(
                user_id=user.discord.uid,
                embed=e)
            logger.debug("sent discord ping to {}".format(user))
        except Exception as e:
            logger.error(e, exc_info=1)
            pass


def send_update_to_webhook(group, update):
    group_hook = GroupUpdateWebhook.objects.filter(
        group_id=group, enabled=True)
    if group_hook.exists():
        for grp in group_hook:
            custom_headers = {"Content-Type": "application/json"}
            r = requests.post(
                grp.webhook,
                headers=custom_headers,
                data=json.dumps(
                    {"content": "{}\n{}".format(update, grp.extra_message)}
                ),
            )
            logger.debug("Got status code %s after sending ping" %
                         r.status_code)
            try:
                r.raise_for_status()
            except Exception as e:
                logger.error(e, exc_info=1)


CACHE_TIMEOUT = 60*60*4


def get_failure_key(sg_id, user_id) -> str:
    return f"SG-CHECK-{sg_id}-{user_id}-FAILURE"


def set_failure(sg_id, user_id):
    cache.set(get_failure_key(sg_id, user_id), True, CACHE_TIMEOUT)


def get_failure(sg_id, user_id) -> bool:
    return cache.get(get_failure_key(sg_id, user_id), False)


def clear_failure(sg_id, user_id):
    cache.delete(get_failure_key(sg_id, user_id))


@shared_task
def run_smart_group_update(sg_id, can_grace=False, fake_run=False):
    # Run Smart Group and add/remove members as required
    smart_group = SmartGroup.objects.get(id=sg_id)
    if smart_group.can_grace:
        can_grace = smart_group.can_grace
    logger.info(
        "Starting '{}' Checks. {}".format(
            smart_group.group.name, "(Fake)" if fake_run else ""
        )
    )

    group = smart_group.group
    all_users = group.user_set.all().values_list("username", flat=True)
    all_graced_members = {}
    _all_graced_members = GracePeriodRecord.objects.filter(
        group=smart_group, user__username__in=all_users
    )
    if smart_group.can_grace:
        for gm in _all_graced_members:
            if gm.user.username not in all_graced_members:
                all_graced_members[gm.user.username] = {}
            all_graced_members[gm.user.username][gm.grace_filter] = gm

    if smart_group.auto_group:
        states = group.authgroup.states.all()
        if states.count() > 0:
            users = User.objects.filter(
                profile__state__in=states)
        else:
            users = User.objects.filter(
                profile__main_character__isnull=False)
    else:
        users = group.user_set.all()

    users = users.select_related(
        "profile", "profile__main_character").distinct()

    bulk_checks = {}
    filters = smart_group.filters.all()
    for f in filters:
        try:
            bulk_checks[f.id] = f.filter_object.audit_filter(users)
        except Exception as e:
            pass

    count = 0
    added = 0
    removed = 0
    pending_removals = 0
    # print(all_graced_members)
    for u in users:
        try:
            assert u.profile.main_character is not None
        except:  # no main character kickeroo
            removed += 1
            if not fake_run:
                u.groups.remove(group)
                # remove user
                message = '{} - Removed from "{}" No Main'.format(
                    u.username, group.name
                )
                send_discord_dm(u, "Removed From Group", message, Color.red())
                notify(
                    u, f'Auto Group Removal "{group.name}"', message, "warning")
                logger.info(message)
            continue

        checks = []
        for f in filters:
            _c = {
                "name": f.filter_object.description,
                "filter": f
            }
            try:
                _c["check"] = bulk_checks[f.id][u.id]['check']
                _c["message"] = bulk_checks[f.id][u.id]['message']
            except Exception as e:
                try:
                    _c["check"] = f.filter_object.process_filter(u)
                    _c["message"] = ""
                except Exception as e:
                    _c["check"] = False
                    _c["message"] = "Filter Failed"
            checks.append(_c)
        if len(checks) == 0:
            break

        count += 1
        out = True
        reasons = []
        for c in checks:
            if not c.get("check", False):
                out = False
                reasons.append(f'{c.get("name", "")}  {c.get("message", "")}')

        if out:
            if u.username in all_graced_members:
                if not fake_run:
                    GracePeriodRecord.objects.filter(
                        user=u, group=smart_group).delete()
            if smart_group.auto_group:
                if u.username not in all_users:
                    # Add user
                    added += 1
                    if not fake_run:
                        u.groups.add(group)
                        message = f"{u.profile.main_character.character_name} - Passed the requirements for {group.name}"
                        notify(
                            u, f'Auto Group Added "{group.name}"', message, "info")
                        logger.info(message)

        else:
            if u.username in all_users:
                remove = False
                grace = False
                was_graced = False
                for c in checks:
                    filter_name = c.get("filter")
                    grace_days = filter_name.grace_period
                    expires = timezone.now() + timedelta(days=grace_days)
                    if u.username in all_graced_members:
                        if filter_name in all_graced_members.get(u.username, {}):
                            if all_graced_members[u.username][filter_name].is_expired():
                                all_graced_members[u.username][filter_name].delete(
                                )
                                remove = True
                                continue
                            else:
                                was_graced = True
                        elif not c.get("check", False):
                            if can_grace and grace_days > 0:
                                grace = True
                                if not fake_run and get_failure(sg_id, u.id):
                                    GracePeriodRecord.objects.create(
                                        user=u,
                                        group=smart_group,
                                        grace_filter=filter_name,
                                        expires=expires,
                                    )
                            else:
                                remove = True
                                continue
                    elif not c.get("check", False):
                        if can_grace and grace_days > 0:
                            grace = True
                            if not fake_run and get_failure(sg_id, u.id):
                                GracePeriodRecord.objects.create(
                                    user=u,
                                    group=smart_group,
                                    grace_filter=filter_name,
                                    expires=expires,
                                )
                        else:
                            remove = True
                            continue
                if remove:
                    removed += 1
                    if not fake_run:
                        u.groups.remove(group)
                        # remove user
                        message = '{} - Removed from "{}" due to failing:\n```{}\n```'.format(
                            u.profile.main_character.character_name,
                            group.name,
                            "\n``` ```".join(reasons),
                        )
                        send_discord_dm(
                            u, "Removed From Group", message, color=0xe74c3c)
                        notify(
                            u, f'Auto Group Removal "{group.name}"', message, "warning"
                        )
                        logger.info(message)
                elif grace:
                    pending_removals += 1
                    if not fake_run:
                        if get_failure(sg_id, u.id):
                            message = (
                                '{} - Pending Removal from "{}" due to failing:\n```{}\n```'.format(
                                    u.profile.main_character.character_name,
                                    group.name,
                                    "\n``` ```".join(reasons),
                                )
                            )
                            send_discord_dm(
                                u, "Group Removal Pending", message, color=0xe67e22)
                            notify(
                                u,
                                f'Auto Group Removal Pending "{group.name}"',
                                message,
                                "warning",
                            )
                            logger.info(message)
                            clear_failure(sg_id, u.id)
                        else:
                            set_failure(sg_id, u.id)
                elif was_graced:
                    pending_removals += 1

    message = "**{4}**: Checked {0} Members, Approved {5}, Added {1}, Removed {2}(Pending Removals {6}) {7}".format(
        count,
        added,
        removed,
        len(all_users),
        group.name,
        group.user_set.all().count(),
        pending_removals,
        "(Fake)" if fake_run else "",
    )

    logger.info(message)

    send_update_to_webhook(group, message)

    # cleanup graces
    GracePeriodRecord.objects.filter(
        group=smart_group
    ).exclude(
        user__in=group.user_set.all()
    ).delete()

    return message


@shared_task
def run_smart_groups(only_hidden=False):

    groups = SmartGroup.objects.filter(enabled=True)

    if only_hidden:
        groups = groups.filter(auto_group=True)

    sig_list = []
    for g in groups:
        sig_list.append(run_smart_group_update.si(g.id))

    chain(sig_list).apply_async(priority=5)
