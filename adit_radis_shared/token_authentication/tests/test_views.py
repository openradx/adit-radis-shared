"""Integration tests for the token-authentication views.

Covers the dashboard (token generation form) and the delete flow through the
example_project URL configuration, plus the unauthenticated CheckAuthView.
"""

import pytest
from django.test import Client
from django.urls import reverse

from adit_radis_shared.accounts.factories import AdminUserFactory, UserFactory
from adit_radis_shared.common.utils.testing_helpers import (
    add_permission,
    create_token_authentication_group,
)
from adit_radis_shared.token_authentication.models import Token


def _user_with_token_perms():
    """A non-staff user that may view, add and delete tokens."""
    user = UserFactory.create()
    group = create_token_authentication_group()
    user.groups.add(group)
    user.change_active_group(group)
    return user


# --- TokenDashboardView -----------------------------------------------------


@pytest.mark.django_db
def test_dashboard_requires_login(client: Client):
    response = client.get(reverse("token_dashboard"))
    assert response.status_code == 302
    assert "/accounts/login" in response.headers["Location"]


@pytest.mark.django_db
def test_dashboard_forbidden_without_permission(client: Client):
    user = UserFactory.create()
    client.force_login(user)
    # PermissionRequiredMixin raises -> 403 for a logged-in user lacking perms.
    response = client.get(reverse("token_dashboard"))
    assert response.status_code == 403


@pytest.mark.django_db
def test_dashboard_lists_only_own_tokens(client: Client):
    user = _user_with_token_perms()
    other = UserFactory.create()
    Token.objects.create_token(user, "mine", expires=None)
    Token.objects.create_token(other, "theirs", expires=None)

    client.force_login(user)
    response = client.get(reverse("token_dashboard"))

    assert response.status_code == 200
    descriptions = {t.description for t in response.context["tokens"]}
    assert descriptions == {"mine"}


@pytest.mark.django_db
def test_dashboard_generates_token_and_shows_it_once(client: Client):
    user = _user_with_token_perms()
    client.force_login(user)

    response = client.post(
        reverse("token_dashboard"),
        {"description": "scripting", "expiry_time": "24"},
        follow=True,
    )

    assert response.status_code == 200
    # The freshly minted token is surfaced exactly once via the session.
    assert response.context["new_token"]
    assert Token.objects.filter(owner=user, description="scripting").count() == 1

    # A subsequent GET no longer exposes the plaintext token.
    follow_up = client.get(reverse("token_dashboard"))
    assert follow_up.context["new_token"] is None


@pytest.mark.django_db
def test_dashboard_rejects_never_expiring_without_permission(client: Client):
    user = _user_with_token_perms()
    client.force_login(user)

    response = client.post(
        reverse("token_dashboard"),
        {"description": "forever", "expiry_time": "0"},
    )

    # Form is redisplayed with a validation error; no token is created.
    assert response.status_code == 200
    assert response.context["form"].errors
    assert not Token.objects.filter(description="forever").exists()


@pytest.mark.django_db
def test_dashboard_allows_never_expiring_with_permission(client: Client):
    user = _user_with_token_perms()
    add_permission(user, "token_authentication", "can_generate_never_expiring_token")
    client.force_login(user)

    response = client.post(
        reverse("token_dashboard"),
        {"description": "forever", "expiry_time": "0"},
        follow=True,
    )

    assert response.status_code == 200
    token = Token.objects.get(owner=user, description="forever")
    assert token.expires is None


# --- DeleteTokenView --------------------------------------------------------


@pytest.mark.django_db
def test_delete_token_removes_own_token(client: Client):
    user = _user_with_token_perms()
    token, _ = Token.objects.create_token(user, "to delete", expires=None)
    client.force_login(user)

    response = client.post(reverse("delete_token", args=[token.pk]))

    assert response.status_code == 302
    assert not Token.objects.filter(pk=token.pk).exists()


@pytest.mark.django_db
def test_delete_token_cannot_delete_other_users_token(client: Client):
    user = _user_with_token_perms()
    other = UserFactory.create()
    token, _ = Token.objects.create_token(other, "not yours", expires=None)
    client.force_login(user)

    # get_queryset() filters to the owner, so another user's token is a 404.
    response = client.post(reverse("delete_token", args=[token.pk]))
    assert response.status_code == 404
    assert Token.objects.filter(pk=token.pk).exists()


@pytest.mark.django_db
def test_staff_can_delete_any_token(client: Client):
    owner = UserFactory.create()
    token, _ = Token.objects.create_token(owner, "owned by user", expires=None)
    staff = AdminUserFactory.create()
    client.force_login(staff)

    response = client.post(reverse("delete_token", args=[token.pk]))

    assert response.status_code == 302
    assert not Token.objects.filter(pk=token.pk).exists()


# --- CheckAuthView ----------------------------------------------------------


@pytest.mark.django_db
def test_check_auth_rejects_anonymous(client: Client):
    # No token supplied -> DRF IsAuthenticated denies with 401/403.
    response = client.get("/api/token-authentication/check-auth/")
    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_check_auth_accepts_valid_token(client: Client):
    user = UserFactory.create()
    _token, token_string = Token.objects.create_token(user, "api", expires=None)

    response = client.get(
        "/api/token-authentication/check-auth/",
        HTTP_AUTHORIZATION=f"Token {token_string}",
    )
    assert response.status_code == 200
