from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.http import HttpRequest


class AccountAdapter(DefaultAccountAdapter):
    def is_open_for_signup(self, request: HttpRequest) -> bool:
        return False


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    # The identity provider decides who may log in, so every user it sends gets
    # an account. What they may do is still up to the app groups.
    def is_open_for_signup(self, request: HttpRequest, sociallogin) -> bool:
        return True
