#!/usr/bin/env python3

import argparse
import os
import shutil

from _common import PROJECT_NAME, PROJECT_PATH

from adit_radis_shared.script_helper import ScriptHelper


def main():
    """Copy JS and CSS dependencies from node_modules to static vendor folder"""

    class CopyStaticsArgs(argparse.Namespace):
        simulate: bool = False

    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--simulate", action="store_true", help="Simulate the copy operation")
    args = parser.parse_args(namespace=CopyStaticsArgs)

    helper = ScriptHelper(PROJECT_NAME, PROJECT_PATH, simulate_execution=args.simulate)

    print("Copying statics...")
    target_folder = helper.project_path / "adit_radis_shared" / "common" / "static" / "vendor"

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
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


if __name__ == "__main__":
    main()
