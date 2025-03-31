import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Format the source code with ruff and djlint")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    print("Formatting Python code with ruff...")
    helper.execute_cmd("uv run ruff format .")

    print("Sorting Python imports with ruff...")
    helper.execute_cmd("uv run ruff check . --fix --select I")

    print("Formatting Django templates with djlint...")
    helper.execute_cmd("uv run djlint . --reformat")
