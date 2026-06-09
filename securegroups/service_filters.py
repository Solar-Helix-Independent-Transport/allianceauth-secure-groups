from collections import defaultdict

from django.contrib.auth.models import User

from .models import FilterBase


class DiscordActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has Discord"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.discord
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.discord.models import (
                DiscordUser,
            )
            active_ids = set(
                DiscordUser.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class MumbleActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has Mumble"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.mumble
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.mumble.models import MumbleUser
            active_ids = set(
                MumbleUser.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class Teamspeak3ActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has TeamSpeak3"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.teamspeak3
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.teamspeak3.models import (
                Teamspeak3User,
            )
            active_ids = set(
                Teamspeak3User.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class OpenfireActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has Openfire"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.openfire
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.openfire.models import (
                OpenfireUser,
            )
            active_ids = set(
                OpenfireUser.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class Phpbb3ActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has phpBB3"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.phpbb3
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.phpbb3.models import Phpbb3User
            active_ids = set(
                Phpbb3User.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class SmfActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has SMF"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.smf
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.smf.models import SmfUser
            active_ids = set(
                SmfUser.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class XenforoActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has XenForo"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.xenforo
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.xenforo.models import (
                XenforoUser,
            )
            active_ids = set(
                XenforoUser.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class DiscourseActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has Discourse"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            return user.discourse.enabled
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.discourse.models import (
                DiscourseUser,
            )
            active_ids = set(
                DiscourseUser.objects.filter(user__in=users, enabled=True)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output


class Ips4ActiveFilter(FilterBase):
    class Meta:
        verbose_name = "Smart Filter: User Has IPS4"
        verbose_name_plural = verbose_name

    def process_filter(self, user: User):
        try:
            _ = user.ips4
            return True
        except Exception:
            return False

    def audit_filter(self, users):
        try:
            from allianceauth.services.modules.ips4.models import Ips4User
            active_ids = set(
                Ips4User.objects.filter(user__in=users)
                .values_list("user_id", flat=True)
            )
        except Exception:
            active_ids = set()
        output = defaultdict(lambda: {"message": "", "check": False})
        for u in users:
            output[u.id] = {"message": "", "check": u.id in active_ids}
        return output
