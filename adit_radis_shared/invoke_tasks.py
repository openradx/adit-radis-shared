import os
import re
import shutil
import sys
from pathlib import Path
from typing import Literal

import requests
from dotenv import set_key
from invoke.context import Context
from invoke.tasks import task

Environments = Literal["dev", "prod"]

###
# Global config
###


PROJECT_NAME: str | None = None
PROJECT_DIR: Path | None = None


###
# Helper functions
###


def get_project_name():
    assert PROJECT_NAME is not None
    return PROJECT_NAME


def get_project_dir():
    assert PROJECT_DIR is not None
    return PROJECT_DIR


def get_compose_dir():
    return get_project_dir() / "compose"


def get_compose_base_file():
    return get_compose_dir() / "docker-compose.base.yml"


def get_compose_env_file(env: Environments):
    if env == "dev":
        return get_compose_dir() / "docker-compose.dev.yml"
    elif env == "prod":
        return get_compose_dir() / "docker-compose.prod.yml"
    else:
        raise ValueError(f"Unknown environment: {env}")


def get_stack_name(env: Environments):
    if env == "dev":
        return f"{get_project_name()}_dev"
    elif env == "prod":
        return f"{get_project_name()}_prod"
    else:
        raise ValueError(f"Unknown environment: {env}")


def build_compose_cmd(env: Environments, profiles: list[str] = []):
    cmd = "docker compose"
    cmd += f" -f {get_compose_base_file()}"
    cmd += f" -f {get_compose_env_file(env)}"
    cmd += f" -p {get_stack_name(env)}"
    for profile in profiles:
        cmd += f" --profile {profile}"
    return cmd


def check_compose_up(ctx: Context, env: Environments):
    stack_name = get_stack_name(env)
    result = ctx.run("docker compose ls", hide=True, warn=True)
    assert result and result.ok
    for line in result.stdout.splitlines():
        if line.startswith(stack_name) and line.find("running") != -1:
            return True
    return False


def find_running_container_id(ctx: Context, env: Environments, name: str):
    stack_name = get_stack_name(env)
    sep = "-" if env == "dev" else "_"
    cmd = f"docker ps -q -f name={stack_name}{sep}{name} -f status=running"
    cmd += " | head -n1"
    result = ctx.run(cmd, hide=True, warn=True)
    if result and result.ok:
        container_id = result.stdout.strip()
        if container_id:
            return container_id
    return None


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
    else:
        return None


def get_latest_local_version_tag(ctx: Context) -> str:
    # Get all tags sorted by creation date (newest first)
    result = ctx.run("git tag -l --sort=-creatordate", hide=True)
    assert result and result.ok
    all_tags = result.stdout.splitlines()

    version_pattern = re.compile(r"^\d+\.\d+\.\d+$")
    for tag in all_tags:
        if version_pattern.match(tag):
            return tag

    return "0.0.0"


###
# Tasks
###


@task(iterable=["profile"])
def compose_up(ctx: Context, env: Environments = "dev", no_build=False, profile: list[str] = []):
    """Start containers in specified environment"""
    version = get_latest_local_version_tag(ctx)
    if env == "dev":
        version += "-dev"

    build_opt = "--no-build" if no_build else "--build"
    ctx.run(
        f"PROJECT_VERSION={version} {build_compose_cmd(env, profile)} up {build_opt} --detach",
        pty=True,
    )


@task(iterable=["profile"])
def compose_down(
    ctx: Context, env: Environments = "dev", cleanup: bool = False, profile: list[str] = []
):
    """Stop containers in specified environment"""
    cmd = f"{build_compose_cmd(env, profile)} down"
    if cleanup:
        cmd += " --remove-orphans --volumes"
    ctx.run(cmd, pty=True)


@task
def stack_deploy(ctx: Context, env: Environments = "prod", build: bool = False):
    """Deploy the stack to Docker Swarm (prod by default!). Optional build it before."""
    if build:
        cmd = f"{build_compose_cmd(env)} build"
        ctx.run(cmd, pty=True)

    version = get_latest_local_version_tag(ctx)
    if env == "dev":
        version += "-dev"

    cmd = f"PROJECT_VERSION={version} docker stack deploy --detach "
    cmd += f" -c {get_compose_base_file()}"
    cmd += f" -c {get_compose_env_file(env)}"
    cmd += f" {get_stack_name(env)}"
    ctx.run(cmd, pty=True)


@task
def stack_rm(ctx: Context, env: Environments = "prod"):
    """Remove the Docker Swarm stack"""
    ctx.run(f"docker stack rm {get_stack_name(env)}", pty=True)


@task
def web_shell(ctx: Context, env: Environments = "dev"):
    """Open Python shell in web container of specified environment"""
    ctx.run(f"{build_compose_cmd(env)} exec web python manage.py shell_plus", pty=True)


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
    if not check_compose_up(ctx, "dev"):
        sys.exit("Integration tests need dev containers running.\nRun 'invoke compose-up' first.")

    cmd = (
        f"{build_compose_cmd('dev')} exec "
        f"--env DJANGO_SETTINGS_MODULE={get_project_name()}.settings.test web pytest "
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
def reset_dev(ctx: Context):
    """Reset the dev environment"""
    # Wipe the database
    ctx.run(f"{build_compose_cmd('dev')} exec web python manage.py flush --noinput", pty=True)
    # Re-populate the database with users and groups
    ctx.run(
        f"{build_compose_cmd('dev')} exec web python manage.py populate_users_and_groups "
        "--users 20 --groups 3",
        pty=True,
    )


@task
def init_workspace(ctx: Context):
    """Initialize workspace for Github Codespaces or Gitpod"""
    env_dev_file = f"{get_project_dir()}/.env.dev"
    if os.path.isfile(env_dev_file):
        print("Workspace already initialized (.env.dev file exists).")
        return

    shutil.copy(f"{get_project_dir()}/example.env", env_dev_file)

    def modify_env_file(domain: str | None = None, uses_https: bool = False):
        if domain:
            url = f"https://{domain}"
            hosts = f".localhost,127.0.0.1,[::1],{domain}"
            set_key(env_dev_file, "DJANGO_CSRF_TRUSTED_ORIGINS", url, quote_mode="never")
            set_key(env_dev_file, "DJANGO_ALLOWED_HOSTS", hosts, quote_mode="never")
            set_key(env_dev_file, "DJANGO_INTERNAL_IPS", hosts, quote_mode="never")
            set_key(env_dev_file, "SITE_DOMAIN", domain, quote_mode="never")

        if uses_https:
            set_key(env_dev_file, "SITE_USES_HTTPS", "true", quote_mode="never")

        set_key(env_dev_file, "FORCE_DEBUG_TOOLBAR", "true", quote_mode="never")

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
    act_path = get_project_dir() / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        ctx.run(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            hide=True,
            pty=True,
        )
    ctx.run(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest", pty=True)


@task
def backup_db(ctx: Context, env: Environments = "prod"):
    """Backup database

    For backup location see setting DBBACKUP_STORAGE_OPTIONS
    For possible commands see:
    https://django-dbbackup.readthedocs.io/en/master/commands.html
    """
    settings = (
        f"{get_project_name()}.settings.production"
        if env == "prod"
        else f"{get_project_name()}.settings.development"
    )
    web_container_id = find_running_container_id(ctx, env, "web")
    ctx.run(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbbackup --clean -v 2"
        ),
        pty=True,
    )


@task
def restore_db(ctx: Context, env: Environments = "prod"):
    """Restore database from previous backup"""
    settings = (
        f"{get_project_name()}.settings.production"
        if env == "prod"
        else f"{get_project_name()}.settings.development"
    )
    web_container_id = find_running_container_id(ctx, env, "web")
    ctx.run(
        (
            f"docker exec --env DJANGO_SETTINGS_MODULE={settings} "
            f"{web_container_id} ./manage.py dbrestore"
        ),
        pty=True,
    )


@task
def upgrade_adit_radis_shared(ctx: Context, version: str | None = None):
    """Upgrade adit-radis-shared package"""
    if version is None:
        version = get_latest_remote_version_tag("openradx", "adit-radis-shared")
    ctx.run(f"poetry add git+https://github.com/openradx/adit-radis-shared.git@{version}", pty=True)


@task
def upgrade_postgresql(ctx: Context, env: Environments, version: str = "latest"):
    print(f"Upgrading PostgreSQL database in {env} environment to {version}.")
    print("Cave, make sure the whole stack is stopped. Otherwise this will corrupt data!")
    if confirm("Are you sure you want to proceed?"):
        print("Starting docker container that upgrades the database files.")
        print("Watch the output if everything went fine or if any further steps are necessary.")
        volume = f"{get_stack_name(env)}_postgres_data"
        ctx.run(
            f"docker run -e POSTGRES_PASSWORD=postgres -e PGAUTO_ONESHOT=yes "
            f"-v {volume}:/var/lib/postgresql/data pgautoupgrade/pgautoupgrade:{version}",
            pty=True,
        )
    else:
        print("Cancelled")
