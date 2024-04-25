from django.apps import AppConfig

from adit_radis_shared.common.site import MainMenuItem, register_main_menu_item


class ExampleAppConfig(AppConfig):
    name = "example_project.example_app"

    def ready(self):
        register_app()


def register_app():
    register_main_menu_item(
        MainMenuItem(
            url_name="admin_section",
            label="Admin Section",
            staff_only=True,
            order=99,
        )
    )

    register_main_menu_item(
        MainMenuItem(
            url_name="example_list",
            label="Examples",
        )
    )
