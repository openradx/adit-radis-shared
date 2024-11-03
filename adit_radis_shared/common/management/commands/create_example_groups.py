from typing import Any

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandParser
from environ import sys
from faker import Faker

from adit_radis_shared.accounts.factories import GroupFactory
from adit_radis_shared.accounts.models import User

fake = Faker()

PREDEFINED_GROUPS = [
    "Thoraxklinik",
    "Allgemeinradiologie",
    "Neuroradiologie",
    "Studienzentrum",
]


class Command(BaseCommand):
    help = "Create example groups in the database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--count", type=int, default=3, help="Number of groups to create.")

    def handle(self, *args: Any, **options: Any) -> str | None:
        if Group.objects.count() > 0:
            self.stdout.write("Database already populated with example groups. Skipping.")
            return

        count = options["count"]
        if count < 1:
            sys.stderr.write("Group count must be at least 1. Skipping.\n")
            return

        groups: list[Group] = []
        for i in range(count):
            if i < len(PREDEFINED_GROUPS):
                group_name = PREDEFINED_GROUPS[i]
                group = GroupFactory.create(name=group_name)
            else:
                group = GroupFactory.create()
            groups.append(group)

        superusers = list(User.objects.filter(is_superuser=True))
        # Add a superuser to all groups and make the first one the active group
        for superuser in superusers:
            for group in groups:
                superuser.groups.add(group)
            superuser.change_active_group(groups[0])

        # Add all users to a random group and make it the active group
        users = list(User.objects.filter(is_superuser=False))
        for user in users:
            group: Group = fake.random_element(elements=groups)
            user.groups.add(group)
            user.change_active_group(group)

        self.stdout.write(f"Created {count} example groups and assigned users to them.")
