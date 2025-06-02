#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse
import os
import shutil
import sys

from adit_radis_shared.cli import helper as cli_helper
from adit_radis_shared.cli import parsers
from adit_radis_shared.cli.setup import setup_root_parser


def copy_statics(**kwargs):
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
    root_parser = argparse.ArgumentParser()
    subparsers = root_parser.add_subparsers(dest="command")

    parsers.register_compose_build(subparsers)
    parsers.register_compose_watch(subparsers)
    parsers.register_compose_up(subparsers)
    parsers.register_compose_down(subparsers)
    parsers.register_compose_pull(subparsers)
    parsers.register_db_backup(subparsers)
    parsers.register_db_restore(subparsers)
    parsers.register_format_code(subparsers)
    parsers.register_generate_auth_token(subparsers)
    parsers.register_generate_certificate_chain(subparsers)
    parsers.register_generate_certificate_files(subparsers)
    parsers.register_generate_django_secret_key(subparsers)
    parsers.register_generate_secure_password(subparsers)
    parsers.register_init_workspace(subparsers)
    parsers.register_lint(subparsers)
    parsers.register_randomize_env_secrets(subparsers)
    parsers.register_shell(subparsers)
    parsers.register_show_outdated(subparsers)
    parsers.register_stack_deploy(subparsers)
    parsers.register_stack_rm(subparsers)
    parsers.register_test(subparsers)
    parsers.register_try_github_actions(subparsers)
    parsers.register_upgrade_postgres_volume(subparsers)

    parser = subparsers.add_parser("copy-statics", help="Copy statics for the project")
    parser.set_defaults(func=copy_statics)

    setup_root_parser(root_parser)
