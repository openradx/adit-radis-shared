from typing import Any

from django.contrib import messages
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    UserPassesTestMixin,
)
from django.core.exceptions import SuspiciousOperation
from django.forms import Form
from django.http import HttpResponse
from django.urls import re_path
from django.views.generic import FormView, View
from django.views.generic.base import TemplateView
from revproxy.views import ProxyView

from adit_radis_shared.accounts.models import User
from adit_radis_shared.common.forms import BroadcastForm
from adit_radis_shared.common.models import ProjectSettings
from adit_radis_shared.common.tasks import broadcast_mail

from .types import AuthenticatedHttpRequest, HtmxHttpRequest


class HtmxTemplateView(TemplateView):
    def get(self, request: HtmxHttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not request.htmx:
            raise SuspiciousOperation
        return super().get(request, *args, **kwargs)


class BaseHomeView(TemplateView):
    template_name: str

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        project_settings = ProjectSettings.get()
        context["announcement"] = project_settings.announcement
        return context


class BaseUpdatePreferencesView(LoginRequiredMixin, View):
    """Allows the client to update the user preferences.

    We use this to retain some form state between browser refreshes.
    The implementations of this view is called by some AJAX requests when specific
    form fields are changed.
    """

    allowed_keys: list[str]

    def post(self, request: AuthenticatedHttpRequest) -> HttpResponse:
        for key in request.POST.keys():
            if key not in self.allowed_keys:
                raise SuspiciousOperation(f'Invalid preference "{key}" to update.')

        preferences = request.user.preferences

        for key, value in request.POST.items():
            if value == "true":
                value = True
            elif value == "false":
                value = False

            preferences[key] = value

        request.user.save()

        return HttpResponse()


class BroadcastView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = "common/broadcast.html"
    form_class = BroadcastForm
    request: AuthenticatedHttpRequest

    def test_func(self) -> bool:
        return self.request.user.is_staff

    def get_success_url(self) -> str:
        return self.request.path

    def form_valid(self, form: Form) -> HttpResponse:
        recipients: list[User] = form.cleaned_data["recipients"]
        subject: str = form.cleaned_data["subject"]
        message: str = form.cleaned_data["message"]

        emails: list[str] = [recipient.email for recipient in recipients]
        broadcast_mail.defer(recipients=emails, subject=subject, message=message)

        messages.add_message(
            self.request,
            messages.SUCCESS,
            "Email will be sent to selected users.",
        )

        return super().form_valid(form)


class AdminProxyView(LoginRequiredMixin, UserPassesTestMixin, ProxyView):
    """A reverse proxy view to hide other services behind that only an admin can access.

    By using a reverse proxy we can use the Django authentication
    to check for an logged in admin user.
    Code from https://stackoverflow.com/a/61997024/166229
    """

    request: AuthenticatedHttpRequest

    def test_func(self):
        return self.request.user.is_staff

    @classmethod
    def as_url(cls):
        return re_path(rf"^{cls.url_prefix}/(?P<path>.*)$", cls.as_view())  # type: ignore
