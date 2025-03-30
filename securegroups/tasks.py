import json
import logging
from datetime import timedelta

import requests
from celery import chain, shared_task

from django.contrib.auth.models import User
from django.core.cache import cache
from django.utils import timezone

from allianceauth.notifications import notify

from . import app_settings
from .models import (
    GracePeriodRecord, GroupUpdateWebhook, PendingNotification, SmartGroup,
)

if app_settings.discord_bot_active():
    import aadiscordbot
    from aadiscordbot.utils.auth import get_discord_user_id
    from discord import Color, Embed

logger = logging.getLogger(__name__)


def create_pending_notification(user, message, group, filter, remove=False):
    logger.info(
        f"Adding {group} to {user} pending notifications for {message}"
    )
    PendingNotification.objects.create(
        user=user,
        filter=filter,
        group=group,
        message=message,
        removal=remove
    )


def send_discord_dm(user, title, message, color):
    if app_settings.discord_bot_active():
        try:
            e = Embed(
                title=title,
                description=message,
                color=color
            )
            aadiscordbot.tasks.send_message(
                user_id=get_discord_user_id(user),
                embed=e
            )
            logger.info(
                f"sent discord ping to {user} - {message}"
            )
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
                    {
                        "content": f"{update}\n{grp.extra_message}"
                    }
                ),
            )
            logger.debug(
                f"Got status code {r.status_code} after sending ping"
            )
            try:
                r.raise_for_status()
            except Exception as e:
                logger.error(e, exc_info=1)


CACHE_TIMEOUT = 60 * 60 * 4


def get_failure_key(sg_id, user_id) -> str:
    return f"SG-CHECK-{sg_id}-{user_id}-FAILURE"


def set_failure(sg_id, user_id):
    cache.set(get_failure_key(sg_id, user_id), True, CACHE_TIMEOUT)


def get_failure(sg_id, user_id) -> bool:
    return cache.get(get_failure_key(sg_id, user_id), False)


def clear_failure(sg_id, user_id):
    cache.delete(get_failure_key(sg_id, user_id))


def process_grace(smart_group, all_users):
    output = {}

    _all_graced_members = GracePeriodRecord.objects.filter(
        group=smart_group, user__username__in=all_users
    )

    if smart_group.can_grace:
        for gm in _all_graced_members:
            if gm.user.username not in output:
                output[gm.user.username] = {}
            output[gm.user.username][gm.grace_filter] = gm

    return output


def process_users_in_bulk(smart_group, users):
    bulk_checks = {}
    filters = smart_group.filters.all()
    for f in filters:
        try:
            bulk_checks[f.id] = f.filter_object.audit_filter(users)
        except Exception:
            pass
    return bulk_checks


def process_user(filter, user, bulk_checks=None):
    _c = {
        "name": filter.filter_object.description,
        "filter": filter
    }
    try:
        _c["check"] = bulk_checks[filter.id][user.id]['check']
        _c["message"] = bulk_checks[filter.id][user.id]['message']
    except Exception:
        try:
            _c["check"] = filter.filter_object.process_filter(user)
            _c["message"] = ""
        except Exception:
            _c["check"] = False
            _c["message"] = "Filter Failed"
    return _c


def check_user_has_main(smart_group, user, fake_run):
    try:
        assert user.profile.main_character is not None
        return True
    except Exception:  # no main character kickeroo!
        if not fake_run:
            user.groups.remove(smart_group.group)
            # remove user
            if smart_group.notify_on_remove:
                message = f'{user.username} - Removed from "{smart_group.group.name}" No Main'
                notify(
                    user,
                    f'Auto Group Removal "{smart_group.group.name}"',
                    message,
                    "warning"
                )
            logger.info(message)
        return False


@shared_task
def run_smart_group_update(sg_id, can_grace=False, fake_run=False):
    # Run Smart Group and add/remove members as required
    smart_group = SmartGroup.objects.get(id=sg_id)
    if smart_group.can_grace:
        can_grace = smart_group.can_grace

    logger.info(
        f"Starting '{smart_group.group.name}' Checks. {'(Fake)' if fake_run else ''}"
    )

    group = smart_group.group
    all_users = group.user_set.all().values_list("username", flat=True)
    all_graced_members = process_grace(smart_group, all_users)

    # who are we going to process?
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
        "profile",
        "profile__main_character"
    ).distinct()

    bulk_checks = process_users_in_bulk(smart_group, users)

    count = 0
    added = 0
    removed = 0
    pending_removals = 0
    for u in users:
        if not check_user_has_main(smart_group, u, fake_run):
            removed += 1
            continue
        checks = []

        filters = smart_group.filters.all()
        for f in filters:
            _c = process_user(f, u, bulk_checks)
            checks.append(_c)

        if len(checks) == 0:
            logging.warning("No checks to process on group?")
            break

        count += 1
        check_pass = True

        reasons = []
        for c in checks:
            if not c.get("check", False):
                check_pass = False
                reasons.append(f'{c.get("name", "")}  {c.get("message", "")}')

        if check_pass:
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
                                all_graced_members[u.username][filter_name].delete()
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

    message = "**{group_name}**: Checked {checked} Members, Approved {approved}, Added {added}, Removed {removed} (Pending Removals {pending_removal}){fake}".format(
        checked=count,
        added=added,
        removed=removed,
        # number_users=len(all_users),
        group_name=group.name,
        approved=group.user_set.all().count(),
        pending_removal=pending_removals,
        fake=" (Fake)" if fake_run else "",
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
        logger.warning(message)
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
        logger.warning(message)
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
