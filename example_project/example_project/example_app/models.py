from django.db import models


class ExampleJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "PE", "Pending"
        IN_PROGRESS = "IP", "In progress"
        DONE = "DO", "Done"

    name = models.CharField(max_length=100)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.PENDING)

    def __str__(self):
        return f"{self.__class__.__name__} {self.name} [{self.pk}]"
