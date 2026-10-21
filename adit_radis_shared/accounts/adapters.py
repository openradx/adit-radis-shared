from allauth.account.adapter import DefaultAccountAdapter
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    # Accounts are created by an administrator, there is no self-service sign up.
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return False
