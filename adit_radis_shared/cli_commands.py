import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import set_key
from rich import print

from . import cli_helpers as helpers


def init_workspace():
    """Initialize workspace for Github Codespaces or local development"""

    env_file = helpers.get_root_path() / ".env"
    if env_file.is_file():
        print(
            "[bold yellow]Workspace already initialized (.env file exists). Skipping.[/bold yellow]"
        )
        sys.exit()

    example_env_file = helpers.get_root_path() / "example.env"
    if not example_env_file.is_file():
        sys.exit("Missing example.env file!")

    shutil.copy(helpers.get_root_path() / "example.env", env_file)

    def modify_env_file(domain: str | None = None, uses_https: bool = False):
        if domain:
            hosts = f".localhost,127.0.0.1,[::1],{domain}"
            set_key(env_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
            set_key(env_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
            set_key(env_file, "SITE_DOMAIN", domain, quote_mode="never")

            origin = f"{'https' if uses_https else 'http'}://{domain}"
            set_key(env_file, "DJANGO_CSRF_TRUSTED_ORIGINS", origin, quote_mode="never")

        set_key(env_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

    if os.environ.get("CODESPACE_NAME"):
        # Inside GitHub Codespaces
        domain = f"{os.environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
        modify_env_file(domain, uses_https=True)
    elif os.environ.get("GITPOD_WORKSPACE_ID"):
        # Inside Gitpod
        result = subprocess.run(
            "gp url 8000", shell=True, capture_output=True, text=True, check=True
        )
        domain = result.stdout.strip().removeprefix("https://")
        modify_env_file(domain, uses_https=True)
    else:
        # Inside some local environment
        modify_env_file()

    print("Successfully initialized .env file.")


def compose_up(
    build: Annotated[bool, typer.Option(help="Do not build images")] = True,
    profile: Annotated[list[str], typer.Option(help="Docker Compose profile(s)")] = [],
):
    """Start stack with docker compose"""

    helpers.prepare_environment()

    if helpers.is_production():
        sys.exit(
            "Starting containers with compose-up can only be used in development. "
            "Check ENVIRONMENT setting in .env file."
        )

    version = helpers.get_latest_local_version_tag()
    if not helpers.is_production():
        version += "-dev"

    cmd = f"{helpers.build_compose_cmd(profile)} up"

    if not build:
        cmd += " --no-build"

    cmd += " --detach"
    helpers.execute_cmd(cmd, env={"PROJECT_VERSION": version})


def compose_down(
    cleanup: Annotated[bool, typer.Option(help="Remove orphans and volumes")] = False,
    profile: Annotated[list[str], typer.Option(help="Docker Compose profile(s)")] = [],
):
    """Stop stack with docker compose"""

    cmd = f"{helpers.build_compose_cmd(profile)} down"

    if cleanup:
        cmd += " --remove-orphans --volumes"

    helpers.execute_cmd(cmd)


def stack_deploy(build: Annotated[bool, typer.Option(help="Build images")] = False):
    """Deploy stack with docker swarm"""

    helpers.prepare_environment()

    config = helpers.load_config_from_env_file()
    if config.get("ENVIRONMENT") != "production":
        sys.exit(
            "stack-deploy task can only be used in production environment. "
            "Check ENVIRONMENT setting in .env file."
        )

    if build:
        cmd = f"{helpers.build_compose_cmd()} build"
        helpers.execute_cmd(cmd)

    version = helpers.get_latest_local_version_tag()
    if not helpers.is_production():
        version += "-dev"

    # Docker Swarm Mode does not support .env files so we load the .env file manually
    # and pass the content as an environment variables.
    env = helpers.load_config_from_env_file()

    env["PROJECT_VERSION"] = version

    cmd = "docker stack deploy --detach "
    cmd += f" -c {helpers.get_compose_base_file()}"
    cmd += f" -c {helpers.get_compose_env_file()}"
    cmd += f" {helpers.get_stack_name()}"
    helpers.execute_cmd(cmd, env=env)


def stack_rm():
    """Remove stack from docker swarm"""

    helpers.execute_cmd(f"docker stack rm {helpers.get_stack_name()}")


def lint():
    """Lint the source code with ruff, pyright and djlint"""

    print("Linting Python code with ruff...")
    helpers.execute_cmd("uv run ruff check .")

    print("Linting Python code with pyright...")
    helpers.execute_cmd("uv run pyright")

    print("Linting Django templates with djlint...")
    helpers.execute_cmd("uv run djlint . --lint")


def format_code():
    """Format the source code with ruff and djlint"""

    print("Formatting Python code with ruff...")
    helpers.execute_cmd("uv run ruff format .")

    print("Sorting Python imports with ruff...")
    helpers.execute_cmd("uv run ruff check . --fix --select I")

    print("Formatting Django templates with djlint...")
    helpers.execute_cmd("uv run djlint . --reformat")


def test(ctx: typer.Context):
    """Run the test suite with pytest"""

    if not helpers.check_compose_up():
        sys.exit(
            "Acceptance tests need dev containers running.\nRun 'uv run ./cli.py compose-up' first."
        )

    cmd = (
        f"{helpers.build_compose_cmd()} exec "
        f"--env DJANGO_SETTINGS_MODULE={helpers.get_project_id()}.settings.test web pytest "
    )
    cmd += " ".join(ctx.args)
    helpers.execute_cmd(cmd)


def show_outdated():
    """Show outdated dependencies"""

    print("### Outdated Python dependencies ###")
    helpers.print_uv_outdated()

    print("### Outdated NPM dependencies ###")
    helpers.execute_cmd("npm outdated", hidden=True)


def backup_db():
    """Backup database in running container stack

    For backup location see setting DBBACKUP_STORAGE_OPTIONS
    For possible commands see:
    https://django-dbbackup.readthedocs.io/en/master/commands.html
    """
    settings = (
        f"{helpers.get_project_id()}.settings.production"
        if helpers.is_production()
        else f"{helpers.get_project_id()}.settings.development"
    )

    web_container_id = helpers.find_running_container_id("web")
    if web_container_id is None:
        sys.exit("Web container is not running. Run 'uv run ./cli.py compose-up' first.")

    helpers.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        )
    )


def restore_db():
    """Restore database in container from the last backup"""

    settings = (
        f"{helpers.get_project_id()}.settings.production"
        if helpers.is_production()
        else f"{helpers.get_project_id()}.settings.development"
    )
    web_container_id = helpers.find_running_container_id("web")
    if web_container_id is None:
        sys.exit("Web container is not running. Run 'uv run ./manage.py compose-up' first.")

    helpers.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        )
    )


def shell(
    container: Annotated[str, typer.Argument(help="Container name ('web' by default)")] = "web",
):
    """Open a Python shell in the specified container container"""

    helpers.execute_cmd(
        f"{helpers.build_compose_cmd()} exec {container} python manage.py shell_plus"
    )


def generate_certificate_files():
    """Generate self-signed certificate files"""

    config = helpers.load_config_from_env_file()

    if "SSL_HOSTNAME" not in config:
        sys.exit("Missing SSL_HOSTNAME setting in .env file")
    if "SSL_SERVER_CERT_FILE" not in config:
        sys.exit("Missing SSL_SERVER_CERT_FILE setting in .env file")
    if "SSL_SERVER_KEY_FILE" not in config:
        sys.exit("Missing SSL_SERVER_KEY_FILE setting in .env file")

    hostname = config["SSL_HOSTNAME"]
    assert hostname

    ip_addresses = config.get("SSL_IP_ADDRESSES", "")
    assert isinstance(ip_addresses, str)
    ip_addresses = [item.strip() for item in ip_addresses.split(",") if item.strip()]

    (cert_pem, key_pem) = helpers.generate_self_signed_certificates(hostname, ip_addresses)

    cert_file = config["SSL_SERVER_CERT_FILE"]
    assert cert_file
    cert_path = Path(cert_file)
    if cert_path.is_file():
        sys.exit(f"A SSL certificate file {cert_path.absolute()} already exists. Skipping.")

    key_file = config["SSL_SERVER_KEY_FILE"]
    assert key_file
    key_path = Path(key_file)
    if key_path.is_file():
        sys.exit(f"Key file {key_path.absolute()} already exists. Skipping.")

    chain_file = config["SSL_SERVER_CHAIN_FILE"]
    assert chain_file
    chain_path = Path(chain_file)
    if chain_path.is_file():
        sys.exit(f"Chain file {chain_path.absolute()} already exists. Skipping.")

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


def generate_certificate_chain(self):
    """Generate certificate chain file for a signed certificate"""

    config = self.load_config_from_env_file()

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
        chain_pem = self.generate_chain_file_for_host(hostname)
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


def generate_django_secret_key():
    """Generate a Django secret key"""

    print(helpers.generate_django_secret_key())


def generate_secure_password(
    length: Annotated[int, typer.Option(help="Length of the password")] = 12,
):
    """Generate a secure password"""

    print(helpers.generate_secure_password(length))


def generate_auth_token(
    length: Annotated[int, typer.Option(help="Length of the token")] = 20,
):
    """Generate an authentication token"""

    print(helpers.generate_auth_token(length))


def randomize_env_secrets():
    """Randomize secrets in the .env file"""

    env_file = helpers.get_root_path() / ".env"
    if not env_file.is_file():
        sys.exit("Workspace not initialized (.env file does not exist).")

    set_key(env_file, "DJANGO_SECRET_KEY", helpers.generate_django_secret_key())
    set_key(env_file, "POSTGRES_PASSWORD", helpers.generate_secure_password())
    set_key(env_file, "ADMIN_USER_PASSWORD", helpers.generate_secure_password())
    set_key(env_file, "ADMIN_AUTH_TOKEN", helpers.generate_auth_token())


def upgrade_postgres_volume(
    version: Annotated[str, typer.Option(help="PostgreSQL version to upgrade to")] = "latest",
):
    """Upgrade PostgreSQL volume data"""

    volume = f"{helpers.get_stack_name()}_postgres_data"
    print(f"Upgrading PostgreSQL database in volume {volume} environment to {version}.")
    print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
    if helpers.confirm("Are you sure you want to proceed?"):
        print("Starting docker container that upgrades the database files.")
        print("Watch the output if everything went fine or if any further steps are necessary.")
        helpers.execute_cmd(
            f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
            f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}"
        )
    else:
        print("Cancelled")


def try_github_actions():
    """Try Github Actions locally using Act"""

    act_path = helpers.get_root_path() / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        helpers.execute_cmd(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            hidden=True,
        )

    helpers.execute_cmd(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest")
