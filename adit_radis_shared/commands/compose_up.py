import argparse
import sys

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    build: bool
    profile: list[str]


def call():
    parser = argparse.ArgumentParser(description="Start stack with docker compose")
    parser.add_argument("--build", action="store_true", help="Build images before starting")
    parser.add_argument("--profile", action="append", help="Docker compose profile(s) to use")
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()
    helper.prepare_environment()

    if helper.is_production():
        sys.exit(
            "Starting containers with compose-up can only be used in development. "
            "Check ENVIRONMENT setting in .env file."
        )

    if args.build:
        cmd = f"{helper.build_compose_cmd()} build"
        cmd += f" --build-arg PROJECT_VERSION={helper.get_project_version()}-local"
        helper.execute_cmd(cmd)

    cmd = f"{helper.build_compose_cmd(args.profile)} up --no-build --detach"
    helper.execute_cmd(cmd)
