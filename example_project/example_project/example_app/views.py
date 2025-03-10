from typing import cast

from asgiref.sync import sync_to_async
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import TemplateView

from adit_radis_shared.accounts.models import User
from adit_radis_shared.common.site import THEME_PREFERENCE_KEY
from adit_radis_shared.common.views import BaseHomeView, BaseUpdatePreferencesView

from .tasks import example_task


class HomeView(BaseHomeView):
    template_name = "example_app/home.html"


@login_required
def admin_section(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    if not user.is_staff:
        raise PermissionDenied
    return render(request, "example_app/admin_section.html", {})


class ExampleListView(TemplateView):
    template_name = "example_app/example_list.html"


def example_toasts(request: HttpRequest) -> HttpResponse:
    return render(request, "example_app/example_toasts.html", {})


def example_messages(request: HttpRequest) -> HttpResponse:
    messages.add_message(request, messages.INFO, "This is a info message that is server generated!")
    messages.add_message(request, messages.SUCCESS, "And one when something succeeded!")
    messages.add_message(request, messages.WARNING, "Or how about a warning?")
    messages.add_message(request, messages.ERROR, "And this is another one if something failed!")

    return render(request, "example_app/example_messages.html", {})


def example_task_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        job_id = example_task.defer()
        messages.info(request, f"Job started with ID {job_id}!")
        return redirect("example_task")

    return render(request, "example_app/example_task.html", {})


# Cave, LoginRequiredMixin won't work with async views! One has to implement it himself.
class AsyncExampleClassView(View):
    async def get(self, request: HttpRequest) -> HttpResponse:
        return await sync_to_async(render)(request, "example_app/example_async_view.html")


class UpdatePreferencesView(BaseUpdatePreferencesView):
    allowed_keys = [THEME_PREFERENCE_KEY]
