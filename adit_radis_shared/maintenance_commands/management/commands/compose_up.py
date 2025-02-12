from typing import Annotated

from typer import Exit, Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Start stack with docker compose"""

    def handle(
        self,
        no_build: Annotated[bool, Option(help="Do not build images")] = False,
        profile: Annotated[list[str], Option(help="Docker Compose profile(s)")] = [],
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        self.prepare_environment()

        if self.force_swarm_mode_in_production:
            if self.is_production():
                print(
                    "Starting containers with compose-up can only be used in development. "
                    "Check ENVIRONMENT setting in .env file."
                )
                raise Exit(1)

        version = self.get_latest_local_version_tag()
        if not self.is_production():
            version += "-dev"

        cmd = f"{self.build_compose_cmd(profile)} up"

        if no_build:
            cmd += " --no-build"

        cmd += " --detach"
        self.execute_cmd(cmd, env={"PROJECT_VERSION": version}, simulate=simulate)
