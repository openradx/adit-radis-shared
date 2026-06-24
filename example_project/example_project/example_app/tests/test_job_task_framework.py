"""Tests for the Job/Task framework as it actually exists on ``main``.

NOTE ON SCOPE
-------------
The brief for these tests assumed an *abstract* Job/Task base class living in
``adit_radis_shared.common`` that implements a status state machine
(``PENDING -> IN_PROGRESS -> SUCCESS/WARNING/FAILURE``), per-task retry, failure
precedence and Job-from-Task state aggregation.

That machinery does **not** exist in this repository on ``main``. It lives in the
downstream ADIT / RADIS projects, not in adit-radis-shared. What this shared
library actually ships is:

* ``example_app.models.ExampleJob`` -- a plain Django model whose only state is a
  3-value ``Status`` enum (``PENDING / IN_PROGRESS / DONE``). There is no Task
  model, no ``SUCCESS/WARNING/FAILURE`` and no aggregation logic.
* The Procrastinate task queue (``example_app.tasks`` + ``common.tasks``), which
  is the real "task" abstraction here: deferral, worker execution, success /
  failure states and retry.

These tests therefore cover what exists:

1. ``ExampleJob`` status values, defaults and transitions.
2. The Procrastinate task lifecycle: defer -> run -> succeeded / failed.
3. Procrastinate retry behaviour (fail-then-succeed, and exhausting retries).

The features from the original brief that are genuinely absent are documented as
``xfail`` markers so the gap is visible in the test report rather than silently
dropped. See ``TestAbsentStateMachineFeatures`` at the bottom.
"""

import pytest
import time_machine
from procrastinate import testing
from procrastinate.app import App
from pytest import CaptureFixture

from example_project.example_app.factories import ExampleJobFactory
from example_project.example_app.models import ExampleJob
from example_project.example_app.tasks import example_task

# ---------------------------------------------------------------------------
# ExampleJob model: the only model-level "Job status" surface that exists.
# ---------------------------------------------------------------------------


class TestExampleJobStatus:
    def test_status_choices_are_exactly_the_three_documented_values(self):
        assert ExampleJob.Status.choices == [
            ("PE", "Pending"),
            ("IP", "In progress"),
            ("DO", "Done"),
        ]

    def test_status_enum_db_values(self):
        assert ExampleJob.Status.PENDING == "PE"
        assert ExampleJob.Status.IN_PROGRESS == "IP"
        assert ExampleJob.Status.DONE == "DO"

    @pytest.mark.django_db
    def test_default_status_is_pending(self):
        job = ExampleJob.objects.create(name="fresh")
        job.refresh_from_db()
        assert job.status == ExampleJob.Status.PENDING

    @pytest.mark.django_db
    def test_status_transition_pending_to_in_progress_to_done(self):
        job = ExampleJob.objects.create(name="lifecycle")
        assert job.status == ExampleJob.Status.PENDING

        job.status = ExampleJob.Status.IN_PROGRESS
        job.save()
        job.refresh_from_db()
        assert job.status == ExampleJob.Status.IN_PROGRESS

        job.status = ExampleJob.Status.DONE
        job.save()
        job.refresh_from_db()
        assert job.status == ExampleJob.Status.DONE

    @pytest.mark.django_db
    def test_str_includes_classname_name_and_pk(self):
        job = ExampleJob.objects.create(name="reporting")
        assert str(job) == f"ExampleJob reporting [{job.pk}]"


@pytest.mark.django_db
class TestExampleJobFactory:
    def test_factory_creates_persisted_job_with_valid_status(self):
        valid = {key for key, _ in ExampleJob.Status.choices}
        job = ExampleJobFactory.create()
        assert job.pk is not None
        assert job.status in valid
        assert job.name

    def test_factory_status_can_be_overridden(self):
        job = ExampleJobFactory.create(status=ExampleJob.Status.IN_PROGRESS)
        assert job.status == ExampleJob.Status.IN_PROGRESS


# ---------------------------------------------------------------------------
# Procrastinate task framework: the actual "task" abstraction.
#
# We assert against the InMemoryConnector job store, which is the supported
# in-memory testing surface (``in_memory_app`` fixture from
# ``adit_radis_shared.pytest_fixtures``).
# ---------------------------------------------------------------------------


def _run_worker(app: App) -> None:
    app.run_worker(
        wait=False, install_signal_handlers=False, listen_notify=False, delete_jobs="never"
    )


def _connector(app: App) -> testing.InMemoryConnector:
    connector = app.connector
    assert isinstance(connector, testing.InMemoryConnector)
    return connector


class TestTaskLifecycle:
    def test_deferred_task_starts_in_todo_state(self, in_memory_app: App):
        job_id = example_task.defer()
        connector = _connector(in_memory_app)
        assert connector.jobs[job_id]["status"] == "todo"

    def test_task_succeeds_after_worker_run(
        self, in_memory_app: App, capsys: CaptureFixture[str]
    ):
        job_id = example_task.defer()
        _run_worker(in_memory_app)

        connector = _connector(in_memory_app)
        assert connector.jobs[job_id]["status"] == "succeeded"
        assert f"Hello from job {job_id}" in capsys.readouterr().out

    def test_task_failure_is_recorded_as_failed_state(self, in_memory_app: App):
        @in_memory_app.task(name="boom_task")
        def boom_task():
            raise ValueError("kaboom")

        job_id = boom_task.defer()
        _run_worker(in_memory_app)

        connector = _connector(in_memory_app)
        assert connector.jobs[job_id]["status"] == "failed"

    def test_task_arguments_are_persisted_on_the_job(self, in_memory_app: App):
        @in_memory_app.task(name="add_task")
        def add_task(a: int, b: int):
            return a + b

        job_id = add_task.defer(a=2, b=3)
        connector = _connector(in_memory_app)
        assert connector.jobs[job_id]["args"] == {"a": 2, "b": 3}
        assert connector.jobs[job_id]["task_name"] == "add_task"


class TestTaskRetry:
    def test_task_retries_until_success(self, in_memory_app: App):
        """A task configured with ``retry=2`` that fails twice then succeeds is
        invoked three times and ends in the ``succeeded`` state."""
        calls = {"count": 0}

        @in_memory_app.task(name="flaky_then_ok", retry=2)
        def flaky_then_ok():
            calls["count"] += 1
            if calls["count"] < 3:
                raise ValueError("transient")
            return "ok"

        job_id = flaky_then_ok.defer()
        _run_worker(in_memory_app)

        connector = _connector(in_memory_app)
        assert calls["count"] == 3
        assert connector.jobs[job_id]["status"] == "succeeded"
        # Procrastinate tracks the attempt counter on the job row.
        assert connector.jobs[job_id]["attempts"] == 3

    def test_task_failure_state_after_retries_exhausted(self, in_memory_app: App):
        """A task that always raises with ``retry=1`` is invoked twice (initial
        attempt + one retry) and finally lands in ``failed``."""
        calls = {"count": 0}

        @in_memory_app.task(name="always_fails", retry=1)
        def always_fails():
            calls["count"] += 1
            raise RuntimeError("permanent")

        job_id = always_fails.defer()
        _run_worker(in_memory_app)

        connector = _connector(in_memory_app)
        assert calls["count"] == 2
        assert connector.jobs[job_id]["status"] == "failed"

    def test_task_without_retry_is_invoked_once(self, in_memory_app: App):
        calls = {"count": 0}

        @in_memory_app.task(name="no_retry_fail")
        def no_retry_fail():
            calls["count"] += 1
            raise RuntimeError("nope")

        job_id = no_retry_fail.defer()
        _run_worker(in_memory_app)

        connector = _connector(in_memory_app)
        assert calls["count"] == 1
        assert connector.jobs[job_id]["status"] == "failed"


class TestPeriodicTask:
    @time_machine.travel("2024-01-01 03:00 +0000")
    def test_periodic_task_is_deferred_and_run(
        self, in_memory_app: App, capsys: CaptureFixture[str]
    ):
        # First worker pass registers the periodic defer, second runs it.
        _run_worker(in_memory_app)
        _run_worker(in_memory_app)
        assert "A periodic hello at 1704078000!" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Documenting the gap: features from the original brief that do NOT exist on
# main. These are xfail (not skip) so they surface in the report and will start
# failing-loudly (xpass) if such a framework is ever added to this repo.
# ---------------------------------------------------------------------------


class TestAbsentStateMachineFeatures:
    @pytest.mark.xfail(
        reason="No abstract Task model with SUCCESS/WARNING/FAILURE exists in "
        "adit_radis_shared on main; only ExampleJob (PENDING/IN_PROGRESS/DONE).",
        strict=True,
    )
    def test_warning_success_failure_statuses_exist(self):
        statuses = {key for key, _ in ExampleJob.Status.choices}
        assert {"SUCCESS", "WARNING", "FAILURE"}.issubset(statuses)

    @pytest.mark.xfail(
        reason="No Task base class / model is shipped by this library on main.",
        strict=True,
    )
    def test_shared_library_exposes_a_task_base_model(self):
        # If a shared abstract Task model is ever added, import it here.
        from adit_radis_shared.common import models as common_models  # noqa: PLC0415

        assert hasattr(common_models, "QueuedTask") or hasattr(common_models, "ProcessingTask")

    @pytest.mark.xfail(
        reason="No Job<->Task aggregation (failure precedence / state rollup) "
        "exists in adit_radis_shared on main.",
        strict=True,
    )
    def test_job_aggregates_state_from_tasks(self):
        from adit_radis_shared.common import models as common_models  # noqa: PLC0415

        assert hasattr(common_models, "Job") and hasattr(
            common_models.Job, "update_job_state"
        )
