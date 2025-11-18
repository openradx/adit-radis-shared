from typing import cast

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
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
    formatted_date_examples: list[dict[str, str]] = []
    raw_post_value = None
    if request.method == "POST":
        raw_post_value = request.POST.get("demo_date") or None
        form = DateDemoForm(request.POST)
        if form.is_valid():
            parsed_date = form.cleaned_data["demo_date"]
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
            messages.success(
                request,
                f"Parsed date: {parsed_date.strftime('%A, %d %B %Y')} (ISO: {parsed_date.isoformat()})",
            )
            form = DateDemoForm()  # Reset so the date picker clears after a successful submit
    else:
        form = DateDemoForm()

    current_time2 = timezone.now()

    return render(
        request,
        "example_app/example_date_input.html",
        {
            "form": form,
            "parsed_date": parsed_date,
            "current_time": current_time2,
            "formatted_date_examples": formatted_date_examples,
            "raw_post_value": raw_post_value,
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
