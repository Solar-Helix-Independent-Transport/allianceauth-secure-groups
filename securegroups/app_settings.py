from django.conf import settings

MEMBER_STATES = getattr(settings, "MEMBER_STATES", ["Member"])


def discord_bot_active():
    return "aadiscordbot" in settings.INSTALLED_APPS
