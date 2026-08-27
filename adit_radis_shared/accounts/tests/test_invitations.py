"""Integration tests for the invitation flow: invite, open the link, sign up."""

from datetime import timedelta

import pytest
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from adit_radis_shared.accounts.factories import GroupFactory, UserFactory
from adit_radis_shared.accounts.models import Invitation, User
from adit_radis_shared.common.utils.testing_helpers import add_permission, add_user_to_group

SIGNUP_DATA = {
    "username": "invited",
    "first_name": "In",
    "last_name": "Vited",
    "phone_number": "12345",
    "department": "Radiology",
    "password1": "a-rather-long-password",
    "password2": "a-rather-long-password",
}


def create_inviter() -> User:
    user = UserFactory.create()
    group = GroupFactory.create(name="Admins")
    add_permission(group, "accounts", "add_invitation")
    add_user_to_group(user, group)
    return user


def accept_url(invitation: Invitation) -> str:
    return reverse("invitation_accept", kwargs={"token": invitation.token})


# --- Inviting ---------------------------------------------------------------


@pytest.mark.django_db
def test_invitations_page_requires_permission(client: Client):
    client.force_login(UserFactory.create())
    assert client.get(reverse("invitations")).status_code == 403

    client.force_login(create_inviter())
    assert client.get(reverse("invitations")).status_code == 200


@pytest.mark.django_db
def test_invite_sends_mail_with_link(client: Client):
    inviter = create_inviter()
    client.force_login(inviter)

    response = client.post(reverse("invitations"), {"email": "new.user@example.org"})

    assert response.status_code == 302
    invitation = Invitation.objects.get(email="new.user@example.org")
    assert invitation.invited_by == inviter
    assert invitation.is_valid
    assert invitation.expires - timezone.now() > timedelta(days=settings.INVITATION_VALID_DAYS - 1)
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["new.user@example.org"]
    assert accept_url(invitation) in mail.outbox[0].body


@pytest.mark.django_db
def test_existing_user_cannot_be_invited(client: Client):
    client.force_login(create_inviter())
    existing = UserFactory.create(email="already@example.org")

    response = client.post(reverse("invitations"), {"email": existing.email})

    assert response.status_code == 200
    assert "already exists" in response.text
    assert not Invitation.objects.exists()
    assert not mail.outbox


# --- Opening the link -------------------------------------------------------


@pytest.mark.django_db
def test_invitation_link_opens_signup_with_locked_email(client: Client):
    invitation = Invitation.objects.create(email="new.user@example.org")

    response = client.get(accept_url(invitation))
    assert response.status_code == 302
    assert response.headers["Location"] == reverse("account_signup")

    response = client.get(reverse("account_signup"))
    assert response.status_code == 200
    assert 'value="new.user@example.org"' in response.text
    assert "disabled" in response.text


@pytest.mark.django_db
def test_expired_invitation_is_rejected(client: Client):
    invitation = Invitation.objects.create(
        email="late@example.org", expires=timezone.now() - timedelta(minutes=1)
    )

    response = client.get(accept_url(invitation))
    assert response.status_code == 410

    response = client.get(reverse("account_signup"))
    assert "only possible with an invitation" in response.text


@pytest.mark.django_db
def test_unknown_token_is_rejected(client: Client):
    response = client.get(reverse("invitation_accept", kwargs={"token": "no-such-token"}))
    assert response.status_code == 410


# --- Signing up -------------------------------------------------------------


@pytest.mark.django_db
def test_signup_with_invitation_creates_user(client: Client):
    invitation = Invitation.objects.create(email="new.user@example.org")
    client.get(accept_url(invitation))

    response = client.post(reverse("account_signup"), SIGNUP_DATA)

    assert response.status_code == 302
    assert response.headers["Location"] == reverse("home")

    user = User.objects.get(username="invited")
    assert user.email == "new.user@example.org"
    assert user.first_name == "In"
    assert user.last_name == "Vited"
    assert user.phone_number == "12345"
    assert user.department == "Radiology"
    assert user.check_password("a-rather-long-password")
    assert EmailAddress.objects.get(user=user).verified
    assert client.session["_auth_user_id"] == str(user.pk)

    invitation.refresh_from_db()
    assert invitation.accepted is not None
    assert invitation.user == user

    # Only an admin can put the user into a group, so the admin is informed ...
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == list(settings.ADMINS)
    assert user.username in mail.outbox[0].body
    # ... and the user is told to wait for that.
    assert user.groups.count() == 0
    response = client.get(reverse("home"))
    assert "not assigned to any group yet" in response.text


@pytest.mark.django_db
def test_signup_ignores_a_submitted_email(client: Client):
    invitation = Invitation.objects.create(email="new.user@example.org")
    client.get(accept_url(invitation))

    client.post(reverse("account_signup"), SIGNUP_DATA | {"email": "someone.else@example.org"})

    assert User.objects.get(username="invited").email == "new.user@example.org"


@pytest.mark.django_db
def test_invitation_cannot_be_used_twice(client: Client):
    invitation = Invitation.objects.create(email="new.user@example.org")
    client.get(accept_url(invitation))
    client.post(reverse("account_signup"), SIGNUP_DATA)
    client.logout()

    assert client.get(accept_url(invitation)).status_code == 410
    assert "only possible with an invitation" in client.get(reverse("account_signup")).text
