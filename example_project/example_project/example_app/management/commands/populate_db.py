from os import environ
from typing import Any

from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from adit_radis_shared.accounts.factories import AdminUserFactory, GroupFactory, UserFactory
from adit_radis_shared.accounts.models import User
from adit_radis_shared.token_authentication.factories import TokenFactory
from adit_radis_shared.token_authentication.models import FRACTION_LENGTH
from adit_radis_shared.token_authentication.utils.crypto import hash_token

USER_COUNT = 20
GROUP_COUNT = 3

fake = Faker()


def create_admin() -> User:
    if "ADMIN_USERNAME" not in environ or "ADMIN_PASSWORD" not in environ:
        print("Cave! No admin credentials found in environment. Using default ones.")

    admin = AdminUserFactory.create(
        username=environ.get("ADMIN_USERNAME", "admin"),
        first_name=environ.get("ADMIN_FIRST_NAME", "Wilhelm"),
        last_name=environ.get("ADMIN_LAST_NAME", "Röntgen"),
        email=environ.get("ADMIN_EMAIL", "wilhelm.roentgen@example.org"),
        password=environ.get("ADMIN_PASSWORD", "mysecret"),
    )

    if "ADMIN_AUTH_TOKEN" not in environ:
        print("No admin auth token in environment. Skipping auth token creation.")
    else:
        auth_token = environ["ADMIN_AUTH_TOKEN"]
        TokenFactory.create(
            token_hashed=hash_token(auth_token),
            fraction=auth_token[:FRACTION_LENGTH],
            owner=admin,
            expires=None,
        )

    return admin


def create_users() -> list[User]:
    admin = create_admin()

    users = [admin]

    user_count = USER_COUNT - 1  # -1 for admin
    for i in range(user_count):
        user = UserFactory.create()
        users.append(user)

    return users


def create_groups(users: list[User]) -> list[Group]:
    groups: list[Group] = []

    for _ in range(GROUP_COUNT):
        group = GroupFactory.create()
        groups.append(group)

    for user in users:
        group: Group = fake.random_element(elements=groups)
        user.groups.add(group)
        if not user.active_group:
            user.change_active_group(group)

    return groups


class Command(BaseCommand):
    help = "Populates the database with example data."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--reset", action="store_true", help="Reset the database.")

    def handle(self, *args: Any, **options: Any) -> str | None:
        if options["reset"]:
            print("Resetting database.")
            # Can only be done when dev server is not running and needs django_extensions installed
            call_command("reset_db", "--noinput")
            call_command("migrate")

        do_populate = True
        if User.objects.count() > 0:
            print("Development database already populated. Skipping.")
            do_populate = False

        if do_populate:
            print("Populating development database with test data.")

            users = create_users()
            print(f"Created {len(users)} users.")

            groups = create_groups(users)
            print(f"Created {len(groups)} groups.")
