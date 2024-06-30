import time
from typing import Callable

import pytest
from django.db import connection
from django_test_migrations.migrator import Migrator
from playwright.sync_api import Locator, Page, Response

from adit_radis_shared.accounts.factories import UserFactory
from adit_radis_shared.common.utils.testing import ChannelsLiveServer


@pytest.fixture
def channels_live_server(request):
    server = ChannelsLiveServer()
    request.addfinalizer(server.stop)
    return server


@pytest.fixture
def poll():
    def _poll(
        locator: Locator,
        func: Callable[[Locator], Response | None] = lambda loc: loc.page.reload(),
        interval: int = 1_500,
        timeout: int = 15_000,
    ):
        start_time = time.time()
        while True:
            try:
                locator.wait_for(timeout=interval)
                return locator
            except Exception as err:
                elapsed_time = (time.time() - start_time) * 1000
                if elapsed_time > timeout:
                    raise err

            func(locator)

    return _poll


@pytest.fixture
def login_user(page: Page):
    def _login_user(server_url: str, username: str, password: str):
        page.goto(server_url + "/accounts/login")
        page.get_by_label("Username").fill(username)
        page.get_by_label("Password").fill(password)
        page.get_by_text("Log in").click()

    return _login_user


# TODO: See if we can make it a yield fixture with name logged_in_user
@pytest.fixture
def create_and_login_user(page: Page, login_user):
    def _create_and_login_user(server_url: str):
        password = "mysecret"
        user = UserFactory(password=password)

        login_user(server_url, user.username, password)

        return user

    return _create_and_login_user


@pytest.fixture
def migrator_ext(migrator: Migrator) -> Migrator:
    # We have to manually drop the Procrastinate tables, functions and types
    # as otherwise django_test_migrations will fail.
    # See https://github.com/procrastinate-org/procrastinate/issues/1090
    with connection.cursor() as cursor:
        cursor.execute("""
        DO $$ 
        DECLARE
            prefix text := 'procrastinate';
        BEGIN
            -- Drop tables
            EXECUTE (
                SELECT string_agg('DROP TABLE IF EXISTS ' || quote_ident(tablename)
                || ' CASCADE;', ' ')
                FROM pg_tables
                WHERE tablename LIKE prefix || '%'
            );

            -- Drop functions
            EXECUTE (
                SELECT string_agg(
                    'DROP FUNCTION IF EXISTS ' || quote_ident(n.nspname) || '.'
                    || quote_ident(p.proname) || '('
                    || pg_catalog.pg_get_function_identity_arguments(p.oid) || ') CASCADE;',
                    ' '
                )
                FROM pg_proc p
                LEFT JOIN pg_namespace n ON n.oid = p.pronamespace
                WHERE p.proname LIKE prefix || '%'
            );

            -- Drop types
            EXECUTE (
                SELECT string_agg('DROP TYPE IF EXISTS ' || quote_ident(typname)
                || ' CASCADE;', ' ')
                FROM pg_type
                WHERE typname LIKE prefix || '%'
            );
        END $$;
        """)

    return migrator
