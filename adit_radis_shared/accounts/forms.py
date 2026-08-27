from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple

from .models import User


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
