import asyncio
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from functools import partial

from asgiref.sync import SyncToAsync
from channels.routing import get_default_application
from daphne.testing import DaphneProcess
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.exceptions import ImproperlyConfigured
from django.db import connections, models
from django.test.utils import modify_settings
from playwright.sync_api import Locator, Page, Response
from procrastinate.contrib.django import app

from adit_radis_shared.accounts.factories import GroupFactory, UserFactory
from adit_radis_shared.accounts.models import User


class ForkSafeDaphneProcess(DaphneProcess):
    """DaphneProcess that resets state inherited through fork.

    The test process may fork while:

    - An event loop is marked as "running" in the forking thread (Playwright's
      sync API keeps one suspended in a greenlet for the whole session). The
      child inherits that marker and Daphne's reactor would refuse to start its
      own loop with "Cannot run the event loop while another loop is running".
    - asgiref's process-wide single-thread executor has a started worker
      thread (any earlier async test using ``sync_to_async`` starts it).
      Worker threads don't survive the fork, but the executor's bookkeeping
      does, so anything the child submits to it (e.g. ``database_sync_to_async``
      in a consumer) would queue up for a thread that doesn't exist and block
      forever.
    """

    def run(self) -> None:
        asyncio.events._set_running_loop(None)
        SyncToAsync.single_thread_executor = ThreadPoolExecutor(max_workers=1)
        super().run()


class ChannelsLiveServer:
    host = "localhost"
    ProtocolServerProcess = ForkSafeDaphneProcess
    static_wrapper = ASGIStaticFilesHandler
    serve_static = True

    def __init__(self) -> None:
        for connection in connections.all():
            if connection.vendor == "sqlite" and connection.is_in_memory_db():  # type: ignore
                raise ImproperlyConfigured(
                    "ChannelsLiveServer can not be used with in memory databases"
                )

        self._live_server_modified_settings = modify_settings(ALLOWED_HOSTS={"append": self.host})
        self._live_server_modified_settings.enable()

        get_application = partial(
            self._make_application,
            static_wrapper=self.static_wrapper if self.serve_static else None,
        )

        self._server_process = self.ProtocolServerProcess(self.host, get_application)
        self._server_process.start()
        self._server_process.ready.wait()
        self._port = self._server_process.port.value

    def stop(self) -> None:
        self._server_process.terminate()
        self._server_process.join()
        self._live_server_modified_settings.disable()

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self._port}"

    def _make_application(self, *, static_wrapper):
        # Module-level function for pickle-ability
        application = get_default_application()
        if static_wrapper is not None:
            application = static_wrapper(application)
        return application


def add_permission(
    user_or_group: User | Group,
    model_or_app_label: str | type[models.Model],
    codename: str,
):
    if isinstance(model_or_app_label, str):
        permission = Permission.objects.get(
            content_type__app_label=model_or_app_label, codename=codename
        )
    else:
        content_type = ContentType.objects.get_for_model(model_or_app_label)
        permission = Permission.objects.get(content_type=content_type, codename=codename)
    if isinstance(user_or_group, User):
        user_or_group.user_permissions.add(permission)
    else:
        user_or_group.permissions.add(permission)


def add_user_to_group(user: User, group: Group, force_activate_group: bool = False):
    user.groups.add(group)
    if not user.active_group or force_activate_group:
        user.change_active_group(group)


def run_worker_once() -> None:
    """Process all queued Procrastinate jobs, then return.

    The worker always runs in a dedicated thread so it never depends on (or
    tries to re-enter) an event loop of the calling thread. Playwright's sync
    API keeps an event loop marked as "running" in the test thread for the
    whole session, so neither asyncio.run() nor loop.run_until_complete()
    could be used here directly.
    """
    errors: list[BaseException] = []

    # The Django connector cannot run a worker itself and builds one via
    # get_worker_connector(). Every other connector -- the one that call
    # returns, or the in-memory connector used in tests -- already can, and
    # offers no such method, so it is used as is.
    build_worker_connector = getattr(app.connector, "get_worker_connector", None)
    connector = build_worker_connector() if build_worker_connector else app.connector

    def _run_worker() -> None:
        try:
            with app.replace_connector(connector):
                app.run_worker(
                    wait=False,
                    install_signal_handlers=False,
                    listen_notify=False,
                    delete_jobs="always",
                )
        except BaseException as err:  # re-raised in the calling thread below
            errors.append(err)

    worker_thread = threading.Thread(target=_run_worker, name="procrastinate-test-worker")
    worker_thread.start()
    worker_thread.join()

    if errors:
        raise errors[0]


def login_user(page: Page, server_url: str, username: str, password: str):
    page.goto(server_url + "/accounts/login")
    page.get_by_label("Username").fill(username)
    page.get_by_label("Password").fill(password)
    page.get_by_text("Log in").click()


def create_and_login_example_user(page: Page, server_url: str):
    password = "my_secret_secret"
    user = UserFactory(password=password)
    login_user(page, server_url, user.username, password)
    return user


def create_token_authentication_group():
    group = GroupFactory.create(name="Radiologists")
    add_permission(group, "token_authentication", "add_token")
    add_permission(group, "token_authentication", "delete_token")
    add_permission(group, "token_authentication", "view_token")
    return group


def poll_locator(
    locator: Locator,
    func: Callable[[Locator], Response | None] = lambda loc: loc.page.reload(),
    interval: int = 1_500,
    timeout: int = 15_000,
):
    start_time = time.time()
    while True:
        try:
            locator.wait_for(timeout=interval)
            return locator
        except Exception as err:
            elapsed_time = (time.time() - start_time) * 1000
            if elapsed_time > timeout:
                raise err

        func(locator)
