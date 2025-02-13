from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Show outdated dependencies"""

    def handle(self):
        print("### Outdated Python dependencies ###")
        self.execute_cmd("poetry show --outdated --top-level")

        print("### Outdated NPM dependencies ###")
        self.execute_cmd("npm outdated")
