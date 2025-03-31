#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
from adit_radis_shared.commands import generate_django_secret_key

if __name__ == "__main__":
    generate_django_secret_key.call()
