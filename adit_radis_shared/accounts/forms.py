from typing import cast

from allauth.account.forms import SignupForm
from allauth.account.models import EmailAddress
from allauth.core import context
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth.models import AbstractBaseUser
from django.http import HttpRequest

from .invitations import forget_invitation, get_invitation, send_new_user_mail_to_admins
from .models import Invitation, User


class InvitationForm(forms.ModelForm):
    class Meta:
        model = Invitation
        fields = ("email",)

    def clean_email(self) -> str:
        email: str = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email address already exists.")
        return email


class InvitationSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    phone_number = forms.CharField(max_length=64)
    department = forms.CharField(max_length=128)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # The signup page is only reachable with an invitation (see AccountAdapter),
        # whose email address the user must keep.
        assert context.request
        invitation = get_invitation(context.request)
        assert invitation
        self.invitation: Invitation = invitation
        email_field = self.fields["email"]
        email_field.disabled = True
        email_field.initial = self.invitation.email
        self.order_fields(
            [
                "email",
                "username",
                "first_name",
                "last_name",
                "phone_number",
                "department",
                "password1",
                "password2",
            ]
        )

    def custom_signup(self, request: HttpRequest, user: AbstractBaseUser) -> None:
        user = cast(User, user)
        user.phone_number = self.cleaned_data["phone_number"]
        user.department = self.cleaned_data["department"]
        user.save()

    def save(self, request: HttpRequest) -> User:
        user = cast(User, super().save(request))
        # Opening the invitation link already proved that the user owns the address.
        EmailAddress.objects.filter(user=user).update(verified=True)
        self.invitation.accept(user)
        forget_invitation(request)
        send_new_user_mail_to_admins(request, user)
        return user


class GroupAdminForm(forms.ModelForm):
    """
    ModelForm that adds an additional multiple select field for managing
    the users in the group.
    """

    users = forms.ModelMultipleChoiceField(
        User.objects.all(),
        widget=FilteredSelectMultiple("Users", False),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            initial_users = self.instance.user_set.values_list("pk", flat=True)
            self.initial["users"] = initial_users

    def save(self, *args, **kwargs):
        kwargs["commit"] = True
        return super().save(*args, **kwargs)

    def save_m2m(self):
        self.instance.user_set.set(self.cleaned_data["users"])
