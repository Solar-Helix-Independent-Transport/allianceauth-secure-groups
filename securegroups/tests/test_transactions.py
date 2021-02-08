from django.test import TransactionTestCase, RequestFactory
from django.urls import reverse
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo
from allianceauth.authentication.models import CharacterOwnership
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .. import filter as gb_filters
from .. import models as gb_models
from .. import tasks as gb_tasks
from django.contrib.auth.models import Group


class TestGroupBotTransactions(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        cls.factory = RequestFactory()
        EveCharacter.objects.all().delete()
        EveCharacter.objects.all().delete()
        User.objects.all().delete()
        CharacterOwnership.objects.all().delete()
        gb_models.SmartGroup.objects.all().delete()

        cls.test_group, _ = Group.objects.update_or_create(name="Test_Group_2")
        cls.test_group3, _ = Group.objects.update_or_create(
            name="Test_Group_3")
        cls.test_group4, _ = Group.objects.update_or_create(
            name="Test_Group_4")
        cls.tst4 = EveCorporationInfo.objects.create(
            corporation_id=4,
            corporation_name="Test Corp 4",
            corporation_ticker="TST4",
            member_count=100,
        )
        tst2 = EveCorporationInfo.objects.create(
            corporation_id=2,
            corporation_name="Test Corp 2",
            corporation_ticker="TST2",
            member_count=100,
        )
        cls.user = AuthUtils.create_user(f"User_transactions_test")
        main_char = AuthUtils.add_main_character_2(
            cls.user,
            f"Main Trans",
            cls.user.id,
            corp_id=1,
            corp_name="Test Corp 1",
            corp_ticker="TST1",
        )
        CharacterOwnership.objects.create(
            user=cls.user, character=main_char, owner_hash="main123"
        )

        character = EveCharacter.objects.create(
            character_name=f"Alt 9999",
            character_id=9999,
            corporation_name="Test Corp 2",
            corporation_id=2,
            corporation_ticker="TST2",
        )
        CharacterOwnership.objects.create(
            character=character, user=cls.user, owner_hash="ownalt321"
        )
        cls._sf = gb_models.AltCorpFilter.objects.create(
            name="Test Corp 2 Alt", description="Have Alt in TST2", alt_corp_id=tst2.pk
        )
        _sf = gb_models.SmartFilter.objects.all().last()
        test_s_group = gb_models.SmartGroup.objects.create(
            group=cls.test_group4,
            can_grace=True,
            auto_group=False,
            include_in_updates=True,
        )
        test_s_group.filters.add(_sf)
        cls.user.groups.add(cls.test_group4)

    def test_cant_join_smart_group_invalidly(self):
        self.user.groups.add(self.test_group)
        self.assertTrue(self.test_group in self.user.groups.all())
        self.assertTrue(self.test_group4 in self.user.groups.all())
        self.user.groups.remove(self.test_group)

        self.user.groups.add(self.test_group, self.test_group3)
        self.assertTrue(self.test_group in self.user.groups.all())
        self.assertTrue(self.test_group3 in self.user.groups.all())
        self.assertTrue(self.test_group4 in self.user.groups.all())
        self.user.groups.remove(self.test_group)
        self.user.groups.remove(self.test_group3)
        gb_models.AltCorpFilter.objects.create(
            name="Test Corp 4 Alt", description="Have Alt in TST4", alt_corp_id=self.tst4.pk
        )

        _sf = gb_models.SmartFilter.objects.all().last()

        test_s_group = gb_models.SmartGroup.objects.create(
            group=self.test_group,
            can_grace=True,
            auto_group=False,
            include_in_updates=True,
        )
        test_s_group.filters.add(_sf)
        self.user.groups.add(self.test_group, self.test_group3)
        self.assertFalse(self.test_group in self.user.groups.all())
        self.assertTrue(self.test_group3 in self.user.groups.all())
        self.assertTrue(self.test_group4 in self.user.groups.all())
