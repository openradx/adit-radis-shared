import argparse

import argcomplete

from .helper import CommandHelper


class Namespace:
    length: int


def call():
    parser = argparse.ArgumentParser(description="Generate an authentication token")
    parser.add_argument(
        "--length",
        type=int,
        default=20,
        help="Length of the token (default: 20)",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()

    print(helper.generate_auth_token(args.length))
