from django.apps import AppConfig
from . import __version__


class SecureGroupsConfig(AppConfig):
    name = "securegroups"
    label = "securegroups"
    verbose_name = f"Secure Groups v{__version__}"

    def ready(self):
        import securegroups.signals
