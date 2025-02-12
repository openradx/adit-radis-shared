import binascii
import ipaddress
import os
import re
import secrets
import string
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from os import urandom
from pathlib import Path
from typing import Any

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.conf import settings
from django.core.management.utils import get_random_secret_key
from django_typer.management import TyperCommand
from dotenv import dotenv_values
from typer import Exit


class MaintenanceCommand(TyperCommand):
    root_path: Path = settings.ROOT_PATH
    project_id: str = settings.PROJECT_ID
    _is_production_cached = None

    ###
    # Helper methods
    ###

    def is_production(self) -> bool:
        if self._is_production_cached is None:
            config = self.load_config_from_env_file()

            if "ENVIRONMENT" not in config:
                print("Missing ENVIRONMENT setting in .env file.")
                raise Exit(1)

            environment = config["ENVIRONMENT"]
            if environment not in ["development", "production"]:
                print(f"Invalid ENVIRONMENT setting {environment} in .env file.")
                raise Exit(1)

            self._is_production_cached = environment == "production"

        return self._is_production_cached

    def get_compose_base_file(self):
        return self.root_path / "docker-compose.base.yml"

    def get_compose_env_file(self):
        if self.is_production():
            return self.root_path / "docker-compose.prod.yml"
        return self.root_path / "docker-compose.dev.yml"

    def get_stack_name(self) -> str:
        config = self.load_config_from_env_file()
        if stack_name := config.get("STACK_NAME", ""):
            return stack_name

        if self.is_production():
            return f"{self.project_id}_prod"
        return f"{self.project_id}_dev"

    def load_config_from_env_file(self) -> dict[str, str | None]:
        env_file = self.root_path / ".env"
        if not env_file.exists():
            print("Missing .env file!")
            raise Exit(1)

        return dotenv_values(env_file)

    def build_compose_cmd(self, profiles: list[str] | None = None):
        cmd = "docker compose"
        cmd += f" -f {self.get_compose_base_file()}"
        cmd += f" -f {self.get_compose_env_file()}"
        cmd += f" -p {self.get_stack_name()}"

        if profiles:
            for profile in profiles:
                cmd += f" --profile {profile}"

        return cmd

    def check_compose_up(self):
        result = self.capture_cmd("docker compose ls")
        for line in result.splitlines():
            if line.startswith(self.get_stack_name()) and line.find("running") != -1:
                return True
        return False

    def prepare_environment(self):
        config = self.load_config_from_env_file()

        backup_dir = config.get("BACKUP_DIR")
        if not backup_dir:
            return

        backup_path = Path(backup_dir)
        if not backup_path.exists():
            print(f"Creating non-existent BACKUP_DIR {backup_path.absolute()}")
            backup_path.mkdir(parents=True, exist_ok=True)
        if not backup_path.is_dir():
            print(f"Invalid BACKUP_DIR {backup_path.absolute()}.")
            raise Exit(1)

    def find_running_container_id(self, name: str):
        sep = "_" if self.is_production() else "-"
        cmd = f"docker ps -q -f name={self.get_stack_name()}{sep}{name} -f status=running"
        cmd += " | head -n1"
        result = self.capture_cmd(cmd)
        if result:
            container_id = result.strip()
            if container_id:
                return container_id
        return None

    def confirm(self, question: str) -> bool:
        valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
        while True:
            sys.stdout.write(f"{question} [y/N] ")
            choice = input().lower()
            if choice == "":
                return False
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' (or 'y' or 'n').\n")

    def get_latest_remote_version_tag(self, owner, repo) -> str | None:
        url = f"https://api.github.com/repos/{owner}/{repo}/tags"
        response = requests.get(url)
        response.raise_for_status()
        tags = response.json()

        semantic_version_pattern = re.compile(r"^(\d+\.\d+\.\d+)$")
        semantic_tags = [tag["name"] for tag in tags if semantic_version_pattern.match(tag["name"])]

        if semantic_tags:
            latest_tag = semantic_tags[0]
            return latest_tag

        return None

    def get_latest_local_version_tag(self) -> str:
        # Get all tags sorted by creation date (newest first)
        result = self.capture_cmd("git tag -l --sort=-creatordate")
        all_tags = result.splitlines()

        version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        for tag in all_tags:
            if version_pattern.match(tag):
                return tag

        return "0.0.0"

    def generate_django_secret_key(self):
        return get_random_secret_key()

    def generate_secure_password(self, length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(characters) for _ in range(length))

    def generate_auth_token(self, length=20):
        return binascii.hexlify(urandom(length)).decode()

    def generate_self_signed_certificates(
        self,
        hostname: str,
        ip_addresses: list[str] | None = None,
        private_key: rsa.RSAPrivateKey | None = None,
    ):
        """Generates self signed certificates for a hostname, and optional IP addresses."""

        # Generate our key
        if private_key is None:
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend(),
            )

        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])

        # best practice seem to be to include the hostname in the SAN,
        # which *SHOULD* mean COMMON_NAME is ignored.
        alt_names: list[x509.GeneralName] = [x509.DNSName(hostname)]

        # allow addressing by IP, for when you don't have real DNS (common in testing scenarios)
        if ip_addresses:
            for addr in ip_addresses:
                # openssl wants DNSnames for ips...
                alt_names.append(x509.DNSName(addr))
                # ... whereas golang's crypto/tls is stricter, and needs IPAddresses
                # note: older versions of cryptography do not understand ip_address objects
                alt_names.append(x509.IPAddress(ipaddress.ip_address(addr)))

        san = x509.SubjectAlternativeName(alt_names)

        # path_len=0 means this cert can only sign itself, not other certs.
        now = datetime.now(timezone.utc)
        basic_constraints = x509.BasicConstraints(ca=True, path_length=0)
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now)
            .not_valid_after(now + timedelta(days=10 * 365))
            .add_extension(basic_constraints, False)
            .add_extension(san, False)
            .sign(private_key, hashes.SHA256(), default_backend())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        return cert_pem, key_pem

    def generate_chain_file_for_host(self, hostname: str):
        """Generates the chain file for a signed certificate"""
        url = (
            f"https://whatsmychaincert.com/generate?include_leaf=1&host={hostname}"
            "&submit_btn=Generate+Chain&include_root=1"
        )
        response = requests.get(url)
        response.raise_for_status()
        chain_pem = response.content
        return chain_pem

    def capture_cmd(self, cmd: str) -> str:
        """Capture the output of a shell command.

        Args:
            cmd: The command to execute
        Returns:
            The output of the command.
        """
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout

    def execute_cmd(
        self,
        cmd: str,
        env: dict[str, Any] | None = None,
        hidden: bool = False,
        simulate: bool = False,
    ):
        """Execute a shell command.

        Args:
            cmd: The command to execute.
            env: Additional environment variables to set for the command.
            hidden: If True, the command will not be printed to stdout.
            simulate: If True, the command will not be executed, but just printed.
        Returns:
            The subprocess.CompletedProcess object.
        """
        if simulate and not hidden:
            print(f"Simulating: {cmd}")
        else:
            if not hidden:
                print(f"Executing: {cmd}")

            if not env:
                custom_env = None
            else:
                custom_env = os.environ.copy()
                custom_env.update(env or {})

            return subprocess.run(cmd, shell=True, check=True, env=custom_env)
