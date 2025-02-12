#!/usr/bin/env python3

from _common import PROJECT_NAME, PROJECT_PATH

from adit_radis_shared.default_scripts import DefaultScripts

if __name__ == "__main__":
    DefaultScripts(PROJECT_NAME, PROJECT_PATH).backup_db()
