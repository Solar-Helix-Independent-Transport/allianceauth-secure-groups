from django.test import TestCase, RequestFactory
from django.urls import reverse
from django.core.cache import cache
from allianceauth.tests.auth_utils import AuthUtils
from allianceauth.eveonline.models import EveCharacter, EveCorporationInfo, EveAllianceInfo
from allianceauth.authentication.models import CharacterOwnership
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .. import filter as gb_filters
from .. import models as gb_models
from .. import tasks as gb_tasks
from django.contrib.auth.models import Group


class TestGroupBotFilters(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.factory = RequestFactory()
        EveCharacter.objects.all().delete()
        EveCharacter.objects.all().delete()
        User.objects.all().delete()
        CharacterOwnership.objects.all().delete()
        gb_models.SmartGroup.objects.all().delete()
        userids = range(1, 11)

        cls.test_group, _ = Group.objects.update_or_create(name="Test_Group")
        tst2 = EveCorporationInfo.objects.create(
            corporation_id=2,
            corporation_name="Test Corp 2",
            corporation_ticker="TST2",
            member_count=100,
        )
        cls.corp_filter = gb_models.AltCorpFilter.objects.create(
            name="Test Corp 2 Alt", description="Have Alt in TST2", alt_corp_id=tst2.pk
        )
        _sf = gb_models.SmartFilter.objects.all().last()
        cls.test_s_group = gb_models.SmartGroup.objects.create(
            group=cls.test_group,
            can_grace=True,
            auto_group=False,
            include_in_updates=True,
        )
        cls.test_s_group.filters.add(_sf)

        users = []
        characters = []
        for uid in userids:
            user = AuthUtils.create_user(f"User_{uid}")
            main_char = AuthUtils.add_main_character_2(
                user,
                f"Main {uid}",
                uid,
                corp_id=1,
                corp_name="Test Corp 1",
                corp_ticker="TST1",
            )
            CharacterOwnership.objects.create(
                user=user, character=main_char, owner_hash=f"main{uid}"
            )

            characters.append(main_char)
            users.append(user)

        # add some extra characters to users in 2 corps/alliance
        for uid in range(0, 5):  # test corp 2
            character = EveCharacter.objects.create(
                character_name=f"Alt {uid}",
                character_id=11 + uid,
                corporation_name="Test Corp 2",
                corporation_id=2,
                corporation_ticker="TST2",
            )
            CharacterOwnership.objects.create(
                character=character, user=users[uid], owner_hash=f"ownalt{11+uid}"
            )
            characters.append(character)

        for uid in range(5, 10):  # Test alliance 1
            character = EveCharacter.objects.create(
                character_name=f"Alt {uid}",
                character_id=11 + uid,
                corporation_name="Test Corp 3",
                corporation_id=3,
                corporation_ticker="TST3",
                alliance_id=1,
                alliance_name="Test Alliance 1",
                alliance_ticker="TSTA1",
            )
            CharacterOwnership.objects.create(
                character=character, user=users[uid], owner_hash=f"ownalt{11+uid}"
            )
            characters.append(character)
        _alli = EveAllianceInfo.objects.create(alliance_id=1,
                                               alliance_name="Test Alliance 1",
                                               alliance_ticker="TSTA1",
                                               executor_corp_id=3)
        cls.alli_filter = gb_models.AltAllianceFilter.objects.create(
            name="Test Alli 1 Alt", description="Have Alt in TSTA2", alt_alli_id=_alli.pk
        )
        cls.grp_filter = gb_models.UserInGroupFilter.objects.create(
            name="Test Group", description="Test Group", group=cls.test_group
        )

    def test_user_alt_corp(self):
        users = {}
        for user in User.objects.all():
            print
            users[user.pk] = None

        tests = {}
        for k, u in users.items():
            tests[k] = gb_filters.check_alt_corp_on_account(
                User.objects.get(pk=k), 2)

        self.assertTrue(tests[1])
        self.assertTrue(tests[2])
        self.assertTrue(tests[3])
        self.assertTrue(tests[4])
        self.assertTrue(tests[5])
        self.assertFalse(tests[6])
        self.assertFalse(tests[7])
        self.assertFalse(tests[8])
        self.assertFalse(tests[9])
        self.assertFalse(tests[10])

    def test_user_alt_corp_audit(self):
        users = []
        for user in User.objects.all():
            print
            users.append(user.pk)

        tests = self.corp_filter.audit_filter(
            User.objects.filter(id__in=users))

        self.assertTrue(tests[1]['check'])
        self.assertTrue(tests[2]['check'])
        self.assertTrue(tests[3]['check'])
        self.assertTrue(tests[4]['check'])
        self.assertTrue(tests[5]['check'])
        self.assertFalse(tests[6]['check'])
        self.assertFalse(tests[7]['check'])
        self.assertFalse(tests[8]['check'])
        self.assertFalse(tests[9]['check'])
        self.assertFalse(tests[10]['check'])

    def test_user_alt_alli(self):
        users = {}
        for user in User.objects.all():
            users[user.pk] = None

        tests = {}
        for k, u in users.items():
            tests[k] = self.alli_filter.process_filter(
                User.objects.get(pk=k))

        self.assertFalse(tests[1])
        self.assertFalse(tests[2])
        self.assertFalse(tests[3])
        self.assertFalse(tests[4])
        self.assertFalse(tests[5])
        self.assertTrue(tests[6])
        self.assertTrue(tests[7])
        self.assertTrue(tests[8])
        self.assertTrue(tests[9])
        self.assertTrue(tests[10])

    def test_user_alt_alli_audit(self):
        users = []
        for user in User.objects.all():
            users.append(user.pk)

        tests = self.alli_filter.audit_filter(
            User.objects.filter(id__in=users))

        self.assertFalse(tests[1]['check'])
        self.assertFalse(tests[2]['check'])
        self.assertFalse(tests[3]['check'])
        self.assertFalse(tests[4]['check'])
        self.assertFalse(tests[5]['check'])
        self.assertTrue(tests[6]['check'])
        self.assertTrue(tests[7]['check'])
        self.assertTrue(tests[8]['check'])
        self.assertTrue(tests[9]['check'])
        self.assertTrue(tests[10]['check'])

    def test_user_group_filter(self):
        User.objects.get(id=1).groups.add(self.test_group)
        User.objects.get(id=7).groups.add(self.test_group)

        users = {}
        for user in User.objects.all():
            users[user.pk] = None

        tests = {}
        for k, u in users.items():
            tests[k] = self.grp_filter.process_filter(
                User.objects.get(pk=k))

        self.assertTrue(tests[1])
        self.assertFalse(tests[2])
        self.assertFalse(tests[3])
        self.assertFalse(tests[4])
        self.assertFalse(tests[5])
        self.assertFalse(tests[6])
        self.assertTrue(tests[7])
        self.assertFalse(tests[8])
        self.assertFalse(tests[9])
        self.assertFalse(tests[10])

    def test_user_group_filter_audit(self):
        User.objects.get(id=1).groups.add(self.test_group)
        User.objects.get(id=7).groups.add(self.test_group)

        users = []
        for user in User.objects.all():
            users.append(user.pk)

        tests = self.grp_filter.audit_filter(
            User.objects.filter(pk__in=users))

        self.assertTrue(tests[1]['check'])
        self.assertFalse(tests[2]['check'])
        self.assertFalse(tests[3]['check'])
        self.assertFalse(tests[4]['check'])
        self.assertFalse(tests[5]['check'])
        self.assertFalse(tests[6]['check'])
        self.assertTrue(tests[7]['check'])
        self.assertFalse(tests[8]['check'])
        self.assertFalse(tests[9]['check'])
        self.assertFalse(tests[10]['check'])

    def test_generic_smart_group_task(self):
        cache.clear()
        reset_time = timezone.now() - timedelta(days=5)
        User.objects.get(id=1).groups.add(self.test_group)
        User.objects.get(id=10).groups.add(self.test_group)
        User.objects.get(id=9).groups.add(self.test_group)
        User.objects.get(id=7).groups.add(self.test_group)
        # users all good
        self.assertTrue(self.test_group in User.objects.get(id=1).groups.all())
        self.assertTrue(
            self.test_group in User.objects.get(id=10).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=9).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=7).groups.all())

        # first pass test hit the pre notify
        gb_tasks.run_smart_group_update(self.test_s_group.id)

        self.assertTrue(self.test_group in User.objects.get(id=1).groups.all())
        self.assertTrue(
            self.test_group in User.objects.get(id=10).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=9).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=7).groups.all())
        self.assertEquals(
            gb_models.GracePeriodRecord.objects.all().count(), 0)  # not notified

        # the data should have been updated by now so try again
        gb_tasks.run_smart_group_update(self.test_s_group.id)

        self.assertTrue(self.test_group in User.objects.get(id=1).groups.all())
        self.assertTrue(
            self.test_group in User.objects.get(id=10).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=9).groups.all())
        self.assertTrue(self.test_group in User.objects.get(id=7).groups.all())
        self.assertEquals(
            gb_models.GracePeriodRecord.objects.all().count(), 3)  # now notified

        gb_models.GracePeriodRecord.objects.all().update(
            expires=reset_time)  # reset he grace to remove

        gb_tasks.run_smart_group_update(self.test_s_group.id)

        # purge the users
        self.assertTrue(self.test_group in User.objects.get(id=1).groups.all())
        self.assertFalse(
            self.test_group in User.objects.get(id=10).groups.all())
        self.assertFalse(
            self.test_group in User.objects.get(id=9).groups.all())
        self.assertFalse(
            self.test_group in User.objects.get(id=7).groups.all())

        self.assertEquals(gb_models.GracePeriodRecord.objects.all().count(), 0)

    def test_fail_view(self):
        user = User.objects.get(id=7)
        permission = AuthUtils.get_permission_by_name(
            "securegroups.access_sec_group")
        user.user_permissions.add(permission)
        user.set_password("1234")
        user.save()
        user.refresh_from_db()
        self.assertTrue(user.has_perm("securegroups.access_sec_group"))
        self.assertTrue(self.client.login(
            username=user.username, password="1234"))
        response = self.client.get(
            reverse("securegroups:request_check", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ineligible")
        self.assertNotContains(response, "Running Group Check Failed")

    def test_pass_view(self):
        user = User.objects.get(id=1)
        permission = AuthUtils.get_permission_by_name(
            "securegroups.access_sec_group")
        user.set_password("1234")
        user.save()
        user.user_permissions.add(permission)
        user.refresh_from_db()
        self.assertTrue(user.has_perm("securegroups.access_sec_group"))
        self.assertTrue(self.client.login(
            username=user.username, password="1234"))
        response = self.client.get(
            reverse("securegroups:request_check", args=[1]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Join Group")
        self.assertNotContains(response, "Running Group Check Failed")

    def test_no_perm_view(self):
        user = User.objects.get(id=5)
        self.assertFalse(user.has_perm("securegroups.access_sec_group"))
        self.client.login(username=user.username)
        response = self.client.get(
            reverse("securegroups:request_check", args=[1]))
        self.assertEqual(response.status_code, 302)
