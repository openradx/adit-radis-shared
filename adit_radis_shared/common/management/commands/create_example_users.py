from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from adit_radis_shared.accounts.factories import UserFactory
from adit_radis_shared.accounts.models import User

fake = Faker()


class Command(BaseCommand):
    help = "Creates example users in the database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--count", type=int, default=20, help="Number of example users to create."
        )

    def handle(self, *args: Any, **options: Any) -> str | None:
        if User.objects.filter(is_superuser=False).exists():
            self.stdout.write("Database already populated with example users. Skipping.")
            return

        count = options["count"]

        self.stdout.write(f"Creating {count} example users...", ending="")
        self.stdout.flush()

        if count < 1:
            self.stderr.write("User count must be at least 1. Skipping.\n")
            return

        for _ in range(count):
            UserFactory.create(username=fake.unique.user_name())

        self.stdout.write("Done")
