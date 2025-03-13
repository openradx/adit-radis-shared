import factory

from adit_radis_shared.common.factories import BaseDjangoModelFactory

from .models import ExampleJob

job_status_keys = [key for key, _ in ExampleJob.Status.choices]


class ExampleJobFactory(BaseDjangoModelFactory[ExampleJob]):
    name = factory.Faker("word")
    status = factory.Faker("random_element", elements=job_status_keys)

    class Meta:
        model = ExampleJob
