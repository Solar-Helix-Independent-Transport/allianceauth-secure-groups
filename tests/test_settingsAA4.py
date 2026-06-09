"""
Alliance Auth Test Suite Django settings.
"""

from allianceauth.project_template.project_name.settings.base import *  # noqa

SITE_URL = "https://example.com"
CSRF_TRUSTED_ORIGINS = [SITE_URL]

# Celery configuration
CELERY_ALWAYS_EAGER = True  # Forces celery to run locally for testing

INSTALLED_APPS += [  # noqa: F405
    "securegroups",
    "allianceauth.services.modules.discord",
    "allianceauth.services.modules.discourse",
    "allianceauth.services.modules.ips4",
    "allianceauth.services.modules.mumble",
    "allianceauth.services.modules.openfire",
    "allianceauth.services.modules.phpbb3",
    "allianceauth.services.modules.smf",
    "allianceauth.services.modules.teamspeak3",
    "allianceauth.services.modules.xenforo",
]

ROOT_URLCONF = 'tests.urls'

NOSE_ARGS = [
    # '--with-coverage',
    # '--cover-package=',
    # '--exe',  # If your tests need this to be found/run, check they py files are not chmodded +x
]


DISCORD_APP_ID = "fake"
DISCORD_APP_SECRET = "fake"
DISCORD_BOT_TOKEN = "fake"
DISCORD_CALLBACK_URL = "https://example.com/discord/callback"
DISCORD_GUILD_ID = "1234567890"

IPS4_URL = "https://example.com/ips4"
IPS4_API_KEY = "fake"

PHPBB3_URL = "https://example.com/phpbb3"
PHPBB3_ENDPOINT = "https://example.com/phpbb3/auth"
PHPBB3_MASTER_KEY = "fake"

SMF_URL = "https://example.com/smf"
SMF_ENDPOINT = "https://example.com/smf/auth"
SMF_MASTER_KEY = "fake"

JABBER_URL = "https://example.com/jabber"
JABBER_SERVER = "example.com"
OPENFIRE_ADDRESS = "example.com"
OPENFIRE_SECRET_KEY = "fake"
OPENFIRE_PORT = 9090

MUMBLE_URL = "example.com"

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# LOGGING = None  # Comment out to enable logging for debugging

# Register an application at https://developers.eveonline.com for Authentication
# & API Access and fill out these settings. Be sure to set the callback URL
# to https://example.com/sso/callback substituting your domain for example.com
# Logging in to auth requires the publicData scope (can be overridden through the
# LOGIN_TOKEN_SCOPES setting). Other apps may require more (see their docs).
ESI_SSO_CLIENT_ID = '123'
ESI_SSO_CLIENT_SECRET = '123'
ESI_SSO_CALLBACK_URL = '123'
ESI_USER_CONTACT_EMAIL = "noreply@example.con"

CACHES = {
    "default": {
        # "BACKEND": "redis_cache.RedisCache",
        # "LOCATION": "localhost:6379",
        # "OPTIONS": {
        #    "DB": 1,
        # }
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/1",
        "OPTIONS": {
            "COMPRESSOR": "django_redis.compressors.lzma.LzmaCompressor",
        }
    }
}
