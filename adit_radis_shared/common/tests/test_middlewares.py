"""Tests for ``common.middlewares.MaintenanceMiddleware``.

The middleware is exercised directly with Django's ``RequestFactory`` and a
stub ``get_response`` callable, so URL routing is not required. The ``health``
URL name is not registered in the example project (it is a consuming-project
concern), so the exemption is tested by patching ``reverse`` in the middleware
module to mimic a project that does register it, plus a case that asserts the
``NoReverseMatch`` fallback keeps the middleware working when it is absent.
"""

from typing import Any, cast

import pytest
from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import NoReverseMatch, reverse

from adit_radis_shared.accounts.factories import AdminUserFactory
from adit_radis_shared.common import middlewares
from adit_radis_shared.common.middlewares import MaintenanceMiddleware
from adit_radis_shared.common.models import ProjectSettings
from adit_radis_shared.common.types import HtmxHttpRequest

HEALTH_PATH = "/health/"


def _sentinel_response(request: Any) -> HttpResponse:
    """A ``get_response`` stub returning a recognisable 200 response."""
    return HttpResponse("OK", status=200)


def _make_request(path: str, user: AbstractBaseUser | AnonymousUser) -> HtmxHttpRequest:
    request = RequestFactory().get(path)
    request.user = user
    return cast(HtmxHttpRequest, request)


def _enable_maintenance() -> None:
    settings_obj = ProjectSettings.get()
    settings_obj.maintenance = True
    settings_obj.save()


def _patch_health_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``reverse("health")`` resolve to ``HEALTH_PATH`` in the middleware.

    Mirrors a consuming project that registers the ``health`` URL pattern; the
    example project deliberately does not.
    """
    real_reverse = reverse

    def fake_reverse(viewname: str, *args: Any, **kwargs: Any) -> str:
        if viewname == "health":
            return HEALTH_PATH
        return real_reverse(viewname, *args, **kwargs)

    monkeypatch.setattr(middlewares, "reverse", fake_reverse)


@pytest.mark.django_db
def test_health_endpoint_passes_through_in_maintenance_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_maintenance()
    _patch_health_url(monkeypatch)

    # Guard: if the middleware ever consults ProjectSettings for the health
    # request, the exemption (which must short-circuit before that) is broken.
    def _boom() -> ProjectSettings:
        raise AssertionError("ProjectSettings.get() must not run for health requests")

    monkeypatch.setattr(ProjectSettings, "get", classmethod(lambda cls: _boom()))

    middleware = MaintenanceMiddleware(_sentinel_response)
    request = _make_request(HEALTH_PATH, AnonymousUser())

    response = middleware(request)

    # Passed straight through to get_response rather than being served the
    # 503 maintenance page.
    assert response.status_code == 200
    assert response.content == b"OK"


@pytest.mark.django_db
def test_normal_endpoint_is_blocked_in_maintenance_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_maintenance()
    _patch_health_url(monkeypatch)

    middleware = MaintenanceMiddleware(_sentinel_response)
    request = _make_request("/some-page/", AnonymousUser())

    response = middleware(request)

    # Anonymous user on a normal page during maintenance gets the 503 page.
    assert response.status_code == 503
    assert response.content != b"OK"


@pytest.mark.django_db
def test_staff_bypass_still_works_in_maintenance_mode(
    monkeypatch: pytest.MonkeyPatch,
):
    _enable_maintenance()
    _patch_health_url(monkeypatch)

    staff = AdminUserFactory.create()
    middleware = MaintenanceMiddleware(_sentinel_response)
    request = _make_request("/some-page/", staff)

    response = middleware(request)

    # Staff bypass the maintenance block and reach the real response.
    assert response.status_code == 200
    assert response.content == b"OK"


@pytest.mark.django_db
def test_missing_health_url_does_not_break_middleware(
    monkeypatch: pytest.MonkeyPatch,
):
    """When ``health`` is not registered, ``NoReverseMatch`` is swallowed.

    The request is then treated as a normal (blockable) request rather than
    raising a 500 on every request.
    """
    _enable_maintenance()
    real_reverse = reverse

    def reverse_without_health(viewname: str, *args: Any, **kwargs: Any) -> str:
        if viewname == "health":
            raise NoReverseMatch("health")
        return real_reverse(viewname, *args, **kwargs)

    monkeypatch.setattr(middlewares, "reverse", reverse_without_health)

    middleware = MaintenanceMiddleware(_sentinel_response)
    request = _make_request(HEALTH_PATH, AnonymousUser())

    response = middleware(request)

    # No NoReverseMatch leaks out; anonymous request is blocked as usual.
    assert response.status_code == 503
