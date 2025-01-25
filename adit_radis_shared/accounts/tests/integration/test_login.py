import pytest
from playwright.sync_api import Page, expect
from pytest_django.live_server_helper import LiveServer

from adit_radis_shared.common.utils.testing_helpers import create_and_login_example_user


@pytest.mark.integration
@pytest.mark.order("last")
@pytest.mark.django_db(transaction=True)
def test_login(live_server: LiveServer, page: Page):
    user = create_and_login_example_user(page, live_server.url)
    expect(page.locator("#logged_in_username")).to_have_text(user.username)
