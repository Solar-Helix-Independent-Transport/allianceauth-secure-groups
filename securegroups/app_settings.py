from django.conf import settings


def discord_bot_active():
    return "aadiscordbot" in settings.INSTALLED_APPS
