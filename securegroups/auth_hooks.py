from . import urls
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook
from .models import AltCorpFilter, AltAllianceFilter, UserInGroupFilter
from allianceauth.groupmanagement.managers import GroupManager
from django.utils.translation import ugettext_lazy as _
from .models import GracePeriodRecord


@hooks.register("url_hook")
def register_url():
    return UrlHook(urls, "securegroups", r"^securegroups/")


class GroupMenu(MenuItemHook):
    def __init__(self):
        MenuItemHook.__init__(
            self,
            "Secure Groups",
            "fas fa-user-lock fa-fw",
            "securegroups:groups",
            45,
            navactive=["securegroups:groups"],
        )

    def render(self, request):
        if request.user.has_perm("securegroups.access_sec_group"):
            _cnt = GracePeriodRecord.objects.filter(
                user=request.user,
                group__auto_group=False).values('group_id').distinct().count()
            if _cnt > 0:
                self.count = _cnt
            return MenuItemHook.render(self, request)
        else:
            return ""


@hooks.register("menu_item_hook")
def register_menu():
    return GroupMenu()


class GroupManagementMenuItem(MenuItemHook):
    """ This class ensures only authorized users will see the menu entry """

    def __init__(self):
        # setup menu entry for sidebar
        MenuItemHook.__init__(
            self,
            text=_("Secure Group Audit"),
            classes="fas fa-user-check fa-fw",
            url_name="securegroups:audit_list",
            order=55,
            navactive=[
                "securegroups:audit_list",
            ],
        )

    def render(self, request):
        if GroupManager.can_manage_groups(request.user) and request.user.has_perms("securegroups.audit_sec_group"):
            return MenuItemHook.render(self, request)
        return ""


@hooks.register("menu_item_hook")
def register_audit():
    return GroupManagementMenuItem()


@hooks.register("secure_group_filters")
def filters():
    return [AltAllianceFilter, AltCorpFilter, UserInGroupFilter]
