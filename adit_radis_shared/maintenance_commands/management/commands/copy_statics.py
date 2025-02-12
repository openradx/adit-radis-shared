import os
import shutil
from typing import Annotated

from typer import Exit, Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Start stack with docker compose"""

    def handle(
        self,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        print("Copying statics...")
        target_folder = self.project_path / "adit_radis_shared" / "common" / "static" / "vendor"

        if not target_folder.exists():
            print(f"Missing target folder {target_folder}")
            raise Exit(1)

        def copy_file(file: str, filename: str | None = None):
            if not filename:
                print(f"Copying {file} to {target_folder}")
                if not simulate:
                    shutil.copy(file, target_folder)
            else:
                target_file = os.path.join(target_folder, filename)
                print(f"Copying {file} to {target_file}")
                if not simulate:
                    shutil.copy(file, target_file)

        copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js")
        copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js.map")
        copy_file("node_modules/bootswatch/dist/flatly/bootstrap.css")
        copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
        copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
        copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
        copy_file("node_modules/htmx.org/dist/htmx.js")
        copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
        copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")
