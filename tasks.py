import os
import shutil
from pathlib import Path

from invoke.context import Context
from invoke.tasks import task

from adit_radis_shared import invoke_tasks
from adit_radis_shared.invoke_tasks import (  # noqa: F401
    Utility,
    compose_down,
    compose_up,
    format,
    generate_auth_token,
    generate_certificate_files,
    generate_django_secret_key,
    generate_secure_password,
    init_workspace,
    lint,
    randomize_env_secrets,
    reset_dev,
    show_outdated,
    stack_deploy,
    stack_rm,
    test,
    try_github_actions,
    web_shell,
)

invoke_tasks.PROJECT_NAME = "example_project"
invoke_tasks.PROJECT_DIR = Path(__file__).resolve().parent


@task
def copy_statics(ctx: Context):
    """Copy JS and CSS dependencies from node_modules to static vendor folder"""
    print("Copying statics...")

    target_folder = Utility.get_project_dir() / "adit_radis_shared" / "common" / "static" / "vendor"

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
            shutil.copy(file, target_file)

    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js")
    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js.map")
    copy_file("node_modules/bootswatch/dist/flatly/bootstrap.css")
    copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
    copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
    copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
    copy_file("node_modules/htmx.org/dist/htmx.js")
    copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
    copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")
