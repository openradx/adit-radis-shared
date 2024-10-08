from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin, UserAdmin
from django.contrib.auth.forms import UserChangeForm
from django.contrib.auth.models import Group

from .forms import GroupAdminForm
from .models import User


class MyUserChangeForm(UserChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["active_group"].queryset = Group.objects.filter(user__pk=self.instance.pk)  # type: ignore


class MyUserAdmin(UserAdmin):
    form = MyUserChangeForm
    ordering = ("date_joined",)
    list_display = (
        "username",
        "email",
        "date_joined",
        "first_name",
        "last_name",
        "is_staff",
    )
    fieldsets = UserAdmin.fieldsets + (  # type: ignore
        (
            "Additional stuff",
            {"fields": ("phone_number", "department", "active_group")},
        ),
    )
    change_form_template = "loginas/change_form.html"


admin.site.register(User, MyUserAdmin)


class MyGroupAdmin(GroupAdmin):
    form = GroupAdminForm


admin.site.unregister(Group)
admin.site.register(Group, MyGroupAdmin)
