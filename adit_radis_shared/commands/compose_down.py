import argparse

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    cleanup: bool
    profile: list[str]


def call():
    parser = argparse.ArgumentParser(description="Stop stack with docker compose")
    parser.add_argument("--cleanup", action="store_true", help="Remove orphans and volumes")
    parser.add_argument("--profile", action="append", help="Docker Compose profile(s)")
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()

    cmd = f"{helper.build_compose_cmd(args.profile)} down"

    if args.cleanup:
        cmd += " --remove-orphans --volumes"

    helper.execute_cmd(cmd)
