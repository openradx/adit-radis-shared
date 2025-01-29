import time_machine
from procrastinate.app import App
from pytest import CaptureFixture

from example_project.example_app.tasks import example_task


def test_example_task(in_memory_app: App, capsys: CaptureFixture[str]):
    job_id = example_task.defer()

    jobs = in_memory_app.job_manager.list_jobs()
    assert len(list(jobs)) == 1

    in_memory_app.run_worker(
        wait=False, install_signal_handlers=False, listen_notify=False, delete_jobs="always"
    )

    jobs = in_memory_app.job_manager.list_jobs()
    assert len(list(jobs)) == 0

    captured = capsys.readouterr()
    assert f"Hello from job {job_id}" in captured.out


@time_machine.travel("2024-01-01 03:00 +0000")
def test_periodic_example_task(in_memory_app: App, capsys: CaptureFixture[str]):
    # The first run creates the periodic job
    in_memory_app.run_worker(
        wait=False, install_signal_handlers=False, listen_notify=False, delete_jobs="always"
    )
    # The second one runs the periodic job
    in_memory_app.run_worker(
        wait=False, install_signal_handlers=False, listen_notify=False, delete_jobs="always"
    )

    captured = capsys.readouterr()
    assert "A periodic hello at 1704078000!" in captured.out
