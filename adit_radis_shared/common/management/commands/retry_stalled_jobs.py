import asyncio
import logging

from asgiref.sync import sync_to_async
from django.apps import apps
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


## some helper functions
def get_task_models():
    task_models = []
    for model in apps.get_models():
        if hasattr(model, "Status") and hasattr(model, "queued_job_id"):
            if hasattr(model.Status, "PENDING") and hasattr(model.Status, "IN_PROGRESS"):  # type: ignore
                task_models.append(model)
    return task_models


def reset_task_state(task) -> None:
    pending_status = getattr(task.Status, "PENDING", "PENDING")
    task.status = pending_status
    task.attempts = (task.attempts or 0) + 1
    task.message = "Recovered from stalled state"
    if hasattr(task, "start"):
        task.start = None
        task.end = None
    elif hasattr(task, "started_at"):
        task.started_at = None
        task.ended_at = None
    task.save()


def update_job_status(task) -> None:
    job = getattr(task, "job", None)
    if job:
        if hasattr(job, "update_job_state"):  # RADIS
            job.update_job_state()
        else:  # ADIT
            pending_job_status = getattr(job.Status, "PENDING", "PENDING")
            in_progress_status = getattr(job.Status, "IN_PROGRESS", "PENDING")
            if (
                job.status == in_progress_status
                and not job.tasks.filter(status=in_progress_status).exists()
            ):
                job.status = pending_job_status
                job.save()


class Command(BaseCommand):
    help = "Retry stalled jobs in the procrastinate queue."

    async def handle_retry_stalled_jobs(self) -> tuple[int, int]:
        stalled_jobs = await app.job_manager.get_stalled_jobs()

        if not stalled_jobs:
            return 0, 0

        job_ids = {job.id: job for job in stalled_jobs}
        tasks_recovered = 0
        failed_tasks = 0

        # Get all task models by checking for required attributes
        task_models = get_task_models()

        for task_model in task_models:
            tasks = await sync_to_async(list)(
                task_model.objects.filter(queued_job_id__in=job_ids.keys()).select_related("job")
            )

            for task in tasks:
                stalled_job = job_ids.get(getattr(task, "queued_job_id", None))
                if not stalled_job:
                    continue

                try:
                    # Reset task state in transaction
                    await sync_to_async(self._reset_task_state)(task)

                    # Retry the job after state is committed (already in async context)
                    retry_priority = getattr(settings, "STALLED_JOBS_RETRY_PRIORITY", 0)
                    await app.job_manager.retry_job(stalled_job, priority=retry_priority)
                    logger.info(f"Retried stalled job {stalled_job.id}")

                    tasks_recovered += 1
                except Exception as e:
                    logger.error(f"Failed to recover task {task.id} (job {stalled_job.id}): {e}")
                    failed_tasks += 1

        # Check if any procrastinate jobs are still stalled without corresponding tasks
        orphaned = len(job_ids) - tasks_recovered - failed_tasks

        return tasks_recovered, orphaned

    @transaction.atomic
    def _reset_task_state(self, task) -> None:
        reset_task_state(task)
        update_job_status(task)

    def handle(self, *args, **options) -> None:
        self.stdout.write("Checking for stalled jobs...")
        tasks_recovered, orphaned = asyncio.run(self.handle_retry_stalled_jobs())

        if tasks_recovered == 0 and orphaned == 0:
            self.stdout.write(self.style.SUCCESS("No stalled jobs found"))
        else:
            msg = f"Recovered {tasks_recovered} tasks"
            if orphaned:
                msg += f", found {orphaned} orphaned jobs"
            self.stdout.write(msg)
