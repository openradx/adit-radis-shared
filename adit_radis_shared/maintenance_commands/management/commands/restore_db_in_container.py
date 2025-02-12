from typing import Annotated

from typer import Exit, Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Restore database in container from the last backup"""

    def handle(
        self,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        settings = (
            f"{self.project_name}.settings.production"
            if self.is_production()
            else f"{self.project_name}.settings.development"
        )
        web_container_id = self.find_running_container_id("web")
        if web_container_id is None:
            print("Web container is not running. Run 'poetry run ./manage.py compose_up' first.")
            raise Exit(1)

        self.execute_cmd(
            (
                f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
                f"{web_container_id} ./manage.py dbrestore"
            ),
            simulate=simulate,
        )
