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
    def get(cls):
        return cls.objects.first()


class AppSettings(models.Model):
    id: int
    locked = models.BooleanField(default=False)

    class Meta:
        abstract = True

    @classmethod
    def get(cls):
        return cls.objects.first()
