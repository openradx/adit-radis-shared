import argparse
import sys
from pathlib import Path

import argcomplete

from .helper import CommandHelper


def call():
    parser = argparse.ArgumentParser(
        description="Generate certificate chain file for a signed certificate"
    )
    argcomplete.autocomplete(parser)
    parser.parse_args()

    helper = CommandHelper()

    config = helper.load_config_from_env_file()

    if "SSL_HOSTNAME" not in config:
        sys.exit("Missing SSL_HOSTNAME setting in .env file")
    if "SSL_SERVER_CERT_FILE" not in config:
        sys.exit("Missing SSL_SERVER_CERT_FILE setting in .env file")
    if "SSL_SERVER_CHAIN_FILE" not in config:
        sys.exit("Missing SSL_SERVER_CHAIN_FILE setting in .env file")

    hostname = config["SSL_HOSTNAME"]
    assert hostname

    cert_file = config["SSL_SERVER_CERT_FILE"]
    assert cert_file

    chain_file = config["SSL_SERVER_CHAIN_FILE"]
    assert chain_file

    cert_path = Path(cert_file)
    if not cert_path.is_file():
        sys.exit(
            f"SSL certificate file {cert_path.absolute()} does not exist. You can generate an"
            " unsigned certificate with 'uv run ./manage.py generate-certificate_files'"
            " with included chain file. If you have a signed certificate from a CA, be sure to"
            " provide the correct SSL_SERVER_CERT_FILE setting in '.env'."
        )

    chain_path = Path(chain_file)
    if chain_path.is_file():
        sys.exit(
            f"Chain file {chain_path.absolute()} already exist."
            " Delete this file to generate a new one. Skipping."
        )

    try:
        chain_pem = helper.generate_chain_file_for_host(hostname)
    except Exception:
        print(
            "Generating chain file failed. "
            "You are probably running within a intranet with no public DNS and an internal CA. "
            "Your signing CA is Root CA of your domain, no intermediate certificates needed. "
            "Therefore chain is generated based on the provided leaf certificate."
        )
        with open(cert_path, "rb") as file:
            chain_pem = file.read()

    chain_path.parent.mkdir(parents=True, exist_ok=True)
    with open(chain_path, "wb") as chain_file:
        chain_file.write(chain_pem)
        print(f"Generated chain file at {chain_path.absolute()}")
