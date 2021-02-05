from . import urls
from allianceauth import hooks
from allianceauth.services.hooks import MenuItemHook, UrlHook
from .models import AltCorpFilter, AltAllianceFilter, UserInGroupFilter


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
            return MenuItemHook.render(self, request)
        else:
            return ""


@hooks.register("menu_item_hook")
def register_menu():
    return GroupMenu()


@hooks.register("secure_group_filters")
def filters():
    return [AltAllianceFilter, AltCorpFilter, UserInGroupFilter]
