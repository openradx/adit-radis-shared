"""Unit tests for the ``common_extras`` template tags and filters.

These are pure functions (or thin wrappers over the ORM/Site framework) so they
can be exercised directly without going through template rendering.
"""

from datetime import date, datetime, time

import pytest
from django.http import HttpRequest, QueryDict

from adit_radis_shared.common.templatetags.common_extras import (
    access_item,
    alert_class,
    base_url,
    bootstrap_icon,
    combine_datetime,
    join_if_list,
    message_symbol,
    url_replace,
)


def test_access_item_returns_value_for_present_key():
    assert access_item({"a": 1, "b": 2}, "a") == 1


def test_access_item_returns_empty_string_for_missing_key():
    assert access_item({"a": 1}, "missing") == ""


def test_bootstrap_icon_builds_context_with_default_size():
    assert bootstrap_icon("house") == {"icon_name": "house", "size": 16}


def test_bootstrap_icon_respects_custom_size():
    assert bootstrap_icon("gear", size=32) == {"icon_name": "gear", "size": 32}


def test_combine_datetime_merges_date_and_time():
    result = combine_datetime(date(2024, 1, 2), time(13, 45))
    assert result == datetime(2024, 1, 2, 13, 45)


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("info", "alert-info"),
        ("success", "alert-success"),
        ("warning", "alert-warning"),
        ("error", "alert-danger"),
        ("unknown", "alert-secondary"),
    ],
)
def test_alert_class_maps_tags(tag, expected):
    assert alert_class(tag) == expected


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("info", "info"),
        ("success", "success"),
        ("warning", "warning"),
        ("error", "error"),
        ("something-else", "bug"),
    ],
)
def test_message_symbol_maps_tags(tag, expected):
    assert message_symbol(tag) == expected


def test_join_if_list_joins_list_values():
    assert join_if_list(["a", "b", "c"], ", ") == "a, b, c"


def test_join_if_list_passes_through_non_list():
    # A plain string is not a list, so it is returned unchanged.
    assert join_if_list("plain", ", ") == "plain"


def test_url_replace_sets_or_overrides_query_param():
    request = HttpRequest()
    request.GET = QueryDict("page=2&status=PE")
    context = {"request": request}

    result = url_replace(context, "page", 5)

    parsed = QueryDict(result)
    assert parsed["page"] == "5"
    assert parsed["status"] == "PE"


def test_url_replace_adds_missing_param():
    request = HttpRequest()
    request.GET = QueryDict("status=PE")
    context = {"request": request}

    result = QueryDict(url_replace(context, "page", 1))
    assert result["page"] == "1"
    assert result["status"] == "PE"


@pytest.mark.django_db
def test_base_url_without_request_uses_settings_environment(settings):
    # The Site framework needs the DB (a Site row is created at startup).
    settings.ENVIRONMENT = "development"
    result = base_url({})
    assert result.startswith("http://")


@pytest.mark.django_db
def test_base_url_production_without_request_is_https(settings):
    settings.ENVIRONMENT = "production"
    result = base_url({})
    assert result.startswith("https://")


@pytest.mark.django_db
def test_base_url_uses_request_scheme_when_available():
    secure_request = HttpRequest()
    secure_request.META["HTTP_X_FORWARDED_PROTO"] = "https"
    secure_request.META["SERVER_PORT"] = "443"
    # is_secure() reads from the request; force it deterministically.
    secure_request.is_secure = lambda: True

    result = base_url({"request": secure_request})
    assert result.startswith("https://")
