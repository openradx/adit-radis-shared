"""
URL configuration for example_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("admin-the-great/", admin.site.urls),
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("accounts/", include("adit_radis_shared.accounts.urls")),
    path("token-authentication/", include("adit_radis_shared.token_authentication.urls")),
    path("sandbox/", include("example_project.sandbox.urls")),
]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns = [
        path("__reload__/", include("django_browser_reload.urls")),
        path("__debug__/", include(debug_toolbar.urls)),
    ] + urlpatterns
