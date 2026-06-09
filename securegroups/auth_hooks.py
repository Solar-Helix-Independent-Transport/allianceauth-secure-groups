from django.apps import apps as django_apps
from django.utils.translation import gettext_lazy as _

from allianceauth import hooks
from allianceauth.groupmanagement.managers import GroupManager
from allianceauth.services.hooks import MenuItemHook, UrlHook

from . import app_settings, urls
from .models import (
    AltAllianceFilter, AltCorpFilter, AltFactionFilter, FilterExpression,
    GracePeriodRecord, UserInGroupFilter,
)
from .service_filters import (
    DiscordActiveFilter, DiscourseActiveFilter, Ips4ActiveFilter,
    MumbleActiveFilter, OpenfireActiveFilter, Phpbb3ActiveFilter,
    SmfActiveFilter, Teamspeak3ActiveFilter, XenforoActiveFilter,
)

_SERVICE_FILTERS = [
    ("allianceauth.services.modules.discord",    DiscordActiveFilter),
    ("allianceauth.services.modules.mumble",     MumbleActiveFilter),
    ("allianceauth.services.modules.teamspeak3", Teamspeak3ActiveFilter),
    ("allianceauth.services.modules.openfire",   OpenfireActiveFilter),
    ("allianceauth.services.modules.phpbb3",     Phpbb3ActiveFilter),
    ("allianceauth.services.modules.smf",        SmfActiveFilter),
    ("allianceauth.services.modules.xenforo",    XenforoActiveFilter),
    ("allianceauth.services.modules.discourse",  DiscourseActiveFilter),
    ("allianceauth.services.modules.ips4",       Ips4ActiveFilter),
]


@hooks.register("url_hook")
def register_url():
    return UrlHook(urls, "securegroups", r"^securegroups/")


class GroupMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            "Secure Groups",
            "fa-solid fa-user-lock",
            "securegroups:groups",
            45,
            navactive=["securegroups:groups"],
        )

    def render(self, request):
        if request.user.has_perm("securegroups.access_sec_group"):
            _cnt = (
                GracePeriodRecord.objects.filter(
                    user=request.user, group__auto_group=False
                )
                .values("group_id")
                .distinct()
                .count()
            )
            if _cnt > 0:
                self.count = _cnt
            return MenuItemHook.render(self, request)
        else:
            return ""


@hooks.register("menu_item_hook")
def register_menu():
    return GroupMenu()


class GroupManagementMenuItem(MenuItemHook):
    """This class ensures only authorized users will see the menu entry"""

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            text=_("Secure Group Audit"),
            classes="fa-solid fa-user-check",
            url_name="securegroups:audit_list",
            order=55,
            navactive=[
                "securegroups:audit",
                "securegroups:audit_check",
                "securegroups:audit_list",
            ],
        )

    def render(self, request):
        mgr = GroupManager.can_manage_groups(request.user)
        adt = request.user.has_perm("securegroups.audit_sec_group")
        if mgr and adt:
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_audit():
    return GroupManagementMenuItem()


@hooks.register("secure_group_filters")
def filters():
    service_filters = [
        cls for app, cls in _SERVICE_FILTERS
        if django_apps.is_installed(app)
    ]
    return [
        AltAllianceFilter, AltCorpFilter, UserInGroupFilter,
        FilterExpression, AltFactionFilter,
        *service_filters,
    ]


@hooks.register("discord_cogs_hook")
def register_cogs():
    return app_settings.DISCORD_BOT_COGS
