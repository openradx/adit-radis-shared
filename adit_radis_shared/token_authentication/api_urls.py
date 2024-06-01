from django.urls import path

from .views import CheckAuthView

urlpatterns = [
    path("check-auth/", CheckAuthView.as_view()),
]
