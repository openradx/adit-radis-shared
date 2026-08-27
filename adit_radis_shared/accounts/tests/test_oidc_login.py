"""Integration tests for the OIDC login with a mocked identity provider.

The provider endpoints (discovery, token, userinfo) are stubbed with the
responses library, so the whole authorization code flow runs against the
Django test client without a real identity provider. A real Keycloak is only
used for manual testing during development, see the README.
"""

from urllib.parse import parse_qs, urlparse

import pytest
import responses
from django.test import Client
from django.urls import reverse

from adit_radis_shared.accounts.models import User

SERVER_URL = "https://idp.example/realms/example-project"
AUTHORIZATION_URL = "https://idp.example/authorize"
TOKEN_URL = "https://idp.example/token"
USERINFO_URL = "https://idp.example/userinfo"

SOCIALACCOUNT_PROVIDERS = {
    "openid_connect": {
        "APPS": [
            {
                "provider_id": "oidc",
                "name": "Example IdP",
                "client_id": "example-client",
                "secret": "example-secret",
                "settings": {"server_url": SERVER_URL},
            }
        ]
    }
}

USERINFO = {
    "sub": "6b3452f5-7868-4670-a751-e4bd847e5162",
    "preferred_username": "idp-user",
    "email": "idp-user@example.org",
    "email_verified": True,
    "given_name": "Idp",
    "family_name": "User",
}


def mock_identity_provider():
    responses.get(
        SERVER_URL + "/.well-known/openid-configuration",
        json={
            "issuer": SERVER_URL,
            "authorization_endpoint": AUTHORIZATION_URL,
            "token_endpoint": TOKEN_URL,
            "userinfo_endpoint": USERINFO_URL,
            "jwks_uri": "https://idp.example/jwks",
        },
    )
    # Without an id_token allauth relies solely on the userinfo endpoint,
    # which saves the mock from producing a signed JWT.
    responses.post(TOKEN_URL, json={"access_token": "mock-access-token"})
    responses.get(USERINFO_URL, json=USERINFO)


def login_via_oidc(client: Client):
    """Run the full authorization code flow and return the final response."""
    response = client.post(reverse("openid_connect_login", kwargs={"provider_id": "oidc"}))
    assert response.status_code == 302
    redirect = urlparse(response.headers["Location"])
    assert response.headers["Location"].startswith(AUTHORIZATION_URL)
    state = parse_qs(redirect.query)["state"][0]

    return client.get(
        reverse("openid_connect_callback", kwargs={"provider_id": "oidc"}),
        {"code": "mock-authorization-code", "state": state},
    )


@pytest.mark.django_db
def test_login_page_offers_oidc_login(client: Client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = SOCIALACCOUNT_PROVIDERS
    response = client.get(reverse("account_login"))
    assert "Log in with Example IdP" in response.text


@pytest.mark.django_db
def test_login_page_without_identity_provider(client: Client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = {}
    response = client.get(reverse("account_login"))
    assert "Log in with" not in response.text


@responses.activate
@pytest.mark.django_db
def test_first_oidc_login_creates_user_without_group(client: Client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = SOCIALACCOUNT_PROVIDERS
    mock_identity_provider()

    response = login_via_oidc(client)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("home")

    user = User.objects.get(username="idp-user")
    assert user.email == "idp-user@example.org"
    assert user.first_name == "Idp"
    assert user.last_name == "User"
    assert client.session["_auth_user_id"] == str(user.pk)

    # The identity provider only authenticates. Authorization happens through
    # the app groups, and nothing provisions those yet, so a fresh OIDC user
    # has no permissions at all.
    assert user.groups.count() == 0
    assert user.active_group is None
    assert user.get_group_permissions() == set()


@responses.activate
@pytest.mark.django_db
def test_second_oidc_login_reuses_user(client: Client, settings):
    settings.SOCIALACCOUNT_PROVIDERS = SOCIALACCOUNT_PROVIDERS
    mock_identity_provider()

    login_via_oidc(client)
    client.logout()
    response = login_via_oidc(client)

    assert response.status_code == 302
    user = User.objects.get(username="idp-user")
    assert client.session["_auth_user_id"] == str(user.pk)
    assert User.objects.count() == 1
