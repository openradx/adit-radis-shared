from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from example_project.example_app.factories import ExampleJobFactory
from example_project.example_app.models import ExampleJob

fake = Faker()


class Command(BaseCommand):
    help = "Creates example jobs in the database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--count", type=int, default=500, help="Number of example jobs to create."
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        if ExampleJob.objects.exists():
            self.stdout.write("Database already populated with example jobs. Skipping.")
            return

        count = options["count"]
        if count < 1:
            raise ValueError("ExampleJob count must be at least 1.")

        self.stdout.write(f"Creating {count} example jobs...", ending="")
        self.stdout.flush()

        for _ in range(count):
            ExampleJobFactory.create()

        self.stdout.write("Done")
