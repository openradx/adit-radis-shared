from django_tables2 import tables

from .models import ExampleJob


class ExampleJobTable(tables.Table):
    class Meta:
        model = ExampleJob
        fields = ("id", "name", "status")
        empty_text = "No jobs to show"
        attrs = {"class": "table table-bordered table-hover"}
