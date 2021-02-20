import logging
from django.contrib.auth.models import User, Group

logger = logging.getLogger(__name__)


def check_alt_alli_on_account(user: User, alt_alli_id, exempt_corps=False, exempt_allis=False):
    try:
        if exempt_allis:
            if user.profile.main_character.alliance_id in exempt_alli:
                return True

        if exempt_corps:
            if user.profile.main_character.corporation_id in exempt_corps:
                return True

        character_list = user.character_ownerships.all().select_related("character")
        character_count = character_list.filter(
            character__alliance_id=alt_alli_id
        ).count()
        if character_count > 0:
            return True
        else:
            return False
    except Exception:
        return False


def check_alt_corp_on_account(user: User, alt_corp_id, exempt_corps=False, exempt_allis=False):
    # logger.debug("Checking {0} for alt in corp {1}".format(character_id, alt_corp_id))
    try:
        character_list = user.character_ownerships.all().select_related("character")

        if exempt_allis:
            if user.profile.main_character.alliance_id in exempt_alli:
                return True

        if exempt_corps:
            if user.profile.main_character.corporation_id in exempt_corps:
                return True

        character_count = character_list.filter(
            character__corporation_id=alt_corp_id
        ).count()
        if character_count > 0:
            return True
        else:
            return False
    except Exception:
        return False


def check_group_on_account(user: User, group: Group, exempt_corps=False, exempt_allis=False):
    try:
        if exempt_allis:
            if user.profile.main_character.alliance_id in exempt_alli:
                return True

        if exempt_corps:
            if user.profile.main_character.corporation_id in exempt_corps:
                return True

        if group in user.groups.all():
            return True
        else:
            return False
    except Exception:
        return False
