import pytest
from django_test_migrations.migrator import Migrator


@pytest.mark.django_db
def test_0007_convert_institutes_to_groups(migrator_ext: Migrator):
    old_state = migrator_ext.apply_initial_migration(("accounts", "0006_user_active_group"))

    User = old_state.apps.get_model("accounts", "User")
    Institute = old_state.apps.get_model("accounts", "Institute")

    user1 = User.objects.create(
        username="user1",
    )
    user2 = User.objects.create(
        username="user2",
    )
    institute = Institute.objects.create(
        name="Institute 1",
        description="Will unfortunately get lost",
    )
    institute.users.add(user1)
    institute.users.add(user2)

    new_state = migrator_ext.apply_tested_migration(
        ("accounts", "0007_convert_institutes_to_groups")
    )

    Group = new_state.apps.get_model("auth", "Group")
    group = Group.objects.first()

    assert Group.objects.count() == 1
    assert group.name == institute.name
    assert group.user_set.count() == 2
    assert group.user_set.filter(pk=user1.pk).exists()
    assert group.user_set.filter(pk=user2.pk).exists()
    for user in group.user_set.all():
        assert user.active_group == group


@pytest.mark.django_db
def test_0013_backfill_email_addresses(migrator_ext: Migrator):
    old_state = migrator_ext.apply_initial_migration(
        [("accounts", "0012_invitation"), ("account", "0009_emailaddress_unique_primary_email")]
    )
    User = old_state.apps.get_model("accounts", "User")
    EmailAddress = old_state.apps.get_model("account", "EmailAddress")
    first = User.objects.create(username="first", email="Shared@Example.org")
    second = User.objects.create(username="second", email="shared@example.org")
    alone = User.objects.create(username="alone", email="Alone@Example.org")
    without = User.objects.create(username="without", email="")
    done = User.objects.create(username="done", email="done@example.org")
    EmailAddress.objects.create(user=done, email="done@example.org", verified=False, primary=True)

    new_state = migrator_ext.apply_tested_migration(("accounts", "0013_backfill_email_addresses"))

    EmailAddress = new_state.apps.get_model("account", "EmailAddress")
    assert EmailAddress.objects.count() == 4
    address = EmailAddress.objects.get(user_id=alone.pk)
    assert (address.email, address.verified, address.primary) == ("alone@example.org", True, True)
    # A shared address stays unverified for every user, so that allauth's password
    # reset, which prefers verified rows, still reaches all of them.
    for user in (first, second):
        address = EmailAddress.objects.get(user_id=user.pk)
        assert (address.email, address.verified, address.primary) == (
            "shared@example.org",
            False,
            True,
        )
    assert not EmailAddress.objects.filter(user_id=without.pk).exists()
    # A row that already exists is left alone, whatever it looks like.
    assert EmailAddress.objects.get(user_id=done.pk).verified is False
