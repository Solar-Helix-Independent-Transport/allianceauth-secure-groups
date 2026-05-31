from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.db.models.signals import m2m_changed
from django.test import TestCase
from django.utils import timezone

from allianceauth.authentication.models import CharacterOwnership
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.tests.auth_utils import AuthUtils

from .. import models as gb_models, signals as gb_signals


class TestGracePeriodRecord(TestCase):
    @classmethod
    def setUpTestData(cls):
        m2m_changed.disconnect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

        tst = EveCorporationInfo.objects.create(
            corporation_id=501, corporation_name="Grace Corp", corporation_ticker="GRC", member_count=1,
        )
        cls.corp_filter = gb_models.AltCorpFilter.objects.create(
            name="Grace Corp Filter", description="Must be in GRC", alt_corp_id=tst.pk
        )
        cls.smart_filter = gb_models.SmartFilter.objects.last()
        cls.group = Group.objects.create(name="Grace_Test_Group")
        cls.smart_group = gb_models.SmartGroup.objects.create(
            group=cls.group, can_grace=True, auto_group=False, enabled=True
        )
        cls.smart_group.filters.add(cls.smart_filter)

        cls.user = AuthUtils.create_user("grace_model_user")
        main = AuthUtils.add_main_character_2(
            cls.user, "Grace Main", 5001, corp_id=1, corp_name="Corp 1", corp_ticker="C1"
        )
        CharacterOwnership.objects.create(user=cls.user, character=main, owner_hash="grace_hash")

        m2m_changed.connect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

    def _make_grace(self, days):
        return gb_models.GracePeriodRecord.objects.create(
            user=self.user,
            group=self.smart_group,
            grace_filter=self.smart_filter,
            expires=timezone.now() + timedelta(days=days),
        )

    def test_is_expired_returns_true_when_past(self):
        record = self._make_grace(days=-1)
        self.assertTrue(record.is_expired())
        record.delete()

    def test_is_expired_returns_false_when_future(self):
        record = self._make_grace(days=5)
        self.assertFalse(record.is_expired())
        record.delete()

    def test_str_representation(self):
        record = self._make_grace(days=5)
        expected = f"{self.user} - {self.smart_group} - {self.smart_filter}"
        self.assertEqual(str(record), expected)
        record.delete()


class TestSmartGroupMethods(TestCase):
    @classmethod
    def setUpTestData(cls):
        m2m_changed.disconnect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

        tst2 = EveCorporationInfo.objects.create(
            corporation_id=502, corporation_name="Method Corp", corporation_ticker="MTH", member_count=1,
        )
        cls.corp_filter = gb_models.AltCorpFilter.objects.create(
            name="Method Filter", description="Must be in MTH", alt_corp_id=tst2.pk
        )
        cls.smart_filter = gb_models.SmartFilter.objects.last()
        cls.group = Group.objects.create(name="Method_Test_Group")
        cls.smart_group = gb_models.SmartGroup.objects.create(
            group=cls.group, can_grace=True, auto_group=False, enabled=True
        )
        cls.smart_group.filters.add(cls.smart_filter)

        # passing_user has an alt in MTH corp
        cls.passing_user = AuthUtils.create_user("method_pass_user")
        main = AuthUtils.add_main_character_2(
            cls.passing_user, "Pass Main", 5010, corp_id=1, corp_name="Corp 1", corp_ticker="C1"
        )
        CharacterOwnership.objects.create(user=cls.passing_user, character=main, owner_hash="pass_hash")
        alt = EveCharacter.objects.create(
            character_name="Pass Alt",
            character_id=5011,
            corporation_name="Method Corp",
            corporation_id=502,
            corporation_ticker="MTH",
        )
        CharacterOwnership.objects.create(user=cls.passing_user, character=alt, owner_hash="pass_alt_hash")

        # failing_user has no alt in MTH corp
        cls.failing_user = AuthUtils.create_user("method_fail_user")
        main2 = AuthUtils.add_main_character_2(
            cls.failing_user, "Fail Main", 5020, corp_id=1, corp_name="Corp 1", corp_ticker="C1"
        )
        CharacterOwnership.objects.create(user=cls.failing_user, character=main2, owner_hash="fail_hash")

        m2m_changed.connect(gb_signals.m2m_changed_user_groups, sender=User.groups.through)

    def test_run_checks_returns_pass_for_qualifying_user(self):
        results = self.smart_group.run_checks(self.passing_user)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["check"])

    def test_run_checks_returns_fail_for_non_qualifying_user(self):
        results = self.smart_group.run_checks(self.failing_user)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["check"])

    def test_run_checks_result_contains_expected_keys(self):
        results = self.smart_group.run_checks(self.passing_user)
        self.assertIn("name", results[0])
        self.assertIn("check", results[0])
        self.assertIn("filter", results[0])

    def test_run_check_on_user_returns_pass_for_qualifying_user(self):
        results = self.smart_group.run_check_on_user(self.passing_user)
        self.assertEqual(len(results), 1)
        self.assertTrue(results[0]["check"])

    def test_run_check_on_user_returns_fail_for_non_qualifying_user(self):
        results = self.smart_group.run_check_on_user(self.failing_user)
        self.assertEqual(len(results), 1)
        self.assertFalse(results[0]["check"])

    def test_run_check_on_user_result_contains_message(self):
        results = self.smart_group.run_check_on_user(self.passing_user)
        self.assertIn("message", results[0])

    def test_process_checks_all_pass(self):
        checks = [{"check": True}, {"check": True}]
        self.assertTrue(self.smart_group.process_checks(checks))

    def test_process_checks_any_fail(self):
        checks = [{"check": True}, {"check": False}]
        self.assertFalse(self.smart_group.process_checks(checks))

    def test_process_checks_all_fail(self):
        checks = [{"check": False}, {"check": False}]
        self.assertFalse(self.smart_group.process_checks(checks))

    def test_process_checks_empty(self):
        self.assertTrue(self.smart_group.process_checks([]))

    def test_check_user_pass(self):
        self.assertTrue(self.smart_group.check_user(self.passing_user))

    def test_check_user_fail(self):
        self.assertFalse(self.smart_group.check_user(self.failing_user))
