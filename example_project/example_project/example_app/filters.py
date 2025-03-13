import django_filters
from django.http import HttpRequest

from adit_radis_shared.common.forms import SingleFilterFieldFormHelper

from .models import ExampleJob


class ExampleJobFilter(django_filters.FilterSet):
    request: HttpRequest

    class Meta:
        model = ExampleJob
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.form.helper = SingleFilterFieldFormHelper(self.request.GET, "status")
