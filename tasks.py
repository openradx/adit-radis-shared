import os
import shutil
import sys
from os import environ
from pathlib import Path
from typing import Literal

from dotenv import set_key
from invoke.context import Context
from invoke.tasks import task

project_dir = Path(__file__).resolve().parent

manage_cmd = (project_dir / "example_project" / "manage.py").as_posix()


@task
def compose_up(
    ctx: Context,
    no_build: bool = False,
):
    """Start example project containers"""
    build_opt = "--no-build" if no_build else "--build"
    cmd = f"docker compose up {build_opt} --detach"
    ctx.run(cmd, pty=True)


@task
def compose_down(
    ctx: Context,
    cleanup: bool = False,
):
    """Stop example project containers"""
    cmd = "docker compose down"
    if cleanup:
        cmd += " --remove-orphans --volumes"
    ctx.run(cmd, pty=True)


@task
def startdev(ctx: Context):
    migrate(ctx)
    populate_db(ctx)
    runserver(ctx)


@task
def runserver(ctx: Context):
    """Run the development server of the example project"""
    ctx.run(f"{manage_cmd} runserver", pty=True)


@task
def makemigrations(ctx: Context):
    """Make Django migrations"""
    ctx.run(f"{manage_cmd} makemigrations", pty=True)


@task
def migrate(ctx: Context):
    """Apply Django migrations"""
    ctx.run(f"{manage_cmd} migrate", pty=True)


@task
def reset_db(ctx: Context):
    """Reset the database

    Can only be done when dev server is not running and needs django_extensions installed.
    """
    ctx.run(f"{manage_cmd} reset_db --no-input", pty=True)
    ctx.run(f"{manage_cmd} migrate", pty=True)


@task
def populate_db(ctx: Context):
    """Populate database with users and groups"""
    cmd = f"{manage_cmd} populate_users_and_groups"
    cmd += " --users 30"
    cmd += " --groups 5"
    ctx.run(cmd, pty=True)


@task
def format(ctx: Context):
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


@task
def lint(ctx: Context):
    """Lint the source code (ruff, djlint, pyright)"""
    cmd_ruff = "poetry run ruff check ."
    ctx.run(cmd_ruff, pty=True)
    cmd_djlint = "poetry run djlint . --lint"
    ctx.run(cmd_djlint, pty=True)
    cmd_pyright = "poetry run pyright"
    ctx.run(cmd_pyright, pty=True)


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
    cmd = "pytest "
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
def ci(ctx: Context):
    """Run the continuous integration (linting and tests)"""
    lint(ctx)
    test(ctx, cov=True)


@task
def copy_statics(ctx: Context):
    """Copy JS and CSS dependencies from node_modules to static vendor folder"""
    print("Copying statics...")

    target_folder = project_dir / "adit_radis_shared" / "common" / "static" / "vendor"

    def copy_file(file: str, filename: str | None = None):
        if not filename:
            shutil.copy(file, target_folder)
        else:
            target_file = os.path.join(target_folder, filename)
            shutil.copy(file, target_file)

    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js")
    copy_file("node_modules/bootstrap/dist/js/bootstrap.bundle.js.map")
    copy_file("node_modules/bootswatch/dist/flatly/bootstrap.css")
    copy_file("node_modules/bootstrap-icons/bootstrap-icons.svg")
    copy_file("node_modules/alpinejs/dist/cdn.js", "alpine.js")
    copy_file("node_modules/@alpinejs/morph/dist/cdn.js", "alpine-morph.js")
    copy_file("node_modules/htmx.org/dist/htmx.js")
    copy_file("node_modules/htmx.org/dist/ext/ws.js", "htmx-ws.js")
    copy_file("node_modules/htmx.org/dist/ext/alpine-morph.js", "htmx-alpine-morph.js")


@task
def init_workspace(ctx: Context):
    """Initialize workspace for Github Codespaces or Gitpod"""
    env_dev_file = f"{project_dir}/.env"
    if os.path.isfile(env_dev_file):
        print("Workspace already initialized (.env.dev file exists).")
        return

    shutil.copy(f"{project_dir}/example.env", env_dev_file)

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

    if environ.get("CODESPACE_NAME"):
        # Inside GitHub Codespaces
        domain = f"{environ['CODESPACE_NAME']}-8000.preview.app.github.dev"
        modify_env_file(domain)
    elif environ.get("GITPOD_WORKSPACE_ID"):
        # Inside Gitpod
        result = ctx.run("gp url 8000", pty=True, hide=True)
        assert result and result.ok
        domain = result.stdout.strip().removeprefix("https://")
        modify_env_file(domain)
    else:
        # Inside some local environment
        modify_env_file()


@task
def show_outdated(ctx: Context):
    """Show outdated dependencies"""
    print("### Outdated Python dependencies ###")
    poetry_cmd = "poetry show --outdated --top-level"
    result = ctx.run(poetry_cmd, pty=True)
    assert result
    print(result.stderr.strip())

    print("### Outdated NPM dependencies ###")
    npm_cmd = "npm outdated"
    ctx.run(npm_cmd, pty=True)


@task
def upgrade(ctx: Context):
    """Upgrade Python and JS packages"""
    ctx.run("poetry update", pty=True)
    ctx.run("npm update", pty=True)
    copy_statics(ctx)


@task
def try_github_actions(ctx: Context):
    """Try Github Actions locally using Act"""
    act_path = project_dir / "bin" / "act"
    if not act_path.exists():
        print("Installing act...")
        ctx.run(
            "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
            pty=True,
            hide=True,
        )
    ctx.run(f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest", pty=True)


@task
def bump_version(ctx: Context, rule: Literal["patch", "minor", "major"]):
    """Bump version, create a tag, commit and push to GitHub"""
    result = ctx.run("git status --porcelain", pty=True, hide=True)
    assert result
    if result.stdout.strip():
        print("There are uncommitted changes. Aborting.")
        sys.exit(1)

    ctx.run(f"poetry version {rule}", pty=True)
    ctx.run("git add pyproject.toml", pty=True)
    ctx.run("git commit -m 'Bump version'", pty=True)
    ctx.run('git tag -a v$(poetry version -s) -m "Release v$(poetry version -s)"', pty=True)
    ctx.run("git push --follow-tags", pty=True)
