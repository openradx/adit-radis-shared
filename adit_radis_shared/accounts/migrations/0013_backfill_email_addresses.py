from collections import Counter

from django.db import migrations


def backfill_email_addresses(apps, schema_editor):
    """Give every existing user with an email address the allauth row that a
    sign up through allauth would have created, marked verified: the former
    registration confirmed the address with its activation mail.

    An address that several users share stays unverified for all of them.
    allauth's password reset sends its link only to the users with a verified
    row once one exists, so a single verified row would cut the others off;
    with all rows unverified every one of them still gets the link. Nothing
    else depends on the flag here (ACCOUNT_EMAIL_VERIFICATION is "none" and
    users log in by username).
    """
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    users = list(User.objects.exclude(email="").order_by("pk"))
    users_per_email = Counter(user.email.lower() for user in users)
    verified_emails = {
        email.lower()
        for email in EmailAddress.objects.filter(verified=True).values_list("email", flat=True)
    }
    for user in users:
        if EmailAddress.objects.filter(user=user).exists():
            continue
        email = user.email.lower()
        verified = users_per_email[email] == 1 and email not in verified_emails
        EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_invitation"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]

    operations = [
        migrations.RunPython(backfill_email_addresses, migrations.RunPython.noop),
    ]
