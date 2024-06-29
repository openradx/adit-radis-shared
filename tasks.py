import os
import shutil
from pathlib import Path
from typing import Literal

from invoke.context import Context
from invoke.tasks import task

from adit_radis_shared.invoke_tasks import Environments, InvokeTasks

project_dir = Path(__file__).resolve().parent
invoke_helper = InvokeTasks("example_project", project_dir)


@task
def compose_up(ctx: Context, no_build=False, profile: str | None = None):
    """Start example project containers"""
    invoke_helper.compose_up(ctx, "dev", no_build=no_build, profile=profile)


@task
def compose_down(
    ctx: Context,
    cleanup: bool = False,
):
    """Stop example project containers"""
    invoke_helper.compose_down(ctx, "dev", cleanup=cleanup)


@task
def stack_deploy(ctx: Context, env: Environments = "prod", build: bool = False):
    """Deploy the stack"""
    invoke_helper.stack_deploy(ctx, env=env, build=build)


@task
def stack_rm(ctx: Context, env: Environments = "prod"):
    """Remove the stack"""
    invoke_helper.stack_rm(ctx, env=env)


@task
def format(ctx: Context):
    """Format the source code with ruff and djlint"""
    invoke_helper.format(ctx)


@task
def lint(ctx: Context):
    """Lint the source code (ruff, djlint, pyright)"""
    invoke_helper.lint(ctx)


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
    invoke_helper.test(
        ctx,
        path=path,
        cov=cov,
        html=html,
        keyword=keyword,
        mark=mark,
        stdout=stdout,
        failfast=failfast,
    )


@task
def init_workspace(ctx: Context):
    """Initialize workspace for Github Codespaces or Gitpod"""
    invoke_helper.init_workspace(ctx)


@task
def show_outdated(ctx: Context):
    """Show outdated dependencies"""
    invoke_helper.show_outdated(ctx)


@task
def try_github_actions(ctx: Context):
    """Try Github Actions locally using Act"""
    invoke_helper.try_github_actions(ctx)


@task
def bump_version(ctx: Context, rule: Literal["patch", "minor", "major"]):
    """Bump version, create a tag, commit and push to GitHub"""
    invoke_helper.bump_version(ctx, rule)


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
