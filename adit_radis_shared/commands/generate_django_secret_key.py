import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Generate a Django secret key")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    print(helper.generate_django_secret_key())
