from django.contrib.auth.models import User
from django.test import TestCase

from allianceauth.services.modules.discord.models import DiscordUser
from allianceauth.services.modules.discourse.models import DiscourseUser
from allianceauth.services.modules.ips4.models import Ips4User
from allianceauth.services.modules.mumble.models import MumbleUser
from allianceauth.services.modules.openfire.models import OpenfireUser
from allianceauth.services.modules.phpbb3.models import Phpbb3User
from allianceauth.services.modules.smf.models import SmfUser
from allianceauth.services.modules.teamspeak3.models import Teamspeak3User
from allianceauth.services.modules.xenforo.models import XenforoUser
from allianceauth.tests.auth_utils import AuthUtils

from ..service_filters import (
    DiscordActiveFilter, DiscourseActiveFilter, Ips4ActiveFilter,
    MumbleActiveFilter, OpenfireActiveFilter, Phpbb3ActiveFilter,
    SmfActiveFilter, Teamspeak3ActiveFilter, XenforoActiveFilter,
)


def _make_filter(cls, name="test"):
    return cls.objects.create(name=name, description=name)


def _user_qs(*users):
    return User.objects.filter(pk__in=[u.pk for u in users])


class TestDiscordActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("discord_user_with")
        cls.user_without = AuthUtils.create_user("discord_user_without")
        DiscordUser.objects.create(
            user=cls.user_with, uid=111, username="TestUser", discriminator="0001"
        )

    def setUp(self):
        self.f = _make_filter(DiscordActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestMumbleActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("mumble_user_with")
        cls.user_without = AuthUtils.create_user("mumble_user_without")
        MumbleUser(user=cls.user_with, username="mumble_test", pwhash="x").save()

    def setUp(self):
        self.f = _make_filter(MumbleActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestTeamspeak3ActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("ts3_user_with")
        cls.user_without = AuthUtils.create_user("ts3_user_without")
        Teamspeak3User.objects.create(user=cls.user_with, uid="abc123", perm_key="key123")

    def setUp(self):
        self.f = _make_filter(Teamspeak3ActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestOpenfireActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("openfire_user_with")
        cls.user_without = AuthUtils.create_user("openfire_user_without")
        OpenfireUser.objects.create(user=cls.user_with, username="openfire_test")

    def setUp(self):
        self.f = _make_filter(OpenfireActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestPhpbb3ActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("phpbb3_user_with")
        cls.user_without = AuthUtils.create_user("phpbb3_user_without")
        Phpbb3User.objects.create(user=cls.user_with, username="phpbb3_test")

    def setUp(self):
        self.f = _make_filter(Phpbb3ActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestSmfActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("smf_user_with")
        cls.user_without = AuthUtils.create_user("smf_user_without")
        SmfUser.objects.create(user=cls.user_with, username="smf_test")

    def setUp(self):
        self.f = _make_filter(SmfActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestXenforoActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("xenforo_user_with")
        cls.user_without = AuthUtils.create_user("xenforo_user_without")
        XenforoUser.objects.create(user=cls.user_with, username="xenforo_test")

    def setUp(self):
        self.f = _make_filter(XenforoActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestDiscourseActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_enabled = AuthUtils.create_user("discourse_user_enabled")
        cls.user_disabled = AuthUtils.create_user("discourse_user_disabled")
        cls.user_without = AuthUtils.create_user("discourse_user_without")
        DiscourseUser.objects.create(user=cls.user_enabled, enabled=True)
        DiscourseUser.objects.create(user=cls.user_disabled, enabled=False)

    def setUp(self):
        self.f = _make_filter(DiscourseActiveFilter)

    def test_process_filter_with_enabled_account(self):
        self.assertTrue(self.f.process_filter(self.user_enabled))

    def test_process_filter_with_disabled_account(self):
        self.assertFalse(self.f.process_filter(self.user_disabled))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(
            _user_qs(self.user_enabled, self.user_disabled, self.user_without)
        )
        self.assertTrue(result[self.user_enabled.id]["check"])
        self.assertFalse(result[self.user_disabled.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])


class TestIps4ActiveFilter(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_with = AuthUtils.create_user("ips4_user_with")
        cls.user_without = AuthUtils.create_user("ips4_user_without")
        Ips4User.objects.create(user=cls.user_with, username="ips4_test", id="42")

    def setUp(self):
        self.f = _make_filter(Ips4ActiveFilter)

    def test_process_filter_with_account(self):
        self.assertTrue(self.f.process_filter(self.user_with))

    def test_process_filter_without_account(self):
        self.assertFalse(self.f.process_filter(self.user_without))

    def test_audit_filter(self):
        result = self.f.audit_filter(_user_qs(self.user_with, self.user_without))
        self.assertTrue(result[self.user_with.id]["check"])
        self.assertFalse(result[self.user_without.id]["check"])
