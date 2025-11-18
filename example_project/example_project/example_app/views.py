from typing import cast

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView
from django_filters.views import FilterView
from django_tables2 import SingleTableMixin

from adit_radis_shared.accounts.models import User
from adit_radis_shared.common.mixins import PageSizeSelectMixin
from adit_radis_shared.common.site import THEME_PREFERENCE_KEY
from adit_radis_shared.common.views import BaseHomeView, BaseUpdatePreferencesView

from .filters import ExampleJobFilter
from .forms import DateDemoForm
from .models import ExampleJob
from .tables import ExampleJobTable
from .tasks import example_task


class HomeView(BaseHomeView):
    template_name = "example_app/home.html"


@login_required
def admin_section(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    if not user.is_staff:
        raise PermissionDenied
    return render(request, "example_app/admin_section.html", {})


def example_messages(request: HttpRequest) -> HttpResponse:
    messages.add_message(request, messages.INFO, "This is a info message that is server generated!")
    messages.add_message(request, messages.SUCCESS, "And one when something succeeded!")
    messages.add_message(request, messages.WARNING, "Or how about a warning?")
    messages.add_message(request, messages.ERROR, "And this is another one if something failed!")

    return render(request, "example_app/example_messages.html", {})


@csrf_exempt
def example_date_input(request: HttpRequest) -> HttpResponse:
    parsed_date = None
    parsed_datetime = None
    parsed_freeform_date = None
    formatted_date_examples: list[dict[str, str]] = []
    formatted_datetime_examples: list[dict[str, str]] = []
    formatted_freeform_examples: list[dict[str, str]] = []
    raw_post_value = None
    raw_datetime_value = None
    raw_freeform_value = None
    freeform_attempted = False
    if request.method == "POST":
        raw_post_value = request.POST.get("demo_date") or None
        raw_datetime_value = request.POST.get("demo_datetime") or None
        raw_freeform_value = request.POST.get("freeform_date")
        freeform_attempted = bool(raw_freeform_value)
        form = DateDemoForm(request.POST)
        if form.is_valid():
            parsed_date = form.cleaned_data.get("demo_date")
            if parsed_date:
                formatted_date_examples = [
                    {"label": "Python isoformat()", "value": parsed_date.isoformat()},
                    {"label": "ISO (YYYY-MM-DD)", "value": parsed_date.strftime("%Y-%m-%d")},
                    {"label": "Custom DD/MM/YYYY", "value": parsed_date.strftime("%d/%m/%Y")},
                    {"label": "Django DATE_FORMAT (l10n on)", "value": date_format(parsed_date, format="DATE_FORMAT", use_l10n=True)},
                    {
                        "label": "Django DATE_FORMAT (l10n off)",
                        "value": date_format(parsed_date, format="DATE_FORMAT", use_l10n=False),
                    },
                    {"label": "Django SHORT_DATE_FORMAT", "value": date_format(parsed_date, format="SHORT_DATE_FORMAT", use_l10n=True)},
                ]
            parsed_datetime = form.cleaned_data.get("demo_datetime")
            if parsed_datetime:
                formatted_datetime_examples = [
                    {"label": "Python isoformat()", "value": parsed_datetime.isoformat()},
                    {"label": "ISO (YYYY-MM-DD HH:MM:SS)", "value": parsed_datetime.strftime("%Y-%m-%d %H:%M:%S")},
                    {"label": "Custom DD/MM/YYYY HH:mm", "value": parsed_datetime.strftime("%d/%m/%Y %H:%M")},
                    {
                        "label": "Django DATETIME_FORMAT (l10n on)",
                        "value": date_format(parsed_datetime, format="DATETIME_FORMAT", use_l10n=True),
                    },
                    {
                        "label": "Django DATETIME_FORMAT (l10n off)",
                        "value": date_format(parsed_datetime, format="DATETIME_FORMAT", use_l10n=False),
                    },
                    {
                        "label": "Django SHORT_DATETIME_FORMAT",
                        "value": date_format(parsed_datetime, format="SHORT_DATETIME_FORMAT", use_l10n=True),
                    },
                ]
            parsed_freeform_date = form.cleaned_data.get("freeform_date")
            if parsed_freeform_date:
                formatted_freeform_examples = [
                    {"label": "Python isoformat()", "value": parsed_freeform_date.isoformat()},
                    {"label": "ISO (YYYY-MM-DD)", "value": parsed_freeform_date.strftime("%Y-%m-%d")},
                    {"label": "Custom DD/MM/YYYY", "value": parsed_freeform_date.strftime("%d/%m/%Y")},
                    {
                        "label": "Django DATE_FORMAT (l10n on)",
                        "value": date_format(parsed_freeform_date, format="DATE_FORMAT", use_l10n=True),
                    },
                ]
            if parsed_date:
                messages.success(
                    request,
                    f"Parsed date: {parsed_date.strftime('%A, %d %B %Y')} (ISO: {parsed_date.isoformat()})",
                )
            elif parsed_freeform_date:
                messages.success(
                    request,
                    f"Parsed free-form date: {parsed_freeform_date.strftime('%A, %d %B %Y')} (ISO: {parsed_freeform_date.isoformat()})",
                )
            elif parsed_datetime:
                messages.success(
                    request,
                    f"Parsed datetime: {parsed_datetime.strftime('%A, %d %B %Y %H:%M')} (ISO: {parsed_datetime.isoformat()})",
                )
            form = DateDemoForm()  # Reset so the date picker clears after a successful submit
    else:
        form = DateDemoForm()

    current_time_utc = timezone.now().astimezone(dt_timezone.utc)
    current_time_local = timezone.localtime()  # respects settings.TIME_ZONE

    return render(
        request,
        "example_app/example_date_input.html",
        {
            "form": form,
            "parsed_date": parsed_date,
            "parsed_datetime": parsed_datetime,
            "parsed_freeform_date": parsed_freeform_date,
            "current_time": current_time_local,
            "current_time_utc": current_time_utc,
            "django_time_zone": settings.TIME_ZONE,
            "django_use_tz": settings.USE_TZ,
            "formatted_date_examples": formatted_date_examples,
            "formatted_datetime_examples": formatted_datetime_examples,
            "formatted_freeform_examples": formatted_freeform_examples,
            "raw_post_value": raw_post_value,
            "raw_datetime_value": raw_datetime_value,
            "raw_freeform_value": raw_freeform_value,
            "freeform_attempted": freeform_attempted,
        },
    )


def example_background_task_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        job_id = example_task.defer()
        messages.info(request, f"Job started with ID {job_id}!")
        return redirect("example_background_task")

    return render(request, "example_app/example_background_task.html", {})


class AsyncExampleClassView(View):
    async def get(self, request: HttpRequest) -> HttpResponse:
        return await sync_to_async(render)(request, "example_app/example_async_view.html")


class ExampleTableHeadingView(PageSizeSelectMixin, SingleTableMixin, FilterView):
    model = ExampleJob
    table_class = ExampleJobTable
    filterset_class = ExampleJobFilter
    template_name = "example_app/example_table_heading.html"


class ExampleCustomPaginationView(PageSizeSelectMixin, ListView):
    model = ExampleJob
    template_name = "example_app/example_custom_pagination.html"
    context_object_name = "jobs"

    def get_paginate_by(self, queryset: QuerySet) -> int | None:
        per_page = 25
        if self.request.GET.get("per_page"):
            return int(self.request.GET.get("per_page", per_page))
        return per_page


class UpdatePreferencesView(BaseUpdatePreferencesView):
    allowed_keys = [THEME_PREFERENCE_KEY]
