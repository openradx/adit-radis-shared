from asgiref.sync import sync_to_async
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.generic import TemplateView


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "example_app/home.html", {})


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


# Cave, LoginRequiredMixin won't work with async views! One has to implement it himself.
class AsyncExampleClassView(View):
    async def get(self, request: HttpRequest) -> HttpResponse:
        return await sync_to_async(render)(request, "example_app/example_async_view.html")
