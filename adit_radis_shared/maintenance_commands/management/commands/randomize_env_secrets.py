from dotenv import set_key
from typer import Exit

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Randomize secrets in the .env file"""

    def handle(self):
        env_file = self.root_path / ".env"
        if not env_file.is_file():
            print("Workspace not initialized (.env file does not exist).")
            raise Exit(1)

        set_key(env_file, "DJANGO_SECRET_KEY", self.generate_django_secret_key())
        set_key(env_file, "POSTGRES_PASSWORD", self.generate_secure_password())
        set_key(env_file, "ADMIN_USER_PASSWORD", self.generate_secure_password())
        set_key(env_file, "ADMIN_AUTH_TOKEN", self.generate_auth_token())
