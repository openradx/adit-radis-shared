from pathlib import Path

from typer import Exit

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Start stack with docker compose"""

    def handle(self):
        """Generate self-signed certificate files"""

        config = self.load_config_from_env_file()

        if "SSL_HOSTNAME" not in config:
            print("Missing SSL_HOSTNAME setting in .env file")
            raise Exit(1)
        if "SSL_SERVER_CERT_FILE" not in config:
            print("Missing SSL_SERVER_CERT_FILE setting in .env file")
            raise Exit(1)
        if "SSL_SERVER_KEY_FILE" not in config:
            print("Missing SSL_SERVER_KEY_FILE setting in .env file")
            raise Exit(1)

        hostname = config["SSL_HOSTNAME"]
        assert hostname

        ip_addresses = config.get("SSL_IP_ADDRESSES", "")
        assert isinstance(ip_addresses, str)
        ip_addresses = [item.strip() for item in ip_addresses.split(",") if item.strip()]

        (cert_pem, key_pem) = self.generate_self_signed_certificates(hostname, ip_addresses)

        cert_file = config["SSL_SERVER_CERT_FILE"]
        assert cert_file
        cert_path = Path(cert_file)
        if cert_path.is_file():
            print(f"A SSL certificate file {cert_path.absolute()} already exists. Skipping.")
            raise Exit()

        key_file = config["SSL_SERVER_KEY_FILE"]
        assert key_file
        key_path = Path(key_file)
        if key_path.is_file():
            print(f"Key file {key_path.absolute()} already exists. Skipping.")
            raise Exit()

        chain_file = config["SSL_SERVER_CHAIN_FILE"]
        assert chain_file
        chain_path = Path(chain_file)
        if chain_path.is_file():
            print(f"Chain file {chain_path.absolute()} already exists. Skipping.")
            raise Exit()

        cert_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cert_path, "wb") as cert_file:
            cert_file.write(cert_pem)
            print(f"Generated cert file at {cert_path.absolute()}")

        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, "wb") as key_file:
            key_file.write(key_pem)
            print(f"Generated key file at {key_path.absolute()}")

        # Necessary copy of cert file to chain file since chain file must not be empty and at
        #  least the leaf certificate must be present
        chain_path.parent.mkdir(parents=True, exist_ok=True)
        with open(chain_path, "wb") as chain_file:
            chain_file.write(cert_pem)
            print(f"Generated chain file at {chain_path.absolute()}")
