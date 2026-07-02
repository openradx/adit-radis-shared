"""Unit/integration tests for REST token authentication.

These exercise the credential boundary directly (model manager + DRF
authentication class) rather than through the browser, complementing the
existing acceptance test.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIRequestFactory

from adit_radis_shared.accounts.factories import UserFactory
from adit_radis_shared.token_authentication.auth import RestTokenAuthentication
from adit_radis_shared.token_authentication.models import (
    FRACTION_LENGTH,
    TOKEN_LENGTH,
    Token,
)
from adit_radis_shared.token_authentication.utils.crypto import hash_token


def _authenticate(token_string: str):
    """Run RestTokenAuthentication against a request carrying the given token."""
    request = APIRequestFactory().get(
        "/api/token-authentication/check-auth",
        HTTP_AUTHORIZATION=f"Token {token_string}",
    )
    return RestTokenAuthentication().authenticate(request)


@pytest.mark.django_db
def test_valid_token_authenticates_and_resolves_user():
    user = UserFactory.create()
    _token, token_string = Token.objects.create_token(user, "valid token", expires=None)

    result = _authenticate(token_string)

    assert result is not None
    auth_user, auth_token = result
    assert auth_user == user
    assert auth_token.owner == user


@pytest.mark.django_db
def test_unknown_token_is_rejected():
    # No token created, so this hash does not exist in the DB.
    with pytest.raises(AuthenticationFailed):
        _authenticate("this_token_does_not_exist")


@pytest.mark.django_db
def test_wrong_protocol_is_rejected():
    user = UserFactory.create()
    _token, token_string = Token.objects.create_token(user, "valid token", expires=None)

    request = APIRequestFactory().get(
        "/api/token-authentication/check-auth",
        HTTP_AUTHORIZATION=f"Bearer {token_string}",
    )
    with pytest.raises(AuthenticationFailed):
        RestTokenAuthentication().authenticate(request)


@pytest.mark.django_db
def test_expired_token_is_rejected():
    user = UserFactory.create()
    expires = timezone.now() - timedelta(hours=1)
    _token, token_string = Token.objects.create_token(user, "expired token", expires=expires)

    with pytest.raises(AuthenticationFailed):
        _authenticate(token_string)


@pytest.mark.django_db
def test_last_used_is_updated_on_use():
    user = UserFactory.create()
    token, token_string = Token.objects.create_token(user, "tracked token", expires=None)
    assert token.last_used is None

    before = timezone.now()
    _authenticate(token_string)

    token.refresh_from_db()
    assert token.last_used is not None
    assert token.last_used >= before


@pytest.mark.django_db
def test_token_is_stored_hashed_never_plaintext():
    user = UserFactory.create()
    token, token_string = Token.objects.create_token(user, "secret token", expires=None)

    token.refresh_from_db()
    # The plaintext is never persisted.
    assert token.token_hashed != token_string
    # What is stored is the deterministic hash of the plaintext.
    assert token.token_hashed == hash_token(token_string)
    # Generated plaintext has the expected length (hexlify doubles the byte count).
    assert len(token_string) == TOKEN_LENGTH * 2


@pytest.mark.django_db
def test_fraction_is_expected_preview():
    user = UserFactory.create()
    token, token_string = Token.objects.create_token(user, "preview token", expires=None)

    token.refresh_from_db()
    assert token.fraction == token_string[:FRACTION_LENGTH]
    assert len(token.fraction) == FRACTION_LENGTH
