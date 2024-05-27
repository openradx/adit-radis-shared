from django.db import models


class ProjectSettings(models.Model):
    id: int
    announcement = models.TextField(blank=True)
    maintenance = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Project settings"

    def __str__(self) -> str:
        return f"{self.__class__.__name__} [ID {self.id}]"

    @classmethod
    def get(cls) -> "ProjectSettings":
        project_settings = cls.objects.first()
        # We made sure during startup that there is always a ProjectSettings
        # (see common/apps.py)
        assert project_settings
        return project_settings


class AppSettings(models.Model):
    id: int
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
