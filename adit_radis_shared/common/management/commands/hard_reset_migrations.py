from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Reset all migration files (dangerous!!!)."

    def handle(self, *args, **options):
        self.stdout.write("Resetting migrations...", ending="")
        self.stdout.flush()

        source_paths: list[Path] = settings.SOURCE_PATHS
        for source_path in source_paths:
            migration_paths = source_path.glob("*/migrations/**/*.py")
            migration_paths = [i for i in migration_paths if i.name != "__init__.py"]
            for migration_path in migration_paths:
                migration_path.unlink()

            pyc_paths = source_path.glob("*/migrations/**/*.pyc")
            for pyc_path in pyc_paths:
                pyc_path.unlink()

        call_command("reset_db", "--noinput")  # needs django_extensions installed
        call_command("makemigrations")
        call_command("migrate")

        self.stdout.write("Done")
