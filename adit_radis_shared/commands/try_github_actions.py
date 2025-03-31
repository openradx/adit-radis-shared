import argparse

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Try Github Actions locally using Act")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    act_path = helper.root_path / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        helper.execute_cmd(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            hidden=True,
        )

    helper.execute_cmd(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest")
