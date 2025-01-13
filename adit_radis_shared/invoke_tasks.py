import binascii
import ipaddress
import os
import re
import secrets
import shutil
import string
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from os import urandom
from pathlib import Path

import requests
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.core.management.utils import get_random_secret_key
from dotenv import dotenv_values, set_key
from invoke.context import Context
from invoke.exceptions import Exit
from invoke.tasks import task

###
# Global config
###

# Those variables are set in tasks.py of the project root.
PROJECT_NAME: str | None = None
PROJECT_DIR: Path | None = None
FORCE_SWARM_MODE_IN_PRODUCTION: bool = False


###
# Utility methods
###


class Utility:
    _is_production_cached: bool | None = None

    @staticmethod
    def get_project_name():
        assert PROJECT_NAME is not None
        return PROJECT_NAME

    @staticmethod
    def get_project_dir():
        assert PROJECT_DIR is not None
        return PROJECT_DIR

    @staticmethod
    def load_config_from_env_file() -> dict[str, str | None]:
        env_file = Utility.get_project_dir() / ".env"
        if not env_file.exists():
            raise Exit("Missing .env file!")

        return dotenv_values(env_file)

    @staticmethod
    def is_production() -> bool:
        global _is_production_cached
        if Utility._is_production_cached is None:
            config = Utility.load_config_from_env_file()

            if "ENVIRONMENT" not in config:
                raise Exit("Missing ENVIRONMENT setting in .env file.")

            environment = config["ENVIRONMENT"]
            if environment not in ["development", "production"]:
                raise Exit(f"Invalid ENVIRONMENT setting {environment} in .env file.")

            Utility._is_production_cached = environment == "production"

        return Utility._is_production_cached

    @staticmethod
    def get_compose_base_file():
        return Utility.get_project_dir() / "docker-compose.base.yml"

    @staticmethod
    def get_compose_env_file():
        if Utility.is_production():
            return Utility.get_project_dir() / "docker-compose.prod.yml"
        return Utility.get_project_dir() / "docker-compose.dev.yml"

    @staticmethod
    def get_stack_name() -> str:
        config = Utility.load_config_from_env_file()
        if stack_name := config.get("STACK_NAME", ""):
            return stack_name

        if Utility.is_production():
            return f"{Utility.get_project_name()}_prod"
        return f"{Utility.get_project_name()}_dev"

    @staticmethod
    def build_compose_cmd(profiles: list[str] = []):
        cmd = "docker compose"
        cmd += f" -f {Utility.get_compose_base_file()}"
        cmd += f" -f {Utility.get_compose_env_file()}"
        cmd += f" -p {Utility.get_stack_name()}"
        for profile in profiles:
            cmd += f" --profile {profile}"
        return cmd

    @staticmethod
    def check_compose_up():
        stack_name = Utility.get_stack_name()
        result = Utility.capture("docker compose ls")
        for line in result.splitlines():
            if line.startswith(stack_name) and line.find("running") != -1:
                return True
        return False

    @staticmethod
    def prepare_environment():
        config = Utility.load_config_from_env_file()

        backup_dir = config.get("BACKUP_DIR")
        if not backup_dir:
            return

        backup_path = Path(backup_dir)
        if not backup_path.exists():
            print(f"Creating non-existent BACKUP_DIR {backup_path.absolute()}")
            backup_path.mkdir(parents=True, exist_ok=True)
        if not backup_path.is_dir():
            raise Exit(f"Invalid BACKUP_DIR {backup_path.absolute()}.")

    @staticmethod
    def find_running_container_id(name: str):
        stack_name = Utility.get_stack_name()
        sep = "_" if Utility.is_production() else "-"
        cmd = f"docker ps -q -f name={stack_name}{sep}{name} -f status=running"
        cmd += " | head -n1"
        result = Utility.capture(cmd)
        if result:
            container_id = result.strip()
            if container_id:
                return container_id
        return None

    @staticmethod
    def confirm(question: str) -> bool:
        valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
        while True:
            sys.stdout.write(f"{question} [y/N] ")
            choice = input().lower()
            if choice == "":
                return False
            elif choice in valid:
                return valid[choice]
            else:
                sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

    @staticmethod
    def capture(cmd: str) -> str:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout

    @staticmethod
    def get_latest_remote_version_tag(owner, repo) -> str | None:
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

    @staticmethod
    def get_latest_local_version_tag() -> str:
        # Get all tags sorted by creation date (newest first)
        result = Utility.capture("git tag -l --sort=-creatordate")
        all_tags = result.splitlines()

        version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
        for tag in all_tags:
            if version_pattern.match(tag):
                return tag

        return "0.0.0"

    @staticmethod
    def generate_django_secret_key():
        return get_random_secret_key()

    @staticmethod
    def generate_secure_password(length=12):
        characters = string.ascii_letters + string.digits + string.punctuation
        return "".join(secrets.choice(characters) for _ in range(length))

    @staticmethod
    def generate_auth_token(length=20):
        return binascii.hexlify(urandom(length)).decode()

    @staticmethod
    def generate_self_signed_certificates(
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

    @staticmethod
    def generate_chain_file_for_host(hostname: str):
        """Generates the chain file for a signed certificate"""
        url = (
            f"https://whatsmychaincert.com/generate?include_leaf=1&host={hostname}"
            "&submit_btn=Generate+Chain&include_root=1"
        )
        response = requests.get(url)
        response.raise_for_status()
        chain_pem = response.content
        return chain_pem


###
# Tasks
###


@task(iterable=["profile"])
def compose_up(ctx: Context, no_build: bool = False, profile: list[str] = []):
    """Start development containers"""
    Utility.prepare_environment()

    if FORCE_SWARM_MODE_IN_PRODUCTION:
        config = Utility.load_config_from_env_file()
        if config.get("ENVIRONMENT") != "development":
            raise Exit(
                "compose-up task can only be used in development environment. "
                "Check ENVIRONMENT setting in .env file."
            )

    version = Utility.get_latest_local_version_tag()
    if not Utility.is_production():
        version += "-dev"

    cmd = f"{Utility.build_compose_cmd(profile)} up"
    if no_build:
        cmd += " --no-build"
    cmd += " --detach"
    ctx.run(cmd, env={"PROJECT_VERSION": version}, pty=True)


@task(iterable=["profile"])
def compose_down(ctx: Context, cleanup: bool = False, profile: list[str] = []):
    """Stop development containers"""
    cmd = f"{Utility.build_compose_cmd(profile)} down"
    if cleanup:
        cmd += " --remove-orphans --volumes"
    ctx.run(cmd, pty=True)


@task
def stack_deploy(ctx: Context, build: bool = False):
    """Deploy the production stack to Docker Swarm. Optional build it before."""
    Utility.prepare_environment()

    if FORCE_SWARM_MODE_IN_PRODUCTION:
        config = Utility.load_config_from_env_file()
        if config.get("ENVIRONMENT") != "production":
            raise Exit(
                "stack-deploy task can only be used in production environment. "
                "Check ENVIRONMENT setting in .env file."
            )

    if build:
        cmd = f"{Utility.build_compose_cmd()} build"
        ctx.run(cmd, pty=True)

    version = Utility.get_latest_local_version_tag()
    if not Utility.is_production():
        version += "-dev"

    # Docker Swarm Mode does not support .env files so we load the .env file manually
    # and pass the content as an environment variables.
    env = Utility.load_config_from_env_file()

    env["PROJECT_VERSION"] = version

    cmd = "docker stack deploy --detach "
    cmd += f" -c {Utility.get_compose_base_file()}"
    cmd += f" -c {Utility.get_compose_env_file()}"
    cmd += f" {Utility.get_stack_name()}"
    ctx.run(cmd, env=env, pty=True)


@task
def stack_rm(ctx: Context):
    """Remove the production stack from Docker Swarm"""
    ctx.run(f"docker stack rm {Utility.get_stack_name()}", pty=True)


@task
def web_shell(ctx: Context):
    """Open Python shell in web container of specified environment"""
    ctx.run(f"{Utility.build_compose_cmd()} exec web python manage.py shell_plus", pty=True)


@task
def format(ctx: Context):
    """Format the source code with ruff and djlint"""
    print("Formatting Python code with ruff...")
    ctx.run("poetry run ruff format .", pty=True)

    print("Sorting Python imports with ruff...")
    ctx.run("poetry run ruff check . --fix --select I", pty=True)

    print("Formatting Django templates with djlint...")
    ctx.run("poetry run djlint . --reformat", pty=True)


@task
def lint(ctx: Context):
    """Lint the source code (ruff, djlint, pyright)"""
    print("Linting Python code with ruff...")
    ctx.run("poetry run ruff check .", pty=True)

    print("Linting Python code with pyright...")
    ctx.run("poetry run pyright", pty=True)

    print("Linting Django templates with djlint...")
    ctx.run("poetry run djlint . --lint", pty=True)


@task
def test(
    ctx: Context,
    path: str | None = None,
    cov: bool | str = False,
    html: bool = False,
    keyword: str | None = None,
    mark: str | None = None,
    stdout: bool = False,
    failfast: bool = False,
):
    """Run the test suite"""
    if not Utility.check_compose_up():
        raise Exit("Integration tests need dev containers running.\nRun 'invoke compose-up' first.")

    cmd = (
        f"{Utility.build_compose_cmd()} exec "
        f"--env DJANGO_SETTINGS_MODULE={Utility.get_project_name()}.settings.test web pytest "
    )
    if cov:
        cmd += "--cov "
        if isinstance(cov, str):
            cmd += f"={cov} "
        if html:
            cmd += "--cov-report=html"
    if keyword:
        cmd += f"-k {keyword} "
    if mark:
        cmd += f"-m {mark} "
    if stdout:
        cmd += "-s "
    if failfast:
        cmd += "-x "
    if path:
        cmd += path

    ctx.run(cmd, pty=True)


@task
def init_workspace(ctx: Context):
    """Initialize workspace for Github Codespaces, Gitpod or local development"""
    env_file = Utility.get_project_dir() / ".env"
    if env_file.is_file():
        raise Exit("Workspace already initialized (.env file exists).")

    shutil.copy(Utility.get_project_dir() / "example.env", env_file)

    def modify_env_file(domain: str | None = None, uses_https: bool = False):
        if domain:
            hosts = f".localhost,127.0.0.1,[::1],{domain}"
            set_key(env_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
            set_key(env_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
            set_key(env_file, "SITE_DOMAIN", domain, quote_mode="never")

            origin = f"{"https" if uses_https else "http"}://{domain}"
            set_key(env_file, "DJANGO_CSRF_TRUSTED_ORIGINS", origin, quote_mode="never")

        if uses_https:
            set_key(env_file, "SITE_USES_HTTPS", "true", quote_mode="never")

        set_key(env_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

    if os.environ.get("CODESPACE_NAME"):
        # Inside GitHub Codespaces
        domain = f"{os.environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
        modify_env_file(domain, uses_https=True)
    elif os.environ.get("GITPOD_WORKSPACE_ID"):
        # Inside Gitpod
        result = ctx.run("gp url 8000", hide=True, pty=True)
        assert result and result.ok
        domain = result.stdout.strip().removeprefix("https://")
        modify_env_file(domain, uses_https=True)
    else:
        # Inside some local environment
        modify_env_file()

    print("Successfully initialized .env file.")


@task
def randomize_env_secrets(ctx: Context):
    """Randomize secrets in the .env file"""
    env_file = Utility.get_project_dir() / ".env"
    if not env_file.is_file():
        raise Exit("Workspace not initialized (.env file does not exist).")

    set_key(env_file, "DJANGO_SECRET_KEY", Utility.generate_django_secret_key())
    set_key(env_file, "POSTGRES_PASSWORD", Utility.generate_secure_password())
    set_key(env_file, "ADMIN_USER_PASSWORD", Utility.generate_secure_password())
    set_key(env_file, "ADMIN_AUTH_TOKEN", Utility.generate_auth_token())


@task
def generate_django_secret_key(ctx: Context):
    """Generate a Django secret key and print it to the console"""
    print(Utility.generate_django_secret_key())


@task
def generate_secure_password(ctx: Context, length=12):
    """Generate a secure password and print it to the console"""
    print(Utility.generate_secure_password(length))


@task
def generate_auth_token(ctx: Context, length=20):
    """Generate an authentication token and print it to the console"""
    print(Utility.generate_auth_token(length))


@task
def generate_certificate_files(ctx: Context):
    """Generate self-signed certificate files"""
    config = Utility.load_config_from_env_file()

    if "SSL_HOSTNAME" not in config:
        raise Exit("Missing SSL_HOSTNAME setting in .env file")
    if "SSL_SERVER_CERT_FILE" not in config:
        raise Exit("Missing SSL_SERVER_CERT_FILE setting in .env file")
    if "SSL_SERVER_KEY_FILE" not in config:
        raise Exit("Missing SSL_SERVER_KEY_FILE setting in .env file")

    hostname = config["SSL_HOSTNAME"]
    assert hostname

    ip_addresses = config.get("SSL_IP_ADDRESSES", "")
    assert isinstance(ip_addresses, str)
    ip_addresses = [item.strip() for item in ip_addresses.split(",") if item.strip()]

    (cert_pem, key_pem) = Utility.generate_self_signed_certificates(hostname, ip_addresses)

    cert_file = config["SSL_SERVER_CERT_FILE"]
    assert cert_file
    cert_path = Path(cert_file)
    if cert_path.is_file():
        raise Exit(f"A SSL certificate file {cert_path.absolute()} already exists.")

    key_file = config["SSL_SERVER_KEY_FILE"]
    assert key_file
    key_path = Path(key_file)
    if key_path.is_file():
        raise Exit(f"Key file {key_path.absolute()} already exists. Skipping.")

    chain_file = config["SSL_SERVER_CHAIN_FILE"]
    assert chain_file
    chain_path = Path(chain_file)
    if chain_path.is_file():
        raise Exit(f"Chain file {chain_path.absolute()} already exists. Skipping.")

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


@task
def generate_certificate_chain(ctx: Context):
    """Generate certificate chain file for a signed certificate"""
    config = Utility.load_config_from_env_file()

    if "SSL_HOSTNAME" not in config:
        raise Exit("Missing SSL_HOSTNAME setting in .env file")
    if "SSL_SERVER_CERT_FILE" not in config:
        raise Exit("Missing SSL_SERVER_CERT_FILE setting in .env file")
    if "SSL_SERVER_CHAIN_FILE" not in config:
        raise Exit("Missing SSL_SERVER_CHAIN_FILE setting in .env file")

    hostname = config["SSL_HOSTNAME"]
    assert hostname

    cert_file = config["SSL_SERVER_CERT_FILE"]
    assert cert_file

    chain_file = config["SSL_SERVER_CHAIN_FILE"]
    assert chain_file

    cert_path = Path(cert_file)
    if not cert_path.is_file():
        raise Exit(
            f"SSL certificate file {cert_path.absolute()} does not exist. "
            "You can generate an unsigned certificate with 'invoke generate-certificate-files'"
            " with included chain file. If you have a signed certificate from a CA, be sure to"
            " provide the correct SSL_SERVER_CERT_FILE setting in '.env'. Skipping."
        )

    chain_path = Path(chain_file)
    if chain_path.is_file():
        raise Exit(
            f"Chain file {chain_path.absolute()} already exist. Delete file to generate a new one. "
            "Skipping."
        )

    try:
        chain_pem = Utility.generate_chain_file_for_host(hostname)
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


@task
def show_outdated(ctx: Context):
    """Show outdated dependencies"""
    print("### Outdated Python dependencies ###")
    result = ctx.run("poetry show --outdated --top-level", pty=True)
    assert result and result.ok
    print(result.stderr.strip())

    print("### Outdated NPM dependencies ###")
    ctx.run("npm outdated", pty=True)


@task
def try_github_actions(ctx: Context):
    """Try Github Actions locally using Act"""
    act_path = Utility.get_project_dir() / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        ctx.run(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            hide=True,
            pty=True,
        )
    ctx.run(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest", pty=True)


@task
def backup_db(ctx: Context):
    """Backup database

    For backup location see setting DBBACKUP_STORAGE_OPTIONS
    For possible commands see:
    https://django-dbbackup.readthedocs.io/en/master/commands.html
    """
    settings = (
        f"{Utility.get_project_name()}.settings.production"
        if Utility.is_production()
        else f"{Utility.get_project_name()}.settings.development"
    )
    web_container_id = Utility.find_running_container_id("web")
    if web_container_id is None:
        raise Exit("Web container is not running. Run 'invoke compose-up' first.")

    ctx.run(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        ),
        pty=True,
    )


@task
def restore_db(ctx: Context):
    """Restore database from previous backup"""
    settings = (
        f"{Utility.get_project_name()}.settings.production"
        if Utility.is_production()
        else f"{Utility.get_project_name()}.settings.development"
    )
    web_container_id = Utility.find_running_container_id("web")
    if web_container_id is None:
        raise Exit("Web container is not running. Run 'invoke compose-up' first.")

    ctx.run(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        ),
        pty=True,
    )


@task
def upgrade_postgresql(ctx: Context, version: str = "latest"):
    volume = f"{Utility.get_stack_name()}_postgres_data"
    print(f"Upgrading PostgreSQL database in volume {volume} environment to {version}.")
    print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
    if Utility.confirm("Are you sure you want to proceed?"):
        print("Starting docker container that upgrades the database files.")
        print("Watch the output if everything went fine or if any further steps are necessary.")
        ctx.run(
            f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
            f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}",
            pty=True,
        )
    else:
        print("Cancelled")
