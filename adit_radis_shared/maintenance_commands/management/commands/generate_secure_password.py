from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Generate a secure password"""

    def handle(
        self,
        length: Annotated[int, Option(help="Length of the password")] = 12,
    ):
        print(self.generate_secure_password(length))
