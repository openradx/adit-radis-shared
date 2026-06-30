"""Tests for the small pure helpers under ``common.utils``.

Covered: mail helpers, the HTMX toast trigger, the auth type-guard and the
``iter_over_async`` bridge.
"""

import asyncio
import json

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.http import HttpResponse

from adit_radis_shared.accounts.factories import UserFactory
from adit_radis_shared.common.utils.async_utils import iter_over_async
from adit_radis_shared.common.utils.auth_utils import is_logged_in_user
from adit_radis_shared.common.utils.htmx_triggers import trigger_toast
from adit_radis_shared.common.utils.mail import send_mail_to_admins, send_mail_to_user

# --- mail helpers -----------------------------------------------------------


def test_send_mail_to_admins_requires_some_content():
    with pytest.raises(Exception):
        send_mail_to_admins("Subject")


def test_send_mail_to_admins_sends_with_text_content():
    send_mail_to_admins("Subject", text_content="Body text")
    assert len(mail.outbox) == 1
    assert "Body text" in mail.outbox[0].body


def test_send_mail_to_admins_strips_html_when_no_text():
    send_mail_to_admins("Subject", html_content="<p>Hello <b>admin</b></p>")
    assert len(mail.outbox) == 1
    # HTML is stripped for the plaintext part.
    assert "Hello admin" in mail.outbox[0].body
    assert "<p>" not in mail.outbox[0].body


@pytest.mark.django_db
def test_send_mail_to_user_prefixes_subject_and_targets_user(settings):
    settings.EMAIL_SUBJECT_PREFIX = "[PREFIX] "
    user = UserFactory.create(email="target@example.test")

    send_mail_to_user(user, "Hi", text_content="Body")

    assert len(mail.outbox) == 1
    sent = mail.outbox[0]
    assert sent.subject == "[PREFIX] Hi"
    assert sent.to == ["target@example.test"]


@pytest.mark.django_db
def test_send_mail_to_user_requires_some_content():
    user = UserFactory.create()
    with pytest.raises(Exception):
        send_mail_to_user(user, "Hi")


# --- htmx triggers ----------------------------------------------------------


def test_trigger_toast_creates_response_when_none_given():
    response = trigger_toast(level="warning", title="Heads up", text="Careful")

    assert isinstance(response, HttpResponse)
    assert response.status_code == 200
    payload = json.loads(response.headers["HX-Trigger"])
    assert payload["toast"] == {
        "level": "warning",
        "title": "Heads up",
        "text": "Careful",
    }


def test_trigger_toast_augments_existing_response():
    original = HttpResponse("content", status=201)
    response = trigger_toast(original, level="success", title="Done", text="")

    assert response is original
    assert response.status_code == 201
    payload = json.loads(response.headers["HX-Trigger"])
    assert payload["toast"]["level"] == "success"


# --- auth type guard --------------------------------------------------------


def test_is_logged_in_user_false_for_anonymous():
    assert is_logged_in_user(AnonymousUser()) is False


@pytest.mark.django_db
def test_is_logged_in_user_true_for_real_user():
    user = UserFactory.create()
    assert is_logged_in_user(user) is True


# --- async bridge -----------------------------------------------------------


def test_iter_over_async_yields_all_items_in_order():
    async def agen():
        for i in range(3):
            yield i

    loop = asyncio.new_event_loop()
    try:
        result = list(iter_over_async(agen(), loop))
    finally:
        loop.close()

    assert result == [0, 1, 2]


def test_iter_over_async_handles_empty_iterator():
    async def agen():
        return
        yield  # pragma: no cover - makes this an async generator

    loop = asyncio.new_event_loop()
    try:
        result = list(iter_over_async(agen(), loop))
    finally:
        loop.close()

    assert result == []
