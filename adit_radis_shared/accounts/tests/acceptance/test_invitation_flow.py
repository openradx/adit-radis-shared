import os

# Workaround to make playwright work with Django
# see https://github.com/microsoft/playwright-pytest/issues/29#issuecomment-731515676
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")
import pytest
from django.contrib.auth.models import Group
from playwright.sync_api import Browser, Page, expect
from pytest_django.live_server_helper import LiveServer

from adit_radis_shared.accounts.factories import GroupFactory, UserFactory
from adit_radis_shared.accounts.models import User
from adit_radis_shared.common.utils.testing_helpers import (
    add_permission,
    add_user_to_group,
    login_user,
)


@pytest.mark.acceptance
@pytest.mark.order("last")
@pytest.mark.django_db(transaction=True)
def test_invite_sign_up_and_activate(live_server: LiveServer, page: Page, browser: Browser):
    password = "my_secret_secret"
    admin = UserFactory.create(password=password, is_staff=True)
    admins = GroupFactory.create(name="Admins")
    add_permission(admins, "accounts", "add_invitation")
    add_user_to_group(admin, admins)
    login_user(page, live_server.url, admin.username, password)

    # The admin invites an address and hands the link over directly.
    page.goto(live_server.url + "/accounts/invitations/")
    page.get_by_label("Email").fill("new.colleague@example.org")
    page.get_by_role("button", name="Invite").click()
    row = page.locator("tr", has_text="new.colleague@example.org")
    expect(row).to_contain_text("Pending")
    link = row.get_by_role("button", name="Copy link").get_attribute("data-link")
    assert link

    # The invitee signs up in their own browser and has to wait for the activation.
    invitee = browser.new_context().new_page()
    invitee.goto(link)
    expect(invitee.locator("input[name=email]")).to_have_value("new.colleague@example.org")
    expect(invitee.locator("input[name=email]")).to_be_disabled()
    invitee.locator("[name=username]").fill("colleague")
    invitee.locator("[name=first_name]").fill("New")
    invitee.locator("[name=last_name]").fill("Colleague")
    invitee.locator("[name=phone_number]").fill("12345")
    invitee.locator("[name=department]").fill("Radiology")
    invitee.locator("[name=password1]").fill(password)
    invitee.locator("[name=password2]").fill(password)
    invitee.get_by_role("button", name="Sign Up").click()
    expect(invitee.get_by_text("Account Not Active")).to_be_visible()

    login_user(invitee, live_server.url, "colleague", password)
    expect(invitee.get_by_text("Account Not Active")).to_be_visible()

    # The admin sees the sign up and finishes the onboarding in the Django admin.
    page.goto(live_server.url + "/accounts/invitations/")
    row = page.locator("tr", has_text="new.colleague@example.org")
    expect(row).to_contain_text("Signed up")
    expect(row.get_by_role("link", name="Activate user")).to_be_visible()
    user = User.objects.get(username="colleague")
    user.is_active = True
    user.save()
    add_user_to_group(user, Group.objects.create(name="Radiologists"))

    # The activated user can log in, and the finished invitation left the list.
    login_user(invitee, live_server.url, "colleague", password)
    expect(invitee.locator("#logged_in_username")).to_have_text("colleague")
    page.goto(live_server.url + "/accounts/invitations/")
    expect(page.locator("tr", has_text="new.colleague@example.org")).to_have_count(0)
