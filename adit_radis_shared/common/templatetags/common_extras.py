import logging
from datetime import date, datetime, time
from typing import Any, Literal

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpRequest
from django.template import Library
from django.template.defaultfilters import join

logger = logging.getLogger(__name__)

register = Library()


@register.filter
def access_item(d: dict, key: str) -> Any:
    return d.get(key, "")


@register.simple_tag(takes_context=True)
def base_url(context: dict[str, Any]) -> str:
    """Get the base URL of the current site."""
    protocol: Literal["http", "https"]
    request: HttpRequest | None = context.get("request")
    if request:
        protocol = "https" if request.is_secure() else "http"
        site = get_current_site(request)
        domain = site.domain
    else:
        protocol = "https" if settings.ENVIRONMENT == "production" else "http"
        domain = settings.SITE_DOMAIN

    return f"{protocol}://{domain}"


@register.simple_tag
def get_setting(name) -> Any:
    """Access a setting from a template.

    Cave, should be used carefully! Don't expose private data in templates.
    """
    return getattr(settings, name, "")


@register.simple_tag
def get_site_name() -> str:
    return get_setting("SITE_NAME")


@register.inclusion_tag("common/_bootstrap_icon.html")
def bootstrap_icon(icon_name: str, size: int = 16):
    return {"icon_name": icon_name, "size": size}


@register.simple_tag(takes_context=True)
def url_replace(context: dict[str, Any], field: str, value: Any) -> str:
    dict_ = context["request"].GET.copy()
    dict_[field] = value
    return dict_.urlencode()


@register.filter(is_safe=True, needs_autoescape=True)
def join_if_list(value: Any, arg: str, autoescape=True) -> Any:
    if isinstance(value, list):
        return join(value, arg, autoescape)

    return value


@register.simple_tag
def combine_datetime(date: date, time: time) -> datetime:
    return datetime.combine(date, time)


@register.filter
def alert_class(tag: str) -> str:
    tag_map = {
        "info": "alert-info",
        "success": "alert-success",
        "warning": "alert-warning",
        "error": "alert-danger",
    }
    return tag_map.get(tag, "alert-secondary")


@register.filter
def message_symbol(tag: str) -> str:
    tag_map = {
        "info": "info",
        "success": "success",
        "warning": "warning",
        "error": "error",
    }
    return tag_map.get(tag, "bug")
