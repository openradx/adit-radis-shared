from django.apps import AppConfig

from adit_radis_shared.common.site import register_main_menu_item


class ExampleAppConfig(AppConfig):
    name = "example_project.example_app"

    def ready(self):
        register_app()


def register_app():
    register_main_menu_item(
        url_name="example_list",
        label="Examples",
    )
