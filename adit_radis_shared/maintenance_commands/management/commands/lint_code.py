from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Lint the source code with ruff, pyright and djlint"""

    def handle(
        self,
    ):
        print("Linting Python code with ruff...")
        self.execute_cmd("poetry run ruff check .")

        print("Linting Python code with pyright...")
        self.execute_cmd("poetry run pyright")

        print("Linting Django templates with djlint...")
        self.execute_cmd("poetry run djlint . --lint")
