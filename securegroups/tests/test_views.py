from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from .. import models as gb_models, signals as gb_signals


class GroupsViewTestBase(TestCase):
    @classmethod
    def disconnect_signals(cls):
        m2m_changed.disconnect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

    @classmethod
    def connect_signals(cls):
        m2m_changed.connect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

    @classmethod
    def setUpTestData(cls):
        cls.disconnect_signals()

        tst2 = EveCorporationInfo.objects.create(
            corporation_id=2,
            corporation_name="Test Corp 2",
            corporation_ticker="TST2",
            member_count=100,
        )
        cls.corp_filter = gb_models.AltCorpFilter.objects.create(
            name="Corp Filter", description="Must be in TST2", alt_corp_id=tst2.pk
        )
        cls.smart_filter = gb_models.SmartFilter.objects.last()

        cls.group = Group.objects.create(name="SG_View_Test_Group")
        cls.group2 = Group.objects.create(name="SG_View_Test_Group_2")

        cls.smart_group = gb_models.SmartGroup.objects.create(
            group=cls.group, can_grace=True, auto_group=False, enabled=True
        )
        cls.smart_group.filters.add(cls.smart_filter)

        cls.smart_group2 = gb_models.SmartGroup.objects.create(
            group=cls.group2, can_grace=True, auto_group=False, enabled=True
        )
        cls.smart_group2.filters.add(cls.smart_filter)

        cls.user = AuthUtils.create_user("sg_view_user")
        main_char = AuthUtils.add_main_character_2(
            cls.user, "SG View Main", 9001, corp_id=1,
            corp_name="Test Corp 1", corp_ticker="TST1",
        )
        CharacterOwnership.objects.create(user=cls.user, character=main_char, owner_hash="sgview1")

        perm = AuthUtils.get_permission_by_name("securegroups.access_sec_group")
        cls.user.user_permissions.add(perm)
        cls.user.set_password("password")
        cls.user.save()

        cls.connect_signals()

    def setUp(self):
        self.client.login(username=self.user.username, password="password")

    def _make_grace(self, user, smart_group, smart_filter=None, days_ahead=5):
        if smart_filter is None:
            smart_filter = self.smart_filter
        return gb_models.GracePeriodRecord.objects.create(
            user=user,
            group=smart_group,
            grace_filter=smart_filter,
            expires=timezone.now() + timedelta(days=days_ahead),
        )


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class TestGroupsViewAccess(GroupsViewTestBase):
    def test_requires_permission(self):
        no_perm_user = AuthUtils.create_user("no_perm_user_view")
        no_perm_user.set_password("password")
        no_perm_user.save()
        self.client.login(username=no_perm_user.username, password="password")
        response = self.client.get(reverse("securegroups:groups"))
        self.assertEqual(response.status_code, 302)

    def test_returns_200_with_permission(self):
        response = self.client.get(reverse("securegroups:groups"))
        self.assertEqual(response.status_code, 200)

    def test_context_contains_groups(self):
        response = self.client.get(reverse("securegroups:groups"))
        self.assertIn("groups", response.context)

    def test_context_contains_pending_removals(self):
        response = self.client.get(reverse("securegroups:groups"))
        self.assertIn("pending_removals", response.context)


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class TestGroupsViewPendingRemovals(GroupsViewTestBase):
    def tearDown(self):
        gb_models.GracePeriodRecord.objects.filter(user=self.user).delete()

    def test_no_pending_removals_when_no_grace_records(self):
        response = self.client.get(reverse("securegroups:groups"))
        self.assertEqual(response.context["pending_removals"], [])

    def test_pending_removal_appears_when_member_has_grace_record(self):
        self.disconnect_signals()
        self.user.groups.add(self.group)
        self.connect_signals()
        self._make_grace(self.user, self.smart_group)

        response = self.client.get(reverse("securegroups:groups"))
        pending = response.context["pending_removals"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["group_name"], self.group.name)
        self.assertEqual(pending[0]["group_id"], self.group.id)
        self.assertIn("expires", pending[0])

        self.disconnect_signals()
        self.user.groups.remove(self.group)
        self.connect_signals()

    def test_pending_removals_deduplicated_per_group(self):
        """Multiple grace records for the same group should produce one pending_removals entry."""
        self.disconnect_signals()
        self.user.groups.add(self.group)
        self.connect_signals()

        corp2 = EveCorporationInfo.objects.create(
            corporation_id=99, corporation_name="Extra Corp", corporation_ticker="EXT", member_count=1,
        )
        #noqa: F841
        second_filter_obj = gb_models.AltCorpFilter.objects.create(
            name="Extra Filter", description="Must be in EXT", alt_corp_id=corp2.pk
        )
        second_smart_filter = gb_models.SmartFilter.objects.last()
        self.smart_group.filters.add(second_smart_filter)

        self._make_grace(self.user, self.smart_group, self.smart_filter, days_ahead=3)
        self._make_grace(self.user, self.smart_group, second_smart_filter, days_ahead=7)

        response = self.client.get(reverse("securegroups:groups"))
        pending = response.context["pending_removals"]
        group_entries = [p for p in pending if p["group_id"] == self.group.id]
        self.assertEqual(len(group_entries), 1)

        self.disconnect_signals()
        self.user.groups.remove(self.group)
        self.smart_group.filters.remove(second_smart_filter)
        self.connect_signals()

    def test_pending_removal_earliest_expiry_kept(self):
        """When a group has multiple grace records, the earliest expiry is shown."""
        self.disconnect_signals()
        self.user.groups.add(self.group)
        self.connect_signals()

        corp2 = EveCorporationInfo.objects.create(
            corporation_id=98, corporation_name="Expiry Corp", corporation_ticker="EXP", member_count=1,
        )
        #noqa: F841
        second_filter_obj = gb_models.AltCorpFilter.objects.create(
            name="Expiry Filter", description="Must be in EXP", alt_corp_id=corp2.pk
        )
        second_smart_filter = gb_models.SmartFilter.objects.last()
        self.smart_group.filters.add(second_smart_filter)

        early = timezone.now() + timedelta(days=2)
        late = timezone.now() + timedelta(days=10)
        gb_models.GracePeriodRecord.objects.create(
            user=self.user, group=self.smart_group, grace_filter=self.smart_filter, expires=early
        )
        gb_models.GracePeriodRecord.objects.create(
            user=self.user, group=self.smart_group, grace_filter=second_smart_filter, expires=late
        )

        response = self.client.get(reverse("securegroups:groups"))
        pending = response.context["pending_removals"]
        entry = next(p for p in pending if p["group_id"] == self.group.id)
        self.assertAlmostEqual(
            entry["expires"].timestamp(), early.timestamp(), delta=1
        )

        self.disconnect_signals()
        self.user.groups.remove(self.group)
        self.smart_group.filters.remove(second_smart_filter)
        self.connect_signals()

    def test_disabled_smart_group_excluded_from_pending_removals(self):
        self.disconnect_signals()
        self.user.groups.add(self.group)
        self.connect_signals()

        self.smart_group.enabled = False
        self.smart_group.save()
        self._make_grace(self.user, self.smart_group)

        response = self.client.get(reverse("securegroups:groups"))
        pending = response.context["pending_removals"]
        group_ids = [p["group_id"] for p in pending]
        self.assertNotIn(self.group.id, group_ids)

        self.smart_group.enabled = True
        self.smart_group.save()
        self.disconnect_signals()
        self.user.groups.remove(self.group)
        self.connect_signals()

    def test_grace_msg_set_on_group_with_pending_removal(self):
        """groups context entry has grace_msg when user is a member with a grace record."""
        self.disconnect_signals()
        self.user.groups.add(self.group)
        self.connect_signals()
        self._make_grace(self.user, self.smart_group)

        response = self.client.get(reverse("securegroups:groups"))
        groups = response.context["groups"]
        entry = next(g for g in groups if g["smart_group"].group == self.group)
        self.assertIsNotNone(entry["grace_msg"])

        self.disconnect_signals()
        self.user.groups.remove(self.group)
        self.connect_signals()

    def test_grace_msg_none_when_not_member(self):
        """grace_msg is None when user has a grace record but is not a group member."""
        self._make_grace(self.user, self.smart_group)
        response = self.client.get(reverse("securegroups:groups"))
        groups = response.context["groups"]
        entry = next((g for g in groups if g["smart_group"].group == self.group), None)
        if entry:
            self.assertIsNone(entry["grace_msg"])

    def test_pending_removal_not_shown_for_other_users_grace(self):
        other = AuthUtils.create_user("other_pending_user")
        other_char = AuthUtils.add_main_character_2(
            other, "Other Main", 9002, corp_id=1, corp_name="Test Corp 1", corp_ticker="TST1"
        )
        CharacterOwnership.objects.create(user=other, character=other_char, owner_hash="other1")
        self.disconnect_signals()
        other.groups.add(self.group)
        self.connect_signals()
        self._make_grace(other, self.smart_group)

        response = self.client.get(reverse("securegroups:groups"))
        pending = response.context["pending_removals"]
        self.assertEqual(len(pending), 0)

        self.disconnect_signals()
        other.groups.remove(self.group)
        self.connect_signals()
        gb_models.GracePeriodRecord.objects.filter(user=other).delete()


@override_settings(STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}, "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class TestShowCheckView(GroupsViewTestBase):
    def test_show_check_returns_200(self):
        response = self.client.get(
            reverse("securegroups:request_show", args=[self.group.id])
        )
        self.assertEqual(response.status_code, 200)

    def test_show_check_requires_permission(self):
        no_perm_user = AuthUtils.create_user("no_perm_show_check")
        no_perm_user.set_password("password")
        no_perm_user.save()
        self.client.login(username=no_perm_user.username, password="password")
        response = self.client.get(
            reverse("securegroups:request_show", args=[self.group.id])
        )
        self.assertEqual(response.status_code, 302)

    def test_show_check_failing_user_shows_ineligible(self):
        response = self.client.get(
            reverse("securegroups:request_show", args=[self.group.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ineligible")

    def test_run_check_and_show_check_render_without_error(self):
        for url_name in ("securegroups:request_check", "securegroups:request_show"):
            with self.subTest(url=url_name):
                response = self.client.get(reverse(url_name, args=[self.group.id]))
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, "Running Group Check Failed")
