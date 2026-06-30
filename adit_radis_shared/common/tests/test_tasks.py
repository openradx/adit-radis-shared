"""Unit tests for the shared periodic tasks in ``common.tasks``.

Only ``backup_db`` is covered here. The real ``dbbackup`` management command is
mocked out (no backup is ever performed); the tests assert the task gates on the
``BACKUP_ENABLED`` setting and, when enabled, invokes ``dbbackup`` with the
expected arguments.

``backup_db`` is a Procrastinate task, but ``Task.__call__`` simply forwards to
the wrapped function, so it can be called directly without a worker or queue.
"""

from unittest.mock import patch

import pytest

from adit_radis_shared.common.tasks import backup_db


def test_backup_db_invokes_dbbackup_with_expected_arguments():
    with patch("adit_radis_shared.common.tasks.call_command") as call_command:
        backup_db(timestamp=0)

    call_command.assert_called_once_with("dbbackup", "--clean", "-v", "2")


def test_backup_db_enabled_by_default(settings):
    # No BACKUP_ENABLED attribute at all -> defaults to enabled.
    if hasattr(settings, "BACKUP_ENABLED"):
        del settings.BACKUP_ENABLED

    with patch("adit_radis_shared.common.tasks.call_command") as call_command:
        backup_db(timestamp=0)

    call_command.assert_called_once_with("dbbackup", "--clean", "-v", "2")


def test_backup_db_runs_when_enabled(settings):
    settings.BACKUP_ENABLED = True

    with patch("adit_radis_shared.common.tasks.call_command") as call_command:
        backup_db(timestamp=0)

    call_command.assert_called_once_with("dbbackup", "--clean", "-v", "2")


def test_backup_db_noops_when_disabled(settings):
    settings.BACKUP_ENABLED = False

    with patch("adit_radis_shared.common.tasks.call_command") as call_command:
        result = backup_db(timestamp=0)

    # The task returns early and never touches the management command.
    assert result is None
    call_command.assert_not_called()


def test_backup_db_propagates_command_errors():
    # If the backup command fails, the task must not swallow the error
    # (so the failure surfaces to the worker / monitoring).
    with patch(
        "adit_radis_shared.common.tasks.call_command",
        side_effect=RuntimeError("backup failed"),
    ):
        with pytest.raises(RuntimeError, match="backup failed"):
            backup_db(timestamp=0)
