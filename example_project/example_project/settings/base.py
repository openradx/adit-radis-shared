"""
Django settings for example_project project.

Generated by 'django-admin startproject' using Django 5.0.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

from pathlib import Path

import environ

env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Used by the ServerCommand to check for file changes during development for autoreload.
SOURCE_FOLDERS = [BASE_DIR / ".." / "adit_radis_shared", BASE_DIR / ".." / "example_project"]  # noqa: F405

# Fetch version from the environment which is passed through from the latest git version tag
PROJECT_VERSION = env.str("PROJECT_VERSION", default="vX.Y.Z")  # type: ignore

# Needed by sites framework
SITE_ID = 1

# The following settings are stored in the Site model on startup initially (see common/apps.py).
# Once set they are stored in the database and can be changed via the admin interface.
SITE_DOMAIN = env.str("SITE_DOMAIN")
SITE_NAME = env.str("SITE_NAME")
SITE_USES_HTTPS = env.bool("SITE_USES_HTTPS")
SITE_META_KEYWORDS = "ADIT, RADIS"
SITE_META_DESCRIPTION = "Shared apps between ADIT and RADIS"
SITE_PROJECT_URL = "https://github.com/openradx/adit-radis-shared"

SECRET_KEY = env.str("DJANGO_SECRET_KEY")

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "daphne",
    "adit_radis_shared.common.apps.CommonConfig",  # must be before "registration"
    "registration",  # should be immediately above "django.contrib.admin"
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.sites",
    "django_extensions",
    "procrastinate.contrib.django",
    "loginas",
    "crispy_forms",
    "crispy_bootstrap5",
    "django_htmx",
    "django_tables2",
    "rest_framework",
    "adit_radis_shared.accounts.apps.AccountsConfig",
    "adit_radis_shared.token_authentication.apps.TokenAuthenticationConfig",
    "example_project.example_app.apps.ExampleAppConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.contrib.sites.middleware.CurrentSiteMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "adit_radis_shared.accounts.middlewares.ActiveGroupMiddleware",
    "adit_radis_shared.common.middlewares.MaintenanceMiddleware",
    "adit_radis_shared.common.middlewares.TimezoneMiddleware",
]

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "adit_radis_shared.common.site.base_context_processor",
            ],
        },
    },
]

WSGI_APPLICATION = "example_project.wsgi.application"

ASGI_APPLICATION = "example_project.asgi.application"

# This seems to be important for Cloud IDEs as CookieStorage does not work there.
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

# Loads the DB setup from the DATABASE_URL environment variable.
DATABASES = {"default": env.db()}

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Custom user model
AUTH_USER_MODEL = "accounts.User"

# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# A custom authentication backend that supports a single currently active group.
AUTHENTICATION_BACKENDS = ["adit_radis_shared.accounts.backends.ActiveGroupModelBackend"]

# Where to redirect to after login
LOGIN_REDIRECT_URL = "home"

# Settings for django-registration-redux
REGISTRATION_FORM = "adit_radis_shared.accounts.forms.RegistrationForm"
ACCOUNT_ACTIVATION_DAYS = 14
REGISTRATION_OPEN = True

EMAIL_SUBJECT_PREFIX = "[ADIT-RADIS-Shared] "

# The email address critical error messages of the server will be sent from.
SERVER_EMAIL = env.str("DJANGO_SERVER_EMAIL")

# The Email address is also used to notify about finished jobs and management notifications.
DEFAULT_FROM_EMAIL = SERVER_EMAIL

# A support Email address that is presented to the users where they can get support.
SUPPORT_EMAIL = env.str("SUPPORT_EMAIL")

# The Django server admins that will receive critical error notifications.
# Also used by django-registration-redux to send account approval emails to.
ADMINS = [(env.str("DJANGO_ADMIN_FULL_NAME"), env.str("DJANGO_ADMIN_EMAIL"))]

# All REST API requests must come from authenticated clients
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "adit_radis_shared.token_authentication.auth.RestTokenAuthentication",
    ],
}

# TODO: Setup LOGGING

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

# A timezone that is presented to the users of the web interface.
USER_TIME_ZONE = env.str("USER_TIME_ZONE")

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/
STATIC_URL = "static/"

# For crispy forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# django-templates2
DJANGO_TABLES2_TEMPLATE = "django_tables2/bootstrap5.html"

# The salt that is used for hashing new tokens in the token authentication app.
# Cave, changing the salt after some tokens were already generated makes them all invalid!
TOKEN_AUTHENTICATION_SALT = env.str("TOKEN_AUTHENTICATION_SALT")
