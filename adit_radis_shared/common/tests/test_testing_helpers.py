"""Tests for the acceptance-test helpers under ``common.utils.testing_helpers``.

These helpers are only used by the downstream projects, so nothing else in this
repository exercises them.
"""

import pytest
from procrastinate import testing
from procrastinate.contrib.django import app
from procrastinate.psycopg_connector import PsycopgConnector

from adit_radis_shared.common.utils.testing_helpers import run_worker_once


@pytest.mark.django_db(transaction=True)
def test_run_worker_once_builds_a_worker_connector_from_the_django_one():
    assert not isinstance(app.connector, PsycopgConnector)

    run_worker_once()


@pytest.mark.django_db(transaction=True)
def test_run_worker_once_accepts_a_connector_that_already_runs_workers():
    """DjangoConnector.get_worker_connector() returns a PsycopgConnector.

    That result offers no get_worker_connector() of its own, so converting a
    second time raises AttributeError and every caller fails at once.
    """
    worker_connector = app.connector.get_worker_connector()  # type: ignore[attr-defined]

    with app.replace_connector(worker_connector):
        run_worker_once()


def test_run_worker_once_accepts_the_in_memory_connector(in_memory_app):
    with app.replace_connector(testing.InMemoryConnector()):
        run_worker_once()
