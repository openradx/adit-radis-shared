from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse

from adit_radis_shared.common.utils.mail import send_mail_to_admins

from .models import Invitation, User

SESSION_KEY = "invitation_id"


def remember_invitation(request: HttpRequest, invitation: Invitation) -> None:
    request.session[SESSION_KEY] = invitation.pk


def forget_invitation(request: HttpRequest) -> None:
    request.session.pop(SESSION_KEY, None)


def get_invitation(request: HttpRequest) -> Invitation | None:
    """The valid invitation the visitor opened, if any."""
    invitation_id = request.session.get(SESSION_KEY)
    if not invitation_id:
        return None
    invitation = Invitation.objects.filter(pk=invitation_id).first()
    if invitation is None or not invitation.is_valid:
        return None
    return invitation


def send_invitation_mail(request: HttpRequest, invitation: Invitation) -> None:
    site_name = get_current_site(request).name
    url = request.build_absolute_uri(
        reverse("invitation_accept", kwargs={"token": invitation.token})
    )
    text = render_to_string(
        "accounts/mail/invitation.txt",
        {"invitation": invitation, "site_name": site_name, "url": url},
    )
    send_mail(
        settings.EMAIL_SUBJECT_PREFIX + f"Invitation to {site_name}",
        text,
        None,
        recipient_list=[invitation.email],
    )


def send_new_user_mail_to_admins(request: HttpRequest, user: User) -> None:
    """Tell the admins that a user was created, as only they can put them in a group."""
    text = render_to_string(
        "accounts/mail/new_user.txt",
        {
            "user": user,
            "site_name": get_current_site(request).name,
            "url": request.build_absolute_uri(
                reverse("admin:accounts_user_change", args=[user.pk])
            ),
        },
    )
    send_mail_to_admins("New user registered", text_content=text)
