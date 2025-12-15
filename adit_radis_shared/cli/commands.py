import os
import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import set_key

from .helper import CommandHelper


def init_workspace(
    web_dev_port: Annotated[int | None, typer.Option(help="Web dev port to use")] = None,
    postgres_dev_port: Annotated[int | None, typer.Option(help="Postgres dev port to use")] = None,
    remote_debugging_port: Annotated[
        int | None, typer.Option(help="Remote debugging port to use")
    ] = None,
):
    """Initialize workspace for Github Codespaces or local development"""

    helper = CommandHelper()

    env_file = helper.root_path / ".env"
    if env_file.is_file():
        print("Workspace already initialized (.env file exists). Skipping.")
        sys.exit()

    example_env_file = helper.root_path / "example.env"
    if not example_env_file.is_file():
        sys.exit("Missing example.env file!")

    shutil.copy(helper.root_path / "example.env", env_file)

    if os.environ.get("CODESPACE_NAME"):
        # Inside GitHub Codespaces
        domain = f"{os.environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
        hosts = f".localhost,127.0.0.1,[::1],{domain}"
        set_key(env_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
        set_key(env_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
        set_key(env_file, "SITE_DOMAIN", domain, quote_mode="never")
        origin = f"https://{domain}"
        set_key(env_file, "DJANGO_CSRF_TRUSTED_ORIGINS", origin, quote_mode="never")

    if web_dev_port is not None:
        set_key(env_file, "WEB_DEV_PORT", str(web_dev_port), quote_mode="never")

    if postgres_dev_port is not None:
        set_key(env_file, "POSTGRES_DEV_PORT", str(postgres_dev_port), quote_mode="never")

    if remote_debugging_port is not None:
        set_key(env_file, "REMOTE_DEBUGGING_PORT", str(remote_debugging_port), quote_mode="never")

    set_key(env_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

    print("Successfully initialized .env file.")


def randomize_env_secrets():
    """Randomize secrets in the .env file"""

    helper = CommandHelper()

    env_file = helper.root_path / ".env"
    if not env_file.is_file():
        sys.exit("Workspace not initialized (.env file does not exist).")

    set_key(env_file, "DJANGO_SECRET_KEY", helper.generate_django_secret_key())
    set_key(env_file, "POSTGRES_PASSWORD", helper.generate_secure_password())
    set_key(env_file, "ADMIN_USER_PASSWORD", helper.generate_secure_password())
    set_key(env_file, "ADMIN_AUTH_TOKEN", helper.generate_auth_token())


def compose_build(
    profile: Annotated[
        list[str] | None, typer.Option(help="Docker compose profile(s) to use")
    ] = None,
    extra_args: Annotated[
        list[str] | None, typer.Argument(help="Extra arguments (after '--')")
    ] = None,
):
    """Build the base images with docker compose"""

    profile = profile or []
    extra_args = extra_args or []

    helper = CommandHelper()
    helper.prepare_environment()

    cmd = f"{helper.build_compose_cmd(profile)} build"
    if extra_args:
        cmd += " " + " ".join(extra_args)

    helper.execute_cmd(
        cmd,
        env={
            "COMPOSE_BAKE": "true",
            "PROJECT_VERSION": helper.get_local_project_version(),
        },
    )


def compose_pull(
    extra_args: Annotated[
        list[str] | None, typer.Argument(help="Extra arguments (after '--')")
    ] = None,
):
    """Pull images with docker compose"""

    extra_args = extra_args or []

    helper = CommandHelper()
    cmd = f"{helper.build_compose_cmd()} pull"
    if extra_args:
        cmd += " " + " ".join(extra_args)

    helper.execute_cmd(
        cmd,
        env={
            "COMPOSE_BAKE": "true",
            "PROJECT_VERSION": helper.get_local_project_version(),
        },
    )


def compose_up(
    profile: Annotated[
        list[str] | None, typer.Option(help="Docker compose profile(s) to use")
    ] = None,
    extra_args: Annotated[
        list[str] | None, typer.Argument(help="Extra arguments (after '--')")
    ] = None,
):
    """Start stack with docker compose"""

    profile = profile or []
    extra_args = extra_args or []

    helper = CommandHelper()
    helper.prepare_environment()

    if helper.is_production():
        sys.exit(
            "Starting containers with compose-up can only be used in development. "
            "Check ENVIRONMENT setting in .env file."
        )

    cmd = f"{helper.build_compose_cmd(profile)} up"
    if extra_args:
        cmd += " " + " ".join(extra_args)

    helper.execute_cmd(
        cmd,
        env={
            "COMPOSE_BAKE": "true",
            "PROJECT_VERSION": helper.get_local_project_version(),
        },
    )


def compose_down(
    profile: Annotated[
        list[str] | None, typer.Option(help="Docker compose profile(s) to use")
    ] = None,
    extra_args: Annotated[
        list[str] | None, typer.Argument(help="Extra arguments (after '--')")
    ] = None,
):
    """Stop stack with docker compose"""

    profile = profile or []
    extra_args = extra_args or []

    helper = CommandHelper()

    cmd = f"{helper.build_compose_cmd(profile)} down"
    if extra_args:
        cmd += " " + " ".join(extra_args)

    helper.execute_cmd(cmd, env={"PROJECT_VERSION": helper.get_local_project_version()})


def stack_deploy():
    """Deploy stack with Docker Swarm"""

    helper = CommandHelper()
    helper.prepare_environment()

    if not helper.is_production():
        sys.exit(
            "stack-deploy task can only be used in production environment. "
            "Check ENVIRONMENT setting in .env file."
        )

    # Docker Swarm Mode does not support .env files so we load the .env file manually
    # and pass the content as an environment variables.
    env = helper.load_config_from_env_file()

    env["PROJECT_VERSION"] = helper.get_local_project_version()

    cmd = "docker stack deploy --detach "
    cmd += f" -c {helper.get_compose_base_file()}"
    cmd += f" -c {helper.get_compose_env_file()}"
    cmd += f" {helper.get_stack_name()}"
    helper.execute_cmd(cmd, env=env)


def stack_rm():
    """Remove stack from Docker Swarm"""

    helper = CommandHelper()
    helper.execute_cmd(f"docker stack rm {helper.get_stack_name()}")


def lint():
    """Lint the source code with ruff, pyright and djlint"""

    helper = CommandHelper()

    print("Linting Python code with ruff...")
    helper.execute_cmd("uv run ruff check .")

    print("Linting Python code with pyright...")
    helper.execute_cmd("uv run pyright")

    print("Linting Django templates with djlint...")
    helper.execute_cmd("uv run djlint . --lint")


def format_code():
    """Format code with ruff and djlint"""

    helper = CommandHelper()

    print("Formatting Python code with ruff...")
    helper.execute_cmd("uv run ruff format .")

    print("Sorting Python imports with ruff...")
    helper.execute_cmd("uv run ruff check . --fix --select I")

    print("Formatting Django templates with djlint...")
    helper.execute_cmd("uv run djlint . --reformat")


def test(
    extra_args: Annotated[
        list[str] | None, typer.Argument(help="Extra arguments (after '--')")
    ] = None,
):
    """Run the test suite with pytest"""

    extra_args = extra_args or []

    helper = CommandHelper()

    if not helper.check_compose_up():
        sys.exit("Acceptance tests need dev containers running.")

    cmd = (
        f"{helper.build_compose_cmd()} exec "
        f"--env DJANGO_SETTINGS_MODULE={helper.project_id}.settings.test web pytest"
    )
    if extra_args:
        cmd += " " + " ".join(extra_args)

    helper.execute_cmd(cmd)


def shell(
    container: Annotated[str, typer.Argument(help="Container name ('web' by default)")] = "web",
):
    """Open a Python shell in the specified container"""

    helper = CommandHelper()

    helper.execute_cmd(f"{helper.build_compose_cmd()} exec {container} python manage.py shell_plus")


def show_outdated():
    """Show outdated dependencies"""

    helper = CommandHelper()

    print("### Outdated Python dependencies ###")
    helper.print_uv_outdated()

    print("### Outdated NPM dependencies ###")
    helper.execute_cmd("npm outdated || true", hidden=True)


def db_backup():
    """Backup database in running container stack"""

    helper = CommandHelper()

    settings = (
        f"{helper.project_id}.settings.production"
        if helper.is_production()
        else f"{helper.project_id}.settings.development"
    )

    web_container_id = helper.find_running_container_id("web")
    if web_container_id is None:
        sys.exit("Web container is not running.")

    helper.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        )
    )


def db_restore():
    """Restore database in running container stack from the latest backup"""

    helper = CommandHelper()

    settings = (
        f"{helper.project_id}.settings.production"
        if helper.is_production()
        else f"{helper.project_id}.settings.development"
    )
    web_container_id = helper.find_running_container_id("web")
    if web_container_id is None:
        sys.exit("Web container is not running. Run 'uv run ./manage.py compose-up' first.")

    helper.execute_cmd(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        )
    )


def generate_auth_token(
    length: Annotated[int, typer.Argument(help="Length of the token (default: 20)")] = 20,
):
    """Generate a secure authentication token"""

    helper = CommandHelper()
    print(helper.generate_auth_token(length))


def generate_secure_password(
    length: Annotated[int, typer.Argument(help="Length of the password (default: 20)")] = 20,
):
    """Generate a secure password"""

    helper = CommandHelper()
    print(helper.generate_secure_password(length))


def generate_django_secret_key():
    """Generate a Django secret key"""

    helper = CommandHelper()
    print(helper.generate_django_secret_key())


def generate_certificate_chain():
    """Generate a SSL certificate chain file for the provided signed leaf certificate"""

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


def generate_certificate_files():
    """Generate self-signed certificate files for local development"""

    helper = CommandHelper()

    config = helper.load_config_from_env_file()

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

    (cert_pem, key_pem) = helper.generate_self_signed_certificates(hostname, ip_addresses)

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


def upgrade_postgres_volume(
    version: Annotated[str, typer.Option(help="PostgreSQL version to upgrade to")] = "latest",
):
    """Upgrade PostgreSQL volume data"""

    helper = CommandHelper()

    volume = f"{helper.get_stack_name()}_postgres_data"
    print(f"Upgrading PostgreSQL database in volume {volume} environment to {version}.")
    print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
    if helper.confirm("Are you sure you want to proceed?"):
        print("Starting docker container that upgrades the database files.")
        print("Watch the output if everything went fine or if any further steps are necessary.")
        helper.execute_cmd(
            f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
            f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}"
        )
    else:
        print("Cancelled")


def try_github_actions():
    """Try Github Actions locally using Act"""

    helper = CommandHelper()

    act_path = helper.root_path / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        helper.execute_cmd(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            hidden=True,
        )

    helper.execute_cmd(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest")
