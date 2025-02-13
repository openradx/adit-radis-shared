from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Generate an authentication token"""

    def handle(
        self,
        length: Annotated[int, Option(help="Length of the token")] = 20,
    ):
        print(self.generate_auth_token(length))
