import argparse

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    length: int


def call():
    parser = argparse.ArgumentParser(description="Generate a secure password")
    parser.add_argument(
        "--length", type=int, default=12, help="Length of the password (default: 12)"
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()

    print(helper.generate_secure_password(args.length))
