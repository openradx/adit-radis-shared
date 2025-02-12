from typing import Annotated

from typer import Argument

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Open a Python shell in the specified container container"""

    def handle(
        self, container: Annotated[str, Argument(help="Container name ('web' by default)")] = "web"
    ):
        self.execute_cmd(f"{self.build_compose_cmd()} exec {container} python manage.py shell_plus")
