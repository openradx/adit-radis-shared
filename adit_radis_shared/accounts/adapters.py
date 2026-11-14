from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest

from .invitations import get_invitation


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return get_invitation(request) is not None
