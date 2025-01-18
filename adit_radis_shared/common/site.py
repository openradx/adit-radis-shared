from typing import Any, NamedTuple

from django.conf import settings
from django.http import HttpRequest
from django.middleware.csrf import get_token

THEME_PREFERENCE_KEY = "theme"


class MainMenuItem(NamedTuple):
    url_name: str
    label: str
    order: int = 1
    staff_only: bool = False


main_menu_items: list[MainMenuItem] = []


def register_main_menu_item(menu_item: MainMenuItem) -> None:
    main_menu_items.append(menu_item)
    main_menu_items.sort(key=lambda x: x.order)


def base_context_processor(request: HttpRequest) -> dict[str, Any]:
    from .utils.auth_utils import is_logged_in_user

    theme = "auto"
    theme_color = "light"
    user = request.user
    if is_logged_in_user(user):
        preferences = user.preferences
        theme = preferences.get("theme", theme)
        theme_color = preferences.get("theme_color", theme_color)

    return {
        "main_menu_items": main_menu_items,
        "project_version": settings.PROJECT_VERSION,
        "site_info": {
            "domain": settings.SITE_DOMAIN,
            "name": settings.SITE_NAME,
            "project_url": settings.SITE_PROJECT_URL,
        },
        "support_email": settings.SUPPORT_EMAIL,
        "theme": theme,
        "theme_color": theme_color,
        ###
        # Data under "public" key will also be available on the client!
        # See also common/templates/common/common_layout.html
        ###
        "public": {
            "debug": settings.DEBUG,
            "csrf_token": get_token(request),
            "theme_preference_key": THEME_PREFERENCE_KEY,
        },
    }
