from django.conf import settings
from app_utils._app_settings import clean_setting

def discord_bot_active():
    return "aadiscordbot" in settings.INSTALLED_APPS


DISCORD_BOT_COGS = getattr(settings, 'SG_DISCORD_BOT_COGS', ["securegroups.cogs.groupcheck",
                                                             ])
USING_DISCORD_SERVICE = clean_setting("USING_DISCORD_SERVICE", False)
""" Whether or not using AA's Discord Service for Discord Service Filter"""