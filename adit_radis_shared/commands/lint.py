import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(
        description="Lint the source code with ruff, pyright and djlint"
    )
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    print("Linting Python code with ruff...")
    helper.execute_cmd("uv run ruff check .")

    print("Linting Python code with pyright...")
    helper.execute_cmd("uv run pyright")

    print("Linting Django templates with djlint...")
    helper.execute_cmd("uv run djlint . --lint")
