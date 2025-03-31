#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import os
import shutil
import sys

import argcomplete

from adit_radis_shared.cli import commands
from adit_radis_shared.cli import helper as cli_helper


def register_copy_statics(subparsers: argparse._SubParsersAction):
    def call(**kwargs):
        parser = argparse.ArgumentParser(description="Copy statics for the project")
        parser.parse_args()

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
        copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
        copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
        copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
        copy_file("node_modules/htmx.org/dist/htmx.js")
        copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
        copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")

    parser = subparsers.add_parser(
        "copy_statics",
        help="Copy statics for the project",
    )
    parser.set_defaults(func=call)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    commands.register_compose_up(subparsers)
    commands.register_compose_down(subparsers)
    commands.register_db_backup(subparsers)
    commands.register_db_restore(subparsers)
    commands.register_format_code(subparsers)
    commands.register_generate_auth_token(subparsers)
    commands.register_generate_certificate_chain(subparsers)
    commands.register_generate_certificate_files(subparsers)
    commands.register_generate_django_secret_key(subparsers)
    commands.register_generate_secure_password(subparsers)
    commands.register_init_workspace(subparsers)
    commands.register_lint(subparsers)
    commands.register_randomize_env_secrets(subparsers)
    commands.register_shell(subparsers)
    commands.register_show_outdated(subparsers)
    commands.register_stack_deploy(subparsers)
    commands.register_stack_rm(subparsers)
    commands.register_test(subparsers)
    commands.register_try_github_actions(subparsers)
    commands.register_upgrade_postgres_volume(subparsers)

    register_copy_statics(subparsers)

    argcomplete.autocomplete(parser)
    args, extra_args = parser.parse_known_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(**vars(args), extra_args=extra_args)
