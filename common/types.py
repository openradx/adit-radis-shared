from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest
from django_htmx.middleware import HtmxDetails
from rest_framework.request import Request

from adit_radis_shared.accounts.models import User


class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails
    user: AnonymousUser | User


class AuthenticatedHttpRequest(HtmxHttpRequest):
    user: User


class AuthenticatedApiRequest(Request):
    user: User
