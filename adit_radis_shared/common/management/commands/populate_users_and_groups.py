from os import environ
from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from faker import Faker

from adit_radis_shared.accounts.factories import AdminUserFactory, GroupFactory, UserFactory
from adit_radis_shared.accounts.models import User
from adit_radis_shared.token_authentication.factories import TokenFactory
from adit_radis_shared.token_authentication.models import FRACTION_LENGTH
from adit_radis_shared.token_authentication.utils.crypto import hash_token

fake = Faker()

PREDFINED_GROUPS = [
    "Thoraxklinik",
    "Allgemeinradiologie",
    "Neuroradiologie",
    "Studienzentrum",
]


def create_admin() -> User | None:
    if "ADMIN_USERNAME" not in environ or "ADMIN_PASSWORD" not in environ:
        print("Cave! No admin credentials found in environment. Skipping admin creation.")
        return None
    else:
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


def create_users(users_count: int) -> list[User]:
    users: list[User] = []
    for i in range(users_count):
        if i == 0:
            user = create_admin()
        else:
            user = UserFactory.create(username=fake.unique.user_name())

        if user is not None:
            users.append(user)

    return users


def create_groups(users: list[User], groups_count: int) -> list[Group]:
    groups: list[Group] = []

    for i in range(groups_count):
        if i < len(PREDFINED_GROUPS):
            group_name = PREDFINED_GROUPS[i]
            group = GroupFactory.create(name=group_name)
        else:
            group = GroupFactory.create()
        groups.append(group)

    # Add admin to all groups and make the first one active
    admin = users[0]
    for group in groups:
        admin.groups.add(group)
        if not admin.active_group:
            admin.change_active_group(group)

    # Add all users to a random group and make it active
    for user in users[1:]:
        group: Group = fake.random_element(elements=groups)
        user.groups.add(group)
        if not user.active_group:
            user.change_active_group(group)

    return groups


class Command(BaseCommand):
    help = "Populates the database with an admin user, example users and example groups."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--users", type=int, default=20, help="Number of users to generate.")
        parser.add_argument("--groups", type=int, default=3, help="Number of groups to generate.")

    def handle(self, *args: Any, **options: Any) -> str | None:
        do_populate = True
        if User.objects.count() > 0:
            print("Development database already populated with example users and groups. Skipping.")
            do_populate = False

        if do_populate:
            print("Populating development database with example users and groups.")

            users = create_users(options["users"])
            print(f"Created {len(users)} users.")

            groups = create_groups(users, options["groups"])
            print(f"Created {len(groups)} groups.")
