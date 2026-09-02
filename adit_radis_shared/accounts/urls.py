from django.urls import include, path

from . import views

urlpatterns = [
    path("", include("allauth.urls")),
    path("profile/", views.UserProfileView.as_view(), name="profile"),
    path(
        "active-group/",
        views.ActiveGroupView.as_view(),
        name="active_group",
    ),
    path("invitations/", views.InvitationsView.as_view(), name="invitations"),
    path(
        "invitations/accept/<str:token>/",
        views.InvitationAcceptView.as_view(),
        name="invitation_accept",
    ),
]
