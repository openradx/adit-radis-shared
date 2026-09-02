import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    phone_number = models.CharField(max_length=64, blank=True)
    department = models.CharField(max_length=128, blank=True)
    preferences = models.JSONField(default=dict)
    active_group = models.ForeignKey(
        Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="active_users",
    )

    def save(self, *args, **kwargs):
        if self.active_group and self.active_group not in self.groups.all():
            raise ValueError("Active group must be one of the user's groups")
        super().save(*args, **kwargs)

    def change_active_group(self, new_group: Group):
        if new_group in self.groups.all():
            self.active_group = new_group
            self.save()
        else:
            raise ValueError("New group must be one of the user's groups")


def generate_invitation_token() -> str:
    return secrets.token_urlsafe(32)


class Invitation(models.Model):
    email = models.EmailField()
    token = models.CharField(
        max_length=64, unique=True, editable=False, default=generate_invitation_token
    )
    invited_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="sent_invitations"
    )
    created = models.DateTimeField(auto_now_add=True)
    expires = models.DateTimeField(blank=True)
    accepted = models.DateTimeField(null=True, blank=True)
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="invitation"
    )

    def __str__(self) -> str:
        return self.email

    def save(self, *args, **kwargs):
        if not self.expires:
            valid_days = getattr(settings, "INVITATION_VALID_DAYS", 14)
            self.expires = timezone.now() + timedelta(days=valid_days)
        super().save(*args, **kwargs)

    @property
    def is_valid(self) -> bool:
        return self.accepted is None and self.expires > timezone.now()

    @property
    def status(self) -> str:
        if self.accepted:
            return "Accepted"
        if self.expires <= timezone.now():
            return "Expired"
        return "Pending"

    def accept(self, user: User) -> None:
        self.accepted = timezone.now()
        self.user = user
        self.save()
