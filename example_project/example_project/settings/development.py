from .base import *  # noqa: F403
from .base import env

DEBUG = True

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])  # type: ignore

INTERNAL_IPS = env.list("DJANGO_INTERNAL_IPS", default=["127.0.0.1"])  # type: ignore

ENABLE_REMOTE_DEBUGGING = env.bool("ENABLE_REMOTE_DEBUGGING", default=False)  # type: ignore

SECRET_KEY = env.str(
    "DJANGO_SECRET_KEY",
    default="ug+cbde301nelb)(di0^p21osy3h=t$%2$-8d&0#xlyfj8&==5",  # type: ignore
)

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "debug_permissions",
    "django_browser_reload",
]

MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django_browser_reload.middleware.BrowserReloadMiddleware",
]

if env.bool("FORCE_DEBUG_TOOLBAR", default=False):  # type: ignore
    # https://github.com/jazzband/django-debug-toolbar/issues/1035
    from django.conf import settings

    DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: settings.DEBUG}

if env.bool("USE_DOCKER", default=False):  # type: ignore
    import socket

    # For Debug Toolbar to show up on Docker Compose in development mode.
    # This only works when browsed from the host where the containers are run.
    # If viewed from somewhere else then DJANGO_INTERNAL_IPS must be set.
    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join(ip.split(".")[:-1] + ["1"]) for ip in ips]
