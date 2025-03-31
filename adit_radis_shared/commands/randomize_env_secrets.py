import argparse
import sys

import argcomplete
from dotenv import set_key

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(description="Randomize secrets in the .env file")
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    env_file = helper.root_path / ".env"
    if not env_file.is_file():
        sys.exit("Workspace not initialized (.env file does not exist).")

    set_key(env_file, "DJANGO_SECRET_KEY", helper.generate_django_secret_key())
    set_key(env_file, "POSTGRES_PASSWORD", helper.generate_secure_password())
    set_key(env_file, "ADMIN_USER_PASSWORD", helper.generate_secure_password())
    set_key(env_file, "ADMIN_AUTH_TOKEN", helper.generate_auth_token())
