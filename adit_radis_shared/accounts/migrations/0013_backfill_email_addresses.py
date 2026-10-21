from django.db import migrations


def backfill_email_addresses(apps, schema_editor):
    """Give every existing user with an email address the allauth row that a
    sign up through allauth would have created, marked verified: the former
    registration confirmed the address with its activation mail. allauth lets
    a verified address exist only once, so when several users share one, the
    oldest keeps it verified and the others get an unverified row.
    """
    User = apps.get_model("accounts", "User")
    EmailAddress = apps.get_model("account", "EmailAddress")

    verified_emails = set(
        EmailAddress.objects.filter(verified=True).values_list("email", flat=True)
    )
    for user in User.objects.exclude(email="").order_by("pk"):
        if EmailAddress.objects.filter(user=user).exists():
            continue
        email = user.email.lower()
        verified = email not in verified_emails
        EmailAddress.objects.create(user=user, email=email, verified=verified, primary=True)
        if verified:
            verified_emails.add(email)


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0012_invitation"),
        ("account", "0009_emailaddress_unique_primary_email"),
    ]

    operations = [
        migrations.RunPython(backfill_email_addresses, migrations.RunPython.noop),
    ]
