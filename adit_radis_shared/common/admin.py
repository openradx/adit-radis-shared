from django.contrib import admin
from django.contrib.sites.admin import SiteAdmin
from django.contrib.sites.models import Site

from .models import ProjectSettings, SiteProfile

admin.site.register(ProjectSettings, admin.ModelAdmin)


class SiteProfileInline(admin.StackedInline):
    model = SiteProfile
    can_delete = False
    verbose_name_plural = "Site Profile"
    fk_name = "site"


class CustomSiteAdmin(SiteAdmin):
    inlines = (SiteProfileInline,)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomSiteAdmin, self).get_inline_instances(request, obj)


admin.site.unregister(Site)
admin.site.register(Site, CustomSiteAdmin)
