import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Remove stack from docker swarm")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()
    helper.execute_cmd(f"docker stack rm {helper.get_stack_name()}")
