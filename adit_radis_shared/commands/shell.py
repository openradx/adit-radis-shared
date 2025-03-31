import argparse

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    container: str


def call():
    parser = argparse.ArgumentParser(description="Open a Python shell in the specified container")
    parser.add_argument(
        "--container", type=str, default="web", help="Container name (default: web)"
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()

    helper.execute_cmd(
        f"{helper.build_compose_cmd()} exec {args.container} python manage.py shell_plus"
    )
