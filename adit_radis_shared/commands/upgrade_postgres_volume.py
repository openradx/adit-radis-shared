import argparse

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    version: str


def call():
    parser = argparse.ArgumentParser(description="Upgrade PostgreSQL volume data")
    parser.add_argument(
        "--version",
        type=str,
        default="latest",
        help="PostgreSQL version to upgrade to (default: latest)",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()

    volume = f"{helper.get_stack_name()}_postgres_data"
    print(f"Upgrading PostgreSQL database in volume {volume} environment to {args.version}.")
    print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
    if helper.confirm("Are you sure you want to proceed?"):
        print("Starting docker container that upgrades the database files.")
        print("Watch the output if everything went fine or if any further steps are necessary.")
        helper.execute_cmd(
            f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
            f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{args.version}"
        )
    else:
        print("Cancelled")
