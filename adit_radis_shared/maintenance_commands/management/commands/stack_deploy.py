from typing import Annotated

from typer import Exit, Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Deploy stack with docker swarm"""

    def handle(
        self,
        build: Annotated[bool, Option(help="Build images")] = False,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        self.prepare_environment()

        config = self.load_config_from_env_file()
        if config.get("ENVIRONMENT") != "production":
            print(
                "stack-deploy task can only be used in production environment. "
                "Check ENVIRONMENT setting in .env file."
            )
            raise Exit(1)

        if build:
            cmd = f"{self.build_compose_cmd()} build"
            self.execute_cmd(cmd, simulate=simulate)

        version = self.get_latest_local_version_tag()
        if not self.is_production():
            version += "-dev"

        # Docker Swarm Mode does not support .env files so we load the .env file manually
        # and pass the content as an environment variables.
        env = self.load_config_from_env_file()

        env["PROJECT_VERSION"] = version

        cmd = "docker stack deploy --detach "
        cmd += f" -c {self.get_compose_base_file()}"
        cmd += f" -c {self.get_compose_env_file()}"
        cmd += f" {self.get_stack_name()}"
        self.execute_cmd(cmd, env=env, simulate=simulate)
