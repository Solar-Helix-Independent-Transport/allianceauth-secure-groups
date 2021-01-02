import datetime
from django.db.models import QuerySet, Q
from math import floor
from dateutil.relativedelta import relativedelta
from django.db.models.functions import Coalesce
from django.db.models import Sum
import logging

logger = logging.getLogger(__name__)


def check_alt_alli_on_account(user, alt_alli_id):
    try:
        character_list = user.character_ownerships.all().select_related("character")
        character_count = character_list.filter(
            character__alliance_id=alt_alli_id
        ).count()
        if character_count > 0:
            return True
        else:
            return False
    except:
        return False


def check_alt_corp_on_account(user, alt_corp_id, exempt_alliances=False):
    # logger.debug("Checking {0} for alt in corp {1}".format(character_id, alt_corp_id))
    try:
        character_list = user.character_ownerships.all().select_related("character")

        if exempt_alliances:
            exempt_alli = character_list.filter(
                character__alliance_id__in=exempt_alliances
            ).count()
            if exempt_alli > 0:
                return True

        character_count = character_list.filter(
            character__corporation_id=alt_corp_id
        ).count()
        if character_count > 0:
            return True
        else:
            return False
    except:
        return False
