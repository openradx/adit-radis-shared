import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand
from procrastinate.contrib.django import app


class Command(BaseCommand):
    help = "Retry stalled jobs in the procrastinate queue."

    async def handle_retry_stalled_jobs(self):
        stalled_jobs = await app.job_manager.get_stalled_jobs()

        priority: int = settings.STALLED_JOBS_RETRY_PRIORITY

        stalled_jobs_num = 0
        for job in stalled_jobs:
            await app.job_manager.retry_job(job, priority=priority)
            stalled_jobs_num += 1

        return stalled_jobs_num

    def handle(self, *args, **options):
        self.stdout.write("Retrying stalled jobs... ", ending="")
        self.stdout.flush()

        stalled_jobs_num = asyncio.run(self.handle_retry_stalled_jobs())
        if stalled_jobs_num == 0:
            self.stdout.write("No stalled jobs found")
        elif stalled_jobs_num == 1:
            self.stdout.write("Found 1 stalled job")
        else:
            self.stdout.write(f"Found {stalled_jobs_num} stalled jobs")
