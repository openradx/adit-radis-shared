from typing import cast

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpRequest

from .invitations import get_invitation, send_new_user_mail_to_admins
from .models import User


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return get_invitation(request) is not None


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    # The identity provider decides who may log in, so every user it sends gets
    # an account. What they may do is still up to the app groups.
    def is_open_for_signup(self, request: HttpRequest, sociallogin) -> bool:
        return True

    def save_user(self, request: HttpRequest, sociallogin, form=None):
        # The user only exists in the app from the first login on, so this is the
        # earliest moment an admin can put them into a group.
        user = super().save_user(request, sociallogin, form)
        send_new_user_mail_to_admins(request, cast(User, user))
        return user
