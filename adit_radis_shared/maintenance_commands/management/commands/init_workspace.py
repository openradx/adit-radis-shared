import os
import shutil

from dotenv import set_key
from typer import Exit

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Initialize workspace for Github Codespaces or local development"""

    def handle(self):
        env_file = self.project_path / ".env"
        if env_file.is_file():
            print("Workspace already initialized (.env file exists).")
            raise Exit(1)

        shutil.copy(self.project_path / "example.env", env_file)

        def modify_env_file(domain: str | None = None, uses_https: bool = False):
            if domain:
                hosts = f".localhost,127.0.0.1,[::1],{domain}"
                set_key(env_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
                set_key(env_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
                set_key(env_file, "SITE_DOMAIN", domain, quote_mode="never")

                origin = f"{'https' if uses_https else 'http'}://{domain}"
                set_key(env_file, "DJANGO_CSRF_TRUSTED_ORIGINS", origin, quote_mode="never")

            set_key(env_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

        if os.environ.get("CODESPACE_NAME"):
            # Inside GitHub Codespaces
            domain = f"{os.environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
            modify_env_file(domain, uses_https=True)
        elif os.environ.get("GITPOD_WORKSPACE_ID"):
            # Inside Gitpod
            result = self.capture_cmd("gp url 8000")
            domain = result.strip().removeprefix("https://")
            modify_env_file(domain, uses_https=True)
        else:
            # Inside some local environment
            modify_env_file()

        print("Successfully initialized .env file.")
