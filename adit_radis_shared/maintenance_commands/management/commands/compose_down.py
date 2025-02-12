from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Stop stack with docker compose"""

    def handle(
        self,
        cleanup: Annotated[bool, Option(help="Remove orphans and volumes")] = False,
        profile: Annotated[list[str], Option(help="Docker Compose profile(s)")] = [],
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        cmd = f"{self.build_compose_cmd(profile)} down"

        if cleanup:
            cmd += " --remove-orphans --volumes"

        self.execute_cmd(cmd, simulate=simulate)
