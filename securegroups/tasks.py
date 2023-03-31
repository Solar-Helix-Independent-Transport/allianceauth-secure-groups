import logging

from celery import shared_task, chain
from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models.expressions import Col
from django.utils import timezone
from datetime import timedelta
from allianceauth.notifications import notify
from .models import GroupUpdateWebhook, PendingNotification, SmartGroup, GracePeriodRecord
from . import app_settings
import requests
import json

if app_settings.discord_bot_active():
    import aadiscordbot
    from discord import Embed, Color

logger = logging.getLogger(__name__)


def create_pending_notification(user, message, group, filter, remove=False):
    logger.debug(
        "Adding {} to pending notifications for {}".format(user, group))
    PendingNotification.objects.create(
        user=user, filter=filter, group=group, message=message, removal=remove)


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
    for u in users:
        try:
            assert u.profile.main_character is not None
        except:  # no main character kickeroo!
            removed += 1
            if not fake_run:
                u.groups.remove(group)
                # remove user
                if smart_group.notify_on_remove:
                    message = '{} - Removed from "{}" No Main'.format(
                        u.username, group.name
                    )
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
                        if smart_group.notify_on_add:
                            if app_settings.discord_bot_active():
                                send_discord_dm(
                                    u,
                                    f'Auto Group Added "{group.name}"',
                                    message,
                                    Color.blue()
                                )
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
                                if smart_group.notify_on_remove:
                                    create_pending_notification(
                                        u,
                                        c.get("message", ""),
                                        smart_group,
                                        c.get("filter"),
                                        remove=True
                                    )
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
                                    if smart_group.notify_on_grace:
                                        create_pending_notification(
                                            u,
                                            c.get("message", ""),
                                            smart_group,
                                            c.get("filter")
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
                                if smart_group.notify_on_grace:
                                    create_pending_notification(
                                        u,
                                        c.get("message", ""),
                                        smart_group,
                                        c.get("filter")
                                    )
                        else:
                            remove = True
                            continue
                if remove:
                    removed += 1
                    if not fake_run:
                        u.groups.remove(group)
                elif grace:
                    pending_removals += 1
                    if not fake_run:
                        if get_failure(sg_id, u.id):
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

    sig_list.append(notify_users.si())

    chain(sig_list).apply_async(priority=5)


def notify_grace():
    users, mdls = PendingNotification.get_grace_notifications()
    for u, msgs in users.items():
        groups = set()
        messages = set()
        for m in msgs:
            groups.add(m.group.group.name)
            messages.add(f"{m.filter.filter_object.description}: {m.message}")

        message = (
            '{} - Pending Removal from these Groups:\n```\n- {}\n```\nDue to failing:\n```\n- {}\n```'.format(
                u.profile.main_character.character_name,
                "\n- ".join(list(groups)),
                "\n- ".join(list(messages)),
            )
        )
        notify(
            u,
            "Pending Removal",
            message,
            "warning"
        )
        if app_settings.discord_bot_active():
            send_discord_dm(
                u,
                "Pending Removal",
                message,
                Color.orange()
            )
    mdls.update(notified=True)


def notify_removal():
    users, mdls = PendingNotification.get_kick_notifications()
    for u, msgs in users.items():
        groups = set()
        messages = set()
        for m in msgs:
            groups.add(m.group.group.name)
            messages.add(f"{m.filter.filter_object.description}: {m.message}")

        message = (
            '{} - Removed from these Groups:\n```\n- {}\n```\nDue to failing:\n```\n- {}\n```'.format(
                u.profile.main_character.character_name,
                "\n- ".join(list(groups)),
                "\n- ".join(list(messages)),
            )
        )
        notify(
            u,
            "Group Removal",
            message,
            "warning"
        )
        if app_settings.discord_bot_active():
            send_discord_dm(
                u,
                "Group Removal",
                message,
                Color.red()
            )
    mdls.update(notified=True)


@shared_task
def notify_users():

    notify_grace()
    notify_removal()

    PendingNotification.objects.filter(notified=True).delete()
