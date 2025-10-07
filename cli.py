#!/usr/bin/env python3
import os
import shutil
import sys

import typer

from adit_radis_shared.cli import commands
from adit_radis_shared.cli import helper as cli_helper

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]},
    no_args_is_help=True,
)

app.command()(commands.init_workspace)
app.command()(commands.randomize_env_secrets)
app.command()(commands.compose_build)
app.command()(commands.compose_pull)
app.command()(commands.compose_up)
app.command()(commands.compose_down)
app.command()(commands.stack_deploy)
app.command()(commands.stack_rm)
app.command()(commands.lint)
app.command()(commands.format_code)
app.command()(commands.test)
app.command()(commands.shell)
app.command()(commands.show_outdated)
app.command()(commands.db_backup)
app.command()(commands.db_restore)
app.command()(commands.generate_auth_token)
app.command()(commands.generate_secure_password)
app.command()(commands.generate_django_secret_key)
app.command()(commands.generate_certificate_chain)
app.command()(commands.generate_certificate_files)
app.command()(commands.upgrade_postgres_volume)
app.command()(commands.try_github_actions)


@app.command()
def copy_statics():
    """Copy statics to Django's static folder"""

    helper = cli_helper.CommandHelper()

    print("Copying statics...")
    target_folder = helper.root_path / "adit_radis_shared" / "common" / "static" / "vendor"

    if not target_folder.exists():
        sys.exit(f"Missing target folder {target_folder}")

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            print(f"Copying {file} to {target_folder}")
            shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
            print(f"Copying {file} to {target_file}")
            shutil.copy(file, target_file)

    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js")
    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js.map")
    copy_file("node_modules/bootstrap/dist/css/bootstrap.css")
    copy_file("node_modules/bootstrap/dist/css/bootstrap.css.map")
    copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
    copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
    copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
    copy_file("node_modules/htmx.org/dist/htmx.js")
    copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
    copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")


if __name__ == "__main__":
    app()
