from django.urls import path
from django.views.generic import TemplateView

from .views import (
    AsyncExampleClassView,
    HomeView,
    UpdatePreferencesView,
    admin_section,
    example_messages,
    example_task_view,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("update-preferences/", UpdatePreferencesView.as_view()),
    path("admin-section/", admin_section, name="admin_section"),
    path(
        "examples/",
        TemplateView.as_view(template_name="example_app/example_list.html"),
        name="example_list",
    ),
    path(
        "examples/messages/",
        example_messages,
        name="example_messages",
    ),
    path(
        "examples/toasts/",
        TemplateView.as_view(template_name="example_app/example_toasts.html"),
        name="example_toasts",
    ),
    path(
        "examples/async-class-view/",
        AsyncExampleClassView.as_view(),
        name="example_async_class_view",
    ),
    path(
        "examples/example-task/",
        example_task_view,
        name="example_task",
    ),
    path(
        "examples/heading/",
        TemplateView.as_view(template_name="example_app/example_heading.html"),
        name="example_heading",
    ),
]
