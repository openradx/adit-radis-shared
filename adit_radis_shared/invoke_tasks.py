import os
import shutil
import sys
from pathlib import Path
from typing import Literal

from dotenv import set_key
from invoke.context import Context

Environments = Literal["dev", "prod"]


class InvokeTasks:
    def __init__(self, project_name: str, project_dir: Path):
        self._project_name = project_name
        self._project_dir = project_dir
        self._compose_dir = project_dir / "compose"

    def _get_compose_base_file(self):
        return self._compose_dir / "docker-compose.base.yml"

    def _get_compose_env_file(self, env: Environments):
        if env == "dev":
            return self._compose_dir / "docker-compose.dev.yml"
        elif env == "prod":
            return self._compose_dir / "docker-compose.prod.yml"
        else:
            raise ValueError(f"Unknown environment: {env}")

    def _get_stack_name(self, env: Environments):
        if env == "dev":
            return f"{self._project_name}_dev"
        elif env == "prod":
            return f"{self._project_name}_prod"
        else:
            raise ValueError(f"Unknown environment: {env}")

    def _build_compose_cmd(self, env: Environments, profile: str | None = None):
        cmd = "docker compose"
        cmd += f" -f {self._get_compose_base_file()}"
        cmd += f" -f {self._get_compose_env_file(env)}"
        cmd += f" -p {self._get_stack_name(env)}"
        if profile:
            cmd += f" --profile {profile}"
        return cmd

    def _check_compose_up(self, ctx: Context, env: Environments):
        stack_name = self._get_stack_name(env)
        result = ctx.run("docker compose ls", hide=True, warn=True)
        assert result and result.ok
        for line in result.stdout.splitlines():
            if line.startswith(stack_name) and line.find("running") != -1:
                return True
        return False

    def _find_running_container_id(self, ctx: Context, env: Environments, name: str):
        stack_name = self._get_stack_name(env)
        sep = "-" if env == "dev" else "_"
        cmd = f"docker ps -q -f name={stack_name}{sep}{name} -f status=running"
        cmd += " | head -n1"
        result = ctx.run(cmd, hide=True, warn=True)
        if result and result.ok:
            container_id = result.stdout.strip()
            if container_id:
                return container_id
        return None

    def _confirm(self, question: str) -> bool:
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

    def compose_up(
        self,
        ctx: Context,
        env: Environments = "dev",
        no_build: bool = False,
        profile: str | None = None,
    ):
        """Start containers in specified environment"""
        build_opt = "--no-build" if no_build else "--build"
        cmd = f"{self._build_compose_cmd(env, profile)} up {build_opt} --detach"
        ctx.run(cmd, pty=True)

    def compose_down(
        self,
        ctx: Context,
        env: Environments = "dev",
        profile: str | None = None,
        cleanup: bool = False,
    ):
        """Stop containers in specified environment"""
        cmd = f"{self._build_compose_cmd(env, profile)} --profile {profile} down"
        if cleanup:
            cmd += " --remove-orphans --volumes"
        ctx.run(cmd, pty=True)

    def stack_deploy2(self, ctx: Context, env: Environments = "prod", build: bool = False):
        if build:
            cmd = f"{self._build_compose_cmd(env)} build"
            ctx.run(cmd, pty=True)

        cmd = (
            f"docker stack deploy -c {self._get_compose_env_file(env)} {self._get_stack_name(env)}"
        )
        ctx.run(cmd, pty=True)

    def stack_deploy(self, ctx: Context, env: Environments = "prod", build: bool = False):
        """Deploy the stack to Docker Swarm (prod by default!). Optional build it before."""
        if build:
            cmd = f"{self._build_compose_cmd(env)} build"
            ctx.run(cmd, pty=True)

        cmd = "docker stack deploy --detach "
        cmd += f" -c {self._get_compose_base_file()}"
        cmd += f" -c {self._get_compose_env_file(env)}"
        cmd += f" {self._get_stack_name(env)}"
        ctx.run(cmd, pty=True)

    def stack_rm(self, ctx: Context, env: Environments = "prod"):
        cmd = f"docker stack rm {self._get_stack_name(env)}"
        ctx.run(cmd, pty=True)

    def web_shell(self, ctx: Context, env: Environments = "dev"):
        """Open Python shell in web container of specified environment"""
        cmd = f"{self._build_compose_cmd(env)} exec web python manage.py shell_plus"
        ctx.run(cmd, pty=True)

    def format(self, ctx: Context):
        """Format the source code with ruff and djlint"""
        # Format Python code
        format_code_cmd = "poetry run ruff format ."
        ctx.run(format_code_cmd, pty=True)
        # Sort Python imports
        sort_imports_cmd = "poetry run ruff check . --fix --select I"
        ctx.run(sort_imports_cmd, pty=True)
        # Format Django templates
        format_templates_cmd = "poetry run djlint . --reformat"
        ctx.run(format_templates_cmd, pty=True)

    def lint(self, ctx: Context):
        """Lint the source code (ruff, djlint, pyright)"""
        cmd_ruff = "poetry run ruff check ."
        ctx.run(cmd_ruff, pty=True)
        cmd_djlint = "poetry run djlint . --lint"
        ctx.run(cmd_djlint, pty=True)
        cmd_pyright = "poetry run pyright"
        ctx.run(cmd_pyright, pty=True)

    def test(
        self,
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
        if not self._check_compose_up(ctx, "dev"):
            sys.exit(
                "Integration tests need dev containers running.\nRun 'invoke compose-up' first."
            )

        cmd = (
            f"{self._build_compose_cmd('dev')} exec "
            f"--env DJANGO_SETTINGS_MODULE={self._project_name}.settings.test web pytest "
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

    def reset_dev(self, ctx: Context):
        """Reset the dev environment"""
        # Wipe the database
        flush_cmd = f"{self._build_compose_cmd('dev')} exec web python manage.py flush --noinput"
        ctx.run(flush_cmd, pty=True)
        # Re-populate the database with users and groups
        populate_cmd = (
            f"{self._build_compose_cmd('dev')} exec web python manage.py "
            "populate_users_and_groups"
        )
        populate_cmd += " --users 20 --groups 3"
        ctx.run(populate_cmd, pty=True)

    def init_workspace(self, ctx: Context):
        """Initialize workspace for Github Codespaces or Gitpod"""
        env_dev_file = f"{self._project_dir}/.env.dev"
        if os.path.isfile(env_dev_file):
            print("Workspace already initialized (.env.dev file exists).")
            return

        shutil.copy(f"{self._project_dir}/example.env", env_dev_file)

        def modify_env_file(domain: str | None = None):
            if domain:
                url = f"https://{domain}"
                hosts = f".localhost,127.0.0.1,[::1],{domain}"
                set_key(env_dev_file, "DJANGO_CSRF_TRUSTED_ORIGINS", url, quote_mode="never")
                set_key(env_dev_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
                set_key(env_dev_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
                set_key(env_dev_file, "SITE_BASE_URL", url, quote_mode="never")
                set_key(env_dev_file, "SITE_DOMAIN", domain, quote_mode="never")

            set_key(env_dev_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

        if os.environ.get("CODESPACE_NAME"):
            # Inside GitHub Codespaces
            domain = f"{os.environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
            modify_env_file(domain)
        elif os.environ.get("GITPOD_WORKSPACE_ID"):
            # Inside Gitpod
            result = ctx.run("gp url 8000", hide=True, pty=True)
            assert result and result.ok
            domain = result.stdout.strip().removeprefix("https://")
            modify_env_file(domain)
        else:
            # Inside some local environment
            modify_env_file()

    def show_outdated(self, ctx: Context):
        """Show outdated dependencies"""
        print("### Outdated Python dependencies ###")
        poetry_cmd = "poetry show --outdated --top-level"
        result = ctx.run(poetry_cmd, pty=True)
        assert result and result.ok
        print(result.stderr.strip())

        print("### Outdated NPM dependencies ###")
        npm_cmd = "npm outdated"
        ctx.run(npm_cmd, pty=True)

    def try_github_actions(self, ctx: Context):
        """Try Github Actions locally using Act"""
        act_path = self._project_dir / "bin" / "act"
        if not act_path.exists():
            print("Installing act...")
            ctx.run(
                "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
                hide=True,
                pty=True,
            )
        ctx.run(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest", pty=True)

    def backup_db(self, ctx: Context, env: Environments = "prod"):
        """Backup database

        For backup location see setting DBBACKUP_STORAGE_OPTIONS
        For possible commands see:
        https://django-dbbackup.readthedocs.io/en/master/commands.html
        """
        settings = (
            f"{self._project_name}.settings.production"
            if env == "prod"
            else f"{self._project_name}.settings.development"
        )
        web_container_id = self._find_running_container_id(ctx, env, "web")
        cmd = (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        )
        ctx.run(cmd, pty=True)

    def restore_db(self, ctx: Context, env: Environments = "prod"):
        """Restore database from backup"""
        settings = (
            f"{self._project_name}.settings.production"
            if env == "prod"
            else f"{self._project_name}.settings.development"
        )
        web_container_id = self._find_running_container_id(ctx, env, "web")
        cmd = (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        )
        ctx.run(cmd, pty=True)

    def bump_version(self, ctx: Context, rule: Literal["patch", "minor", "major"]):
        """Bump version, create a tag, commit and push to GitHub"""
        result = ctx.run("git status --porcelain", hide=True, pty=True)
        assert result and result.ok
        if result.stdout.strip():
            print("There are uncommitted changes. Aborting.")
            sys.exit(1)

        ctx.run(f"poetry version {rule}", pty=True)
        ctx.run("git add pyproject.toml", pty=True)
        ctx.run("git commit -m 'Bump version'", pty=True)
        ctx.run('git tag -a v$(poetry version -s) -m "Release v$(poetry version -s)"', pty=True)
        ctx.run("git push --follow-tags", pty=True)

    def upgrade_postgresql(self, ctx: Context, env: Environments, version: str = "latest"):
        print(f"Upgrading PostgreSQL database in {env} environment to {version}.")
        print("Cave, make sure the whole stack is not stopped. Otherwise this will corrupt data!")
        if self._confirm("Are you sure you want to proceed?"):
            print("Starting docker container that upgrades the database files.")
            print("Watch the output if everything went fine or if any further steps are necessary.")
            volume = f"{self._get_stack_name(env)}_postgres_data"
            ctx.run(
                f"docker run -e POSTGRES_PASSWORD=postgres -v {volume}:/var/lib/postgresql/data "
                f"pgautoupgrade/pgautoupgrade:{version}",
                pty=True,
            )
        else:
            print("Cancelled")
