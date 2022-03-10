from django.conf import settings


def discord_bot_active():
    return "aadiscordbot" in settings.INSTALLED_APPS


DISCORD_BOT_COGS = getattr(settings, 'SG_DISCORD_BOT_COGS', ["securegroups.cogs.groupcheck",
                                                             ])
