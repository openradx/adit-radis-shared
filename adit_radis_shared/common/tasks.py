import logging

from django.conf import settings
from django.core.mail import send_mail
from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


@app.task
def broadcast_mail(recipients: list[str], subject: str, message: str):
    send_mail(subject, message, settings.SUPPORT_EMAIL, recipients)
    logger.info("Successfully sent an Email to %d recipents.", len(recipients))
