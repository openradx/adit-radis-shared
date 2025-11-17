from typing import cast

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
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


def example_date_input(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = DateDemoForm(request.POST)
        if form.is_valid():
            picked_date = form.cleaned_data["demo_date"]
            messages.success(
                request,
                f"Parsed date: {picked_date.strftime('%A, %d %B %Y')} (ISO: {picked_date.isoformat()})",
            )
            return redirect("example_date_input")
    else:
        form = DateDemoForm()

    return render(request, "example_app/example_date_input.html", {"form": form})


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
