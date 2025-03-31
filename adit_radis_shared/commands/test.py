import argparse
import sys

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Run the test suite with pytest")
    argcomplete.autocomplete(parser)
    extra_args = parser.parse_known_args()[1]

    helper = CommandHelper()

    if not helper.check_compose_up():
        sys.exit("Acceptance tests need dev containers running.")

    cmd = (
        f"{helper.build_compose_cmd()} exec "
        f"--env DJANGO_SETTINGS_MODULE={helper.project_id}.settings.test web pytest "
    )
    cmd += " ".join(extra_args)
    helper.execute_cmd(cmd)
