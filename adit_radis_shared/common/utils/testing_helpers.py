import asyncio
import time
from functools import partial
from typing import Callable

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


class ChannelsLiveServer:
    host = "localhost"
    ProtocolServerProcess = DaphneProcess
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


def add_user_to_group(user: User, group: Group):
    user.groups.add(group)
    if not user.active_group:
        user.change_active_group(group)


def run_worker_once() -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    def _run_worker_once_sync() -> None:
        with app.replace_connector(app.connector.get_worker_connector()):  # type: ignore
            app.run_worker(
                wait=False,
                install_signal_handlers=False,
                listen_notify=False,
                delete_jobs="always",
            )

    async def _run_worker_once_async() -> None:
        with app.replace_connector(app.connector.get_worker_connector()):  # type: ignore
            async with app.open_async():
                await app.run_worker_async(
                    wait=False,
                    install_signal_handlers=False,
                    listen_notify=False,
                    delete_jobs="always",
                )

    if loop is None:
        _run_worker_once_sync()
    else:
        loop.run_until_complete(_run_worker_once_async())


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
