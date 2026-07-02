"""Integration tests for ``common.views`` through the example_project URLs.

These go through the real Django test client so URL routing, middleware and
templates are all exercised together.
"""

import pytest
from django.test import Client
from django.urls import reverse

from adit_radis_shared.accounts.factories import AdminUserFactory, UserFactory
from adit_radis_shared.common.models import ProjectSettings
from adit_radis_shared.common.site import THEME_PREFERENCE_KEY

# --- BaseHomeView -----------------------------------------------------------


@pytest.mark.django_db
def test_home_view_renders_announcement_in_context(client: Client):
    settings_obj = ProjectSettings.get()
    settings_obj.announcement = "Scheduled downtime tonight"
    settings_obj.save()

    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert response.context["announcement"] == "Scheduled downtime tonight"


# --- BaseUpdatePreferencesView ----------------------------------------------


@pytest.mark.django_db
def test_update_preferences_requires_login(client: Client):
    # update-preferences/ has no name, so use the literal path.
    response = client.post("/update-preferences/", {THEME_PREFERENCE_KEY: "dark"})
    # LoginRequiredMixin redirects anonymous users to the login page.
    assert response.status_code == 302
    assert "/accounts/login" in response.headers["Location"]


@pytest.mark.django_db
def test_update_preferences_persists_allowed_key(client: Client):
    user = UserFactory.create()
    client.force_login(user)

    response = client.post("/update-preferences/", {THEME_PREFERENCE_KEY: "dark"})

    assert response.status_code == 200
    user.refresh_from_db()
    assert user.preferences[THEME_PREFERENCE_KEY] == "dark"


@pytest.mark.django_db
def test_update_preferences_coerces_true_false_strings(client: Client):
    user = UserFactory.create()
    client.force_login(user)

    client.post("/update-preferences/", {THEME_PREFERENCE_KEY: "true"})
    user.refresh_from_db()
    assert user.preferences[THEME_PREFERENCE_KEY] is True

    client.post("/update-preferences/", {THEME_PREFERENCE_KEY: "false"})
    user.refresh_from_db()
    assert user.preferences[THEME_PREFERENCE_KEY] is False


@pytest.mark.django_db
def test_update_preferences_rejects_disallowed_key(client: Client):
    user = UserFactory.create()
    client.force_login(user)

    # An unknown key triggers a SuspiciousOperation (HTTP 400).
    response = client.post("/update-preferences/", {"not_allowed": "x"})
    assert response.status_code == 400


# --- BroadcastView ----------------------------------------------------------


@pytest.mark.django_db
def test_broadcast_view_forbidden_for_non_staff(client: Client):
    user = UserFactory.create(is_staff=False)
    client.force_login(user)

    response = client.get(reverse("broadcast"))
    # UserPassesTestMixin returns 403 for a logged-in user failing the test.
    assert response.status_code == 403


@pytest.mark.django_db
def test_broadcast_view_renders_form_for_staff(client: Client):
    staff = AdminUserFactory.create()
    client.force_login(staff)

    response = client.get(reverse("broadcast"))
    assert response.status_code == 200
    assert "form" in response.context


@pytest.mark.django_db
def test_broadcast_view_defers_mail_on_valid_post(client: Client, in_memory_app):
    staff = AdminUserFactory.create()
    recipient = UserFactory.create(email="recipient@example.test")
    client.force_login(staff)

    response = client.post(
        reverse("broadcast"),
        {
            "recipients": [recipient.pk],
            "subject": "Maintenance",
            "message": "Tonight at 9pm",
        },
    )

    # Successful form submission redirects back to the same page.
    assert response.status_code == 302

    # The broadcast_mail task was deferred to the (in-memory) queue.
    jobs = list(in_memory_app.job_manager.list_jobs())
    assert len(jobs) == 1
    assert jobs[0].task_name.endswith("broadcast_mail")
    assert jobs[0].task_kwargs["recipients"] == ["recipient@example.test"]


# --- HtmxTemplateView -------------------------------------------------------


@pytest.mark.django_db
def test_htmx_template_view_requires_htmx_header(client: Client):
    user = UserFactory.create()
    client.force_login(user)

    # token_authentication_help is wired to HtmxTemplateView.
    url = reverse("token_authentication_help")

    # Without the HX-Request header it raises SuspiciousOperation -> 400.
    assert client.get(url).status_code == 400

    # With the header it renders normally.
    assert client.get(url, headers={"HX-Request": "true"}).status_code == 200
