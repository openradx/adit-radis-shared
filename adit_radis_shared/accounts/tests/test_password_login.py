"""Integration tests for the username/password login provided by django-allauth."""

import pytest
from django.test import Client
from django.urls import reverse

from adit_radis_shared.accounts.factories import UserFactory


@pytest.mark.django_db
def test_login_with_username_and_password(client: Client):
    user = UserFactory.create(password="my_secret_secret")

    response = client.post(
        reverse("account_login"), {"login": user.username, "password": "my_secret_secret"}
    )

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("home")
    assert client.session["_auth_user_id"] == str(user.pk)


@pytest.mark.django_db
def test_login_with_wrong_password(client: Client):
    user = UserFactory.create(password="my_secret_secret")

    response = client.post(reverse("account_login"), {"login": user.username, "password": "wrong"})

    assert response.status_code == 200
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
def test_signup_is_closed_without_invitation(client: Client):
    response = client.get(reverse("account_signup"))

    assert response.status_code == 200
    assert "only possible with an invitation" in response.text
