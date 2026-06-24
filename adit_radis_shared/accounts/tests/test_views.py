"""Integration tests for the accounts views (profile + active group switch)."""

import json

import pytest
from django.test import Client
from django.urls import reverse

from adit_radis_shared.accounts.factories import GroupFactory, UserFactory
from adit_radis_shared.common.utils.testing_helpers import add_user_to_group

# --- UserProfileView --------------------------------------------------------


@pytest.mark.django_db
def test_profile_requires_login(client: Client):
    response = client.get(reverse("profile"))
    assert response.status_code == 302
    assert "/accounts/login" in response.headers["Location"]


@pytest.mark.django_db
def test_profile_renders_for_logged_in_user(client: Client):
    user = UserFactory.create()
    client.force_login(user)
    response = client.get(reverse("profile"))
    assert response.status_code == 200


# --- ActiveGroupView --------------------------------------------------------


@pytest.mark.django_db
def test_active_group_requires_htmx(client: Client):
    user = UserFactory.create()
    group = GroupFactory.create()
    add_user_to_group(user, group)
    client.force_login(user)

    # Without the HX-Request header the view raises SuspiciousOperation (400).
    response = client.post(reverse("active_group"), {"group": group.pk})
    assert response.status_code == 400


@pytest.mark.django_db
def test_active_group_switches_and_triggers_toast(client: Client):
    user = UserFactory.create()
    group_a = GroupFactory.create(name="Group A")
    group_b = GroupFactory.create(name="Group B")
    add_user_to_group(user, group_a, force_activate_group=True)
    add_user_to_group(user, group_b)
    client.force_login(user)

    response = client.post(
        reverse("active_group"),
        {"group": group_b.pk},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.active_group == group_b

    payload = json.loads(response.headers["HX-Trigger"])
    assert payload["toast"]["title"] == "Active group changed"
    assert "Group B" in payload["toast"]["text"]


@pytest.mark.django_db
def test_active_group_invalid_id_raises_validation_error(client: Client):
    user = UserFactory.create()
    group = GroupFactory.create()
    add_user_to_group(user, group)
    client.force_login(user)

    # A non-integer group id triggers a ValidationError inside the view.
    with pytest.raises(Exception):
        client.post(
            reverse("active_group"),
            {"group": "not-an-int"},
            headers={"HX-Request": "true"},
        )
