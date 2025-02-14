#! /usr/bin/env python3

import os
import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer

from adit_radis_shared import cli_commands as commands
from adit_radis_shared import cli_helpers as helpers

helpers.PROJECT_ID = "example_project"
helpers.ROOT_PATH = Path(__file__).resolve().parent

app = typer.Typer()

extra_args = {"allow_extra_args": True, "ignore_unknown_options": True}

app.command()(commands.init_workspace)
app.command()(commands.compose_up)
app.command()(commands.compose_down)
app.command()(commands.stack_deploy)
app.command()(commands.stack_rm)
app.command()(commands.lint)
app.command()(commands.format_code)
app.command(context_settings=extra_args)(commands.test)
app.command()(commands.show_outdated)
app.command()(commands.backup_db)
app.command()(commands.restore_db)
app.command()(commands.shell)
app.command()(commands.generate_certificate_files)
app.command()(commands.generate_certificate_chain)
app.command()(commands.generate_django_secret_key)
app.command()(commands.generate_secure_password)
app.command()(commands.generate_auth_token)
app.command()(commands.randomize_env_secrets)
app.command()(commands.try_github_actions)


@app.command()
def copy_statics(
    simulate: Annotated[bool, typer.Option(help="Simulate the command")] = False,
):
    """Start stack with docker compose"""

    print("Copying statics...")
    target_folder = helpers.get_root_path() / "adit_radis_shared" / "common" / "static" / "vendor"

    if not target_folder.exists():
        sys.exit(f"Missing target folder {target_folder}")

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            print(f"Copying {file} to {target_folder}")
            if not simulate:
                shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
            print(f"Copying {file} to {target_file}")
            if not simulate:
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


if __name__ == "__main__":
    app()
