import argparse
import sys

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(
        description="Backup database in running container stack",
        epilog="For backup location see DBBACKUP_STORAGE_OPTIONS setting",
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
        sys.exit("Web container is not running.")

    helper.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        )
    )
