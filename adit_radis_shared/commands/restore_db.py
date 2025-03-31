import argparse
import sys

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(
        description="Restore database in container from the last backup"
    )
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    settings = (
        f"{helper.project_id}.settings.production"
        if helper.is_production()
        else f"{helper.project_id}.settings.development"
    )
    web_container_id = helper.find_running_container_id("web")
    if web_container_id is None:
        sys.exit("Web container is not running. Run 'uv run ./manage.py compose-up' first.")

    helper.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        )
    )
