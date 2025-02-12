from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Format the source code with ruff and djlint"""

    def handle(
        self,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        print("Formatting Python code with ruff...")
        self.execute_cmd("poetry run ruff format .", simulate=simulate)

        print("Sorting Python imports with ruff...")
        self.execute_cmd("poetry run ruff check . --fix --select I", simulate=simulate)

        print("Formatting Django templates with djlint...")
        self.execute_cmd("poetry run djlint . --reformat", simulate=simulate)
