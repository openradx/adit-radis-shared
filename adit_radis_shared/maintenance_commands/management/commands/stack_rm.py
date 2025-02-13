from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Remove stack from docker swarm"""

    def handle(
        self,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        self.execute_cmd(f"docker stack rm {self.get_stack_name()}", simulate=simulate)
