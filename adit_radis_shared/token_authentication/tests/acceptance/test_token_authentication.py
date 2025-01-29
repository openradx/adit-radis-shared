import pytest
import requests
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from adit_radis_shared.common.utils.testing_helpers import (
    add_user_to_group,
    create_and_login_example_user,
    create_token_authentication_group,
)


@pytest.mark.acceptance
@pytest.mark.order("last")
@pytest.mark.django_db(transaction=True)
def test_create_and_delete_authentication_token(live_server: LiveServer, page: Page):
    user = create_and_login_example_user(page, live_server.url)
    group = create_token_authentication_group()
    add_user_to_group(user, group)

    page.goto(live_server.url + "/token-authentication/")
    page.get_by_label("Description").fill("Just a test token")
    page.get_by_text("Generate Token").click()
    expect(page.locator("#unhashed-token-string")).to_be_visible()
    token = page.locator("#unhashed-token-string").inner_text()

    response = requests.get(
        live_server.url + "/api/token-authentication/check-auth",
        headers={"Authorization": f"Token {token}"},
    )
    assert response.status_code == 200

    expect(page.locator("table").get_by_text("Just a test token")).to_be_visible()
    page.get_by_label("Delete token").click()
    expect(page.locator("table").get_by_text("Just a test token")).not_to_be_visible()

    response = requests.get(
        live_server.url + "/api/token-authentication/check-auth",
        headers={"Authorization": f"Token {token}"},
    )
    assert response.status_code == 401


@pytest.mark.acceptance
@pytest.mark.order("last")
@pytest.mark.django_db(transaction=True)
def test_invalid_authentication_token(live_server: LiveServer):
    response = requests.get(
        live_server.url + "/api/token-authentication/check-auth",
        headers={"Authorization": "Token invalid_token"},
    )
    assert response.status_code == 401
