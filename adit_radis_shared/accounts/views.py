from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import AccessMixin, LoginRequiredMixin, PermissionRequiredMixin
from django.core.exceptions import SuspiciousOperation, ValidationError
from django.http import HttpRequest
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import FormView, TemplateView

from adit_radis_shared.common.types import AuthenticatedHttpRequest
from adit_radis_shared.common.utils.htmx_triggers import trigger_toast

from .forms import InvitationForm
from .invitations import remember_invitation, send_invitation_mail
from .models import Invitation


class UserProfileView(LoginRequiredMixin, AccessMixin, TemplateView):
    template_name = "accounts/profile.html"
    request: AuthenticatedHttpRequest


class ActiveGroupView(LoginRequiredMixin, View):
    def post(self, request: AuthenticatedHttpRequest):
        if not request.htmx:
            raise SuspiciousOperation

        try:
            group_id = request.POST.get("group") or ""
            group_id = int(group_id)
        except ValueError:
            raise ValidationError("Invalid group ID")

        request.user.active_group = request.user.groups.get(id=group_id)
        request.user.save()

        return trigger_toast(
            title="Active group changed",
            text=f"Active group changed to {request.user.active_group.name}",
        )


class InvitationsView(PermissionRequiredMixin, FormView):
    permission_required = "accounts.add_invitation"
    template_name = "accounts/invitations.html"
    form_class = InvitationForm
    success_url = reverse_lazy("invitations")
    request: AuthenticatedHttpRequest

    def form_valid(self, form: InvitationForm):
        invitation: Invitation = form.save(commit=False)
        invitation.invited_by = self.request.user
        invitation.save()
        send_invitation_mail(self.request, invitation)
        messages.success(self.request, f"Invitation sent to {invitation.email}.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["invitations"] = Invitation.objects.select_related("invited_by").order_by(
            "-created"
        )
        return context


class InvitationAcceptView(View):
    def get(self, request: HttpRequest, token: str):
        invitation = Invitation.objects.filter(token=token).first()
        if invitation is None or not invitation.is_valid:
            return render(request, "accounts/invitation_invalid.html", status=410)

        # The sign up page redirects logged in users away, and the invitee wants
        # a new account anyway, e.g. when opening the link on a shared computer.
        if request.user.is_authenticated:
            logout(request)
        remember_invitation(request, invitation)
        return redirect("account_signup")
