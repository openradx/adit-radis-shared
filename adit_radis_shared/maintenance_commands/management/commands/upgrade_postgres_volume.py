from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Upgrade PostgreSQL volume data"""

    def handle(
        self,
        version: Annotated[str, Option(help="PostgreSQL version to upgrade to")] = "latest",
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        volume = f"{self.get_stack_name()}_postgres_data"
        print(f"Upgrading PostgreSQL database in volume {volume} environment to {version}.")
        print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
        if self.confirm("Are you sure you want to proceed?"):
            print("Starting docker container that upgrades the database files.")
            print("Watch the output if everything went fine or if any further steps are necessary.")
            self.execute_cmd(
                f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
                f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}",
                simulate=simulate,
            )
        else:
            print("Cancelled")
