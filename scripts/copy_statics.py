import argparse
import os
import shutil
import sys

import argcomplete

from adit_radis_shared.commands.helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Copy statics for the project")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    print("Copying statics...")
    target_folder = helper.root_path / "adit_radis_shared" / "common" / "static" / "vendor"

    if not target_folder.exists():
        sys.exit(f"Missing target folder {target_folder}")

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            print(f"Copying {file} to {target_folder}")
            shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
            print(f"Copying {file} to {target_file}")
            shutil.copy(file, target_file)

    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js")
    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js.map")
    copy_file("node_modules/bootstrap/dist/css/bootstrap.css")
    copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
    copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
    copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
    copy_file("node_modules/htmx.org/dist/htmx.js")
    copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
    copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")


if __name__ == "__main__":
    call()
