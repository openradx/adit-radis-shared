from django.contrib import admin

from .models import ProjectSettings

admin.site.register(ProjectSettings, admin.ModelAdmin)
