from django.contrib.sites.models import Site
from django.db import models


class SiteProfile(models.Model):
    uses_https = models.BooleanField(default=False)
    meta_keywords = models.CharField(max_length=120, blank=True)
    meta_description = models.TextField(max_length=200, blank=True)
    project_url = models.URLField(blank=True)
    site = models.OneToOneField(Site, on_delete=models.CASCADE, related_name="profile")

    def __str__(self) -> str:
        return f"{self.__class__.__name__} [{self.pk}]"


class ProjectSettings(models.Model):
    announcement = models.TextField(blank=True)
    maintenance = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Project settings"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} [{self.pk}]"

    @classmethod
    def get(cls) -> "ProjectSettings":
        project_settings = cls.objects.first()
        # We made sure during startup that there is always a ProjectSettings
        # (see common/apps.py)
        assert project_settings
        return project_settings


class AppSettings(models.Model):
    locked = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @classmethod
    def get(cls) -> "AppSettings":
        app_settings = cls.objects.first()
        # We made sure during startup that there is always a AppSettings
        # (see apps.py of the specific app)
        assert app_settings
        return app_settings
