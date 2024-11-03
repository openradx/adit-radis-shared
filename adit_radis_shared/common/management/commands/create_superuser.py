import os

from django.core.management.base import BaseCommand

from adit_radis_shared.accounts.models import User
from adit_radis_shared.token_authentication.factories import TokenFactory
from adit_radis_shared.token_authentication.models import FRACTION_LENGTH
from adit_radis_shared.token_authentication.utils.crypto import hash_token


class Command(BaseCommand):
    help = "Creates a superuser account from environment variables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Create another superuser even if one already exists.",
        )

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists() and not options["force"]:
            self.stdout.write("A superuser already exists. Skipping superuser creation.")
            return

        username = os.environ.get("SUPERUSER_USERNAME")
        email = os.environ.get("SUPERUSER_EMAIL")
        password = os.environ.get("SUPERUSER_PASSWORD")

        msg = "No %s in environment. Skipping superuser creation."
        if not username:
            self.stdout.write(msg % "SUPERUSER_USERNAME")
            return
        if not email:
            self.stdout.write(msg % "SUPERUSER_EMAIL")
            return
        if not password:
            self.stdout.write(msg % "SUPERUSER_PASSWORD")
            return

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                f"A user with username '{username}' already exists. Skipping superuser creation."
            )
            return

        self.stdout.write(f"Creating superuser with username '{username}'...", ending="")
        self.stdout.flush()
        superuser = User.objects.create_superuser(username, email, password)
        self.stdout.write("Done")

        auth_token = os.environ.get("SUPERUSER_AUTH_TOKEN")
        if not auth_token:
            self.stdout.write(
                "No SUPERUSER_AUTH_TOKEN in environment. Skipping auth token creation of superuser."
            )
            return

        self.stdout.write(f"Creating auth token for superuser '{username}'...", ending="")
        self.stdout.flush()
        TokenFactory.create(
            token_hashed=hash_token(auth_token),
            fraction=auth_token[:FRACTION_LENGTH],
            owner=superuser,
            expires=None,
        )
        self.stdout.write("Done")
