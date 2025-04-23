import logging

from django.conf import settings
from django.core.mail import send_mail
from django.core.management import call_command
from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


@app.task
def broadcast_mail(recipients: list[str], subject: str, message: str):
    send_mail(subject, message, settings.SUPPORT_EMAIL, recipients)
    logger.info("Successfully sent an Email to %d recipents.", len(recipients))


@app.periodic(cron="*/10 * * * *")
@app.task(queueing_lock="retry_stalled_jobs")
def retry_stalled_jobs(timestamp: int):
    call_command("retry_stalled_jobs")
