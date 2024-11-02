import re
import zoneinfo

from django.conf import settings
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone

from adit_radis_shared.common.models import ProjectSettings
from adit_radis_shared.common.types import HtmxHttpRequest


def is_html_response(response):
    return response.has_header("Content-Type") and response["Content-Type"].startswith("text/html")


class MaintenanceMiddleware:
    """Render a maintenance template if in maintenance mode.

    Adapted from http://blog.ankitjaiswal.tech/put-your-django-site-on-maintenanceoffline-mode/
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HtmxHttpRequest):
        login_request = request.path == reverse("auth_login")
        logout_request = request.path == reverse("auth_logout")
        if login_request or logout_request:
            return self.get_response(request)

        project_settings = ProjectSettings.get()
        if project_settings.maintenance:
            # Unfortunately, DRF does authenticate the user at a later stage and API requests
            # are always anonymous inside the middleware. But this is ok, as we never want
            # to allow API requests in maintenance mode (admin users may never know about
            # that the site is in maintenance when using an API client).
            if request.path.startswith("/api/"):
                return HttpResponse(status=503)

            if not request.user.is_staff:
                response = TemplateResponse(request, "common/maintenance.html", status=503)
                return response.render()

        response = self.get_response(request)
        if (
            is_html_response(response)
            and project_settings
            and project_settings.maintenance
            and request.user.is_staff
        ):
            response.content = re.sub(
                r"<body.*>",
                r"\g<0><div class='maintenance-hint'>Site is in maintenance mode!</div>",
                response.content.decode("utf-8"),
            )
        return response


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = settings.USER_TIME_ZONE
        if tzname:
            timezone.activate(zoneinfo.ZoneInfo(tzname))
        else:
            timezone.deactivate()
        return self.get_response(request)
