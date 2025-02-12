from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Generate a Django secret key"""

    def handle(self):
        print(self.generate_django_secret_key())
