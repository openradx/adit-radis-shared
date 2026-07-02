import pytest
from django.db import connection
from django_test_migrations.migrator import Migrator
from procrastinate import testing
from procrastinate.contrib.django import procrastinate_app

from adit_radis_shared.common.utils.testing_helpers import ChannelsLiveServer


@pytest.fixture
def channels_live_server(request):
    server = ChannelsLiveServer()
    request.addfinalizer(server.stop)
    return server


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """Terminate leaked test-database sessions before the database is dropped.

    Unlike real ASGI serving (which wraps each request in a
    ThreadSensitiveContext and closes its connections on request_finished),
    Django's test AsyncClient runs the sync ORM parts of async views in
    asgiref's process-wide executor thread and never closes the connections
    opened there (its handler even disconnects close_old_connections on
    purpose). Those idle sessions would make pytest-django's DROP DATABASE
    fail with 'database "..." is being accessed by other users'. Terminating
    them here is what DROP DATABASE ... WITH (FORCE) would do; Django just
    doesn't use FORCE.
    """
    yield
    with django_db_blocker.unblock(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = current_database() AND pid <> pg_backend_pid()"
        )


@pytest.fixture
def in_memory_app(monkeypatch):
    in_memory = testing.InMemoryConnector()
    with procrastinate_app.current_app.replace_connector(in_memory) as app:
        monkeypatch.setattr(procrastinate_app, "current_app", app)
        yield app


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
