import argparse
import os
import shutil
import sys
from pathlib import Path

from dotenv import set_key

from adit_radis_shared.script_helper import ScriptHelper


class DefaultScripts:
    def __init__(
        self, project_name: str, project_path: Path, force_swarm_mode_in_production: bool = False
    ):
        self.project_name = project_name
        self.project_path = project_path
        self.force_swarm_mode_in_production = force_swarm_mode_in_production

    def _setup_helper(self, args) -> ScriptHelper:
        simulate = False
        if "simulate" in args and args.simulate:
            simulate = True

        return ScriptHelper(
            self.project_name,
            self.project_path,
            simulate_execution=simulate,
        )

    def compose_up(self):
        """Start stack with docker compose"""

        class ComposeUpArgs(argparse.Namespace):
            no_build: bool
            profile: list[str]
            simulate: bool

        parser = argparse.ArgumentParser(description=self.compose_up.__doc__)
        parser.add_argument("--no-build", action="store_true", help="Do not build images")
        parser.add_argument("--profile", type=str, nargs="+", help="Docker compose profile(s)")
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=ComposeUpArgs())

        helper = self._setup_helper(args)

        helper.prepare_environment()

        if self.force_swarm_mode_in_production:
            if helper.is_production:
                sys.exit(
                    "Starting containers with compose-up can only be used in development. "
                    "Check ENVIRONMENT setting in .env file."
                )

        version = helper.get_latest_local_version_tag()
        if not helper.is_production:
            version += "-dev"

        cmd = f"{helper.build_compose_cmd(args.profile)} up"

        if args.no_build:
            cmd += " --no-build"

        cmd += " --detach"
        helper.execute(cmd, env={"PROJECT_VERSION": version})

    def compose_down(self):
        """Stop stack with docker compose"""

        class ComposeDownArgs(argparse.Namespace):
            cleanup: bool
            profile: list[str]
            simulate: bool

        parser = argparse.ArgumentParser(description=self.compose_down.__doc__)
        parser.add_argument("--cleanup", action="store_true", help="Remove orphans and volumes")
        parser.add_argument("--profile", type=str, nargs="+", help="Docker compose profile(s)")
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=ComposeDownArgs())

        helper = self._setup_helper(args)

        cmd = f"{helper.build_compose_cmd(args.profile)} down"

        if args.cleanup:
            cmd += " --remove-orphans --volumes"

        helper.execute(cmd)

    def stack_deploy(self):
        """Deploy stack with docker swarm"""

        class StackDeployArgs(argparse.Namespace):
            build: bool
            simulate: bool

        parser = argparse.ArgumentParser(description=self.stack_deploy.__doc__)
        parser.add_argument("--build", action="store_true", help="Build images")
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=StackDeployArgs())

        helper = self._setup_helper(args)

        helper.prepare_environment()

        if self.force_swarm_mode_in_production:
            config = helper.load_config_from_env_file()
            if config.get("ENVIRONMENT") != "production":
                sys.exit(
                    "stack-deploy task can only be used in production environment. "
                    "Check ENVIRONMENT setting in .env file."
                )

        if args.build:
            cmd = f"{helper.build_compose_cmd()} build"
            helper.execute(cmd)

        version = helper.get_latest_local_version_tag()
        if not helper.is_production:
            version += "-dev"

        # Docker Swarm Mode does not support .env files so we load the .env file manually
        # and pass the content as an environment variables.
        env = helper.load_config_from_env_file()

        env["PROJECT_VERSION"] = version

        cmd = "docker stack deploy --detach "
        cmd += f" -c {helper.compose_base_file}"
        cmd += f" -c {helper.compose_env_file}"
        cmd += f" {helper.stack_name}"
        helper.execute(cmd, env=env)

    def stack_rm(self):
        """Remove stack from docker swarm"""

        class StackRmArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.stack_rm.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=StackRmArgs())

        helper = self._setup_helper(args)

        helper.execute(f"docker stack rm {helper.stack_name}")

    def web_shell(self):
        """Open Python shell in web container"""

        class WebShellArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.web_shell.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=WebShellArgs())

        helper = self._setup_helper(args)

        helper.execute(f"{helper.build_compose_cmd()} exec web python manage.py shell_plus")

    def format_code(self):
        """Format the source code with ruff and djlint"""

        class FormatArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.format_code.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=FormatArgs())

        helper = self._setup_helper(args)

        print("Formatting Python code with ruff...")
        helper.execute("poetry run ruff format .")

        print("Sorting Python imports with ruff...")
        helper.execute("poetry run ruff check . --fix --select I")

        print("Formatting Django templates with djlint...")
        helper.execute("poetry run djlint . --reformat")

    def lint_code(self):
        """Lint the source code with ruff, pyright and djlint"""

        class LintArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.lint_code.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=LintArgs())

        helper = self._setup_helper(args)

        print("Linting Python code with ruff...")
        helper.execute("poetry run ruff check .")

        print("Linting Python code with pyright...")
        helper.execute("poetry run pyright")

        print("Linting Django templates with djlint...")
        helper.execute("poetry run djlint . --lint")

    def run_tests(self):
        """Run the test suite with pytest"""

        class TestArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.run_tests.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args, unknown_args = parser.parse_known_args(namespace=TestArgs())

        helper = self._setup_helper(args)

        if not helper.check_compose_up():
            sys.exit(
                "Acceptance tests need dev containers running.\n"
                "Run 'poetry run scripts/compose_up.py' first."
            )

        cmd = (
            f"{helper.build_compose_cmd()} exec "
            f"--env DJANGO_SETTINGS_MODULE={helper.project_name}.settings.test web pytest "
        )
        cmd += " ".join(unknown_args)
        helper.execute(cmd)

    def init_workspace(self):
        """Initialize workspace for Github Codespaces or local development"""

        class InitWorkspaceArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.init_workspace.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=InitWorkspaceArgs())

        helper = self._setup_helper(args)

        env_file = helper.project_path / ".env"
        if env_file.is_file():
            sys.exit("Workspace already initialized (.env file exists).")

        shutil.copy(helper.project_path / "example.env", env_file)

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
            result = helper.capture("gp url 8000")
            domain = result.strip().removeprefix("https://")
            modify_env_file(domain, uses_https=True)
        else:
            # Inside some local environment
            modify_env_file()

        print("Successfully initialized .env file.")

    def randomize_env_secrets(self):
        """Randomize secrets in the .env file"""

        class RandomizeEnvSecretsArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.randomize_env_secrets.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args(namespace=RandomizeEnvSecretsArgs())

        helper = self._setup_helper(args)

        env_file = helper.project_path / ".env"
        if not env_file.is_file():
            sys.exit("Workspace not initialized (.env file does not exist).")

        set_key(env_file, "DJANGO_SECRET_KEY", helper.generate_django_secret_key())
        set_key(env_file, "POSTGRES_PASSWORD", helper.generate_secure_password())
        set_key(env_file, "ADMIN_USER_PASSWORD", helper.generate_secure_password())
        set_key(env_file, "ADMIN_AUTH_TOKEN", helper.generate_auth_token())

    def generate_django_secret_key(self):
        """Generate a Django secret key"""

        parser = argparse.ArgumentParser(description=self.generate_django_secret_key.__doc__)
        args = parser.parse_args()

        helper = self._setup_helper(args)
        print(helper.generate_django_secret_key())

    def generate_secure_password(self):
        """Generate a secure password"""

        class GenerateSecurePasswordArgs(argparse.Namespace):
            length: int

        parser = argparse.ArgumentParser(description=self.generate_secure_password.__doc__)
        parser.add_argument("--length", type=int, default=12, help="Length of the password")
        args = parser.parse_args(namespace=GenerateSecurePasswordArgs())

        helper = self._setup_helper(args)
        print(helper.generate_secure_password(args.length))

    def generate_auth_token(self):
        """Generate an authentication token"""

        class GenerateAuthTokenArgs(argparse.Namespace):
            length: int

        parser = argparse.ArgumentParser(description=self.generate_auth_token.__doc__)
        parser.add_argument("--length", type=int, default=20, help="Length of the token")
        args = parser.parse_args(namespace=GenerateAuthTokenArgs())

        helper = self._setup_helper(args)
        print(helper.generate_auth_token(args.length))

    def generate_certificate_files(self):
        """Generate self-signed certificate files"""

        parser = argparse.ArgumentParser(description=self.generate_certificate_files.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args()

        helper = self._setup_helper(args)

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
            sys.exit(f"A SSL certificate file {cert_path.absolute()} already exists.")

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

        parser = argparse.ArgumentParser(description=self.generate_certificate_chain.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args()

        helper = self._setup_helper(args)

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
                " unsigned certificate with 'poetry run scripts/generate_certificate_files.py'"
                " with included chain file. If you have a signed certificate from a CA, be sure to"
                " provide the correct SSL_SERVER_CERT_FILE setting in '.env'. Skipping."
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

    def show_outdated(self):
        """Show outdated dependencies"""

        parser = argparse.ArgumentParser(description=self.show_outdated.__doc__)
        args = parser.parse_args()

        helper = self._setup_helper(args)

        print("### Outdated Python dependencies ###")
        helper.execute("poetry show --outdated --top-level")

        print("### Outdated NPM dependencies ###")
        helper.execute("npm outdated")

    def try_github_actions(self):
        """Try Github Actions locally using Act"""

        class TryGithubActionsArgs(argparse.Namespace):
            simulate: bool

        parser = argparse.ArgumentParser(description=self.try_github_actions.__doc__)
        parser.add_argument("--simulate", action="store_true", help="Simulate the command")
        args = parser.parse_args()

        helper = self._setup_helper(args)

        act_path = helper.project_path / "bin" / "act"
        if not act_path.exists():
            print("Installing act...")
            helper.execute(
                "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
                hidden=True,
            )

        helper.execute(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest")

    def backup_db(self):
        """Backup database

        For backup location see setting DBBACKUP_STORAGE_OPTIONS
        For possible commands see:
        https://django-dbbackup.readthedocs.io/en/master/commands.html
        """

        parser = argparse.ArgumentParser(
            description=self.backup_db.__doc__, formatter_class=argparse.RawTextHelpFormatter
        )
        args = parser.parse_args()

        helper = self._setup_helper(args)

        settings = (
            f"{helper.project_name}.settings.production"
            if helper.is_production
            else f"{helper.project_name}.settings.development"
        )
        web_container_id = helper.find_running_container_id("web")
        if web_container_id is None:
            sys.exit("Web container is not running. Run 'poetry run scripts/compose_up.py' first.")

        helper.execute(
            (
                f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
                f"{web_container_id} ./manage.py dbbackup --clean -v 2"
            ),
        )

    def restore_db(self):
        """Restore database from previous backup"""

        parser = argparse.ArgumentParser(description=self.restore_db.__doc__)
        args = parser.parse_args()

        helper = self._setup_helper(args)

        settings = (
            f"{helper.project_name}.settings.production"
            if helper.is_production
            else f"{helper.project_name}.settings.development"
        )
        web_container_id = helper.find_running_container_id("web")
        if web_container_id is None:
            sys.exit("Web container is not running. Run 'poetry run scripts/compose_up.py' first.")

        helper.execute(
            (
                f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
                f"{web_container_id} ./manage.py dbrestore"
            ),
        )

    def upgrade_postgresql(self, version: str = "latest"):
        """Upgrade PostgreSQL volume data"""

        class UpgradePostgresqlArgs(argparse.Namespace):
            version: str

        parser = argparse.ArgumentParser(description=self.upgrade_postgresql.__doc__)
        parser.add_argument("version", nargs="?", default="latest", help="Version to upgrade to")
        args = parser.parse_args(namespace=UpgradePostgresqlArgs())

        helper = self._setup_helper(args)

        volume = f"{helper.stack_name}_postgres_data"
        print(f"Upgrading PostgreSQL database in volume {volume} environment to {version}.")
        print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
        if helper.confirm("Are you sure you want to proceed?"):
            print("Starting docker container that upgrades the database files.")
            print("Watch the output if everything went fine or if any further steps are necessary.")
            helper.execute(
                f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
                f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}",
            )
        else:
            print("Cancelled")
