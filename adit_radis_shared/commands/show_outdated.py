import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Show outdated dependencies")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    print("### Outdated Python dependencies ###")
    helper.print_uv_outdated()

    print("### Outdated NPM dependencies ###")
    helper.execute_cmd("npm outdated", hidden=True)
