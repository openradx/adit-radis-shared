import argparse
from typing import Callable

from . import commands


def register_compose_up(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Start stack with docker compose"
    parser = subparsers.add_parser("compose-up", help=info, description=info)
    parser.add_argument("--build", action="store_true", help="Build images before starting")
    parser.add_argument("--profile", action="append", help="Docker compose profile(s) to use")
    parser.set_defaults(func=func or commands.compose_up)


def register_compose_down(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Stop stack with docker compose"
    parser = subparsers.add_parser("compose-down", help=info, description=info)
    parser.add_argument("--cleanup", action="store_true", help="Remove orphans and volumes")
    parser.add_argument("--profile", action="append", help="Docker compose profile(s) to use")
    parser.set_defaults(func=func or commands.compose_down)


def register_db_backup(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Backup database in running container stack"
    parser = subparsers.add_parser(
        "db-backup",
        help=info,
        description=info,
        epilog="For backup location see DBBACKUP_STORAGE_OPTIONS setting",
    )
    parser.set_defaults(func=func or commands.db_backup)


def register_db_restore(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Restore database in container from the last backup"
    parser = subparsers.add_parser("db-restore", help=info, description=info)
    parser.set_defaults(func=func or commands.db_restore)


def register_format_code(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    parser = subparsers.add_parser(
        "format-code",
        help="Format the source code with ruff and djlint",
    )
    parser.set_defaults(func=func or commands.format_code)


def register_generate_auth_token(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Generate an authentication token"
    parser = subparsers.add_parser("generate-auth-token", help=info, description=info)
    parser.add_argument("--length", type=int, default=20, help="Length of the token (default: 20)")
    parser.set_defaults(func=func or commands.generate_auth_token)


def register_generate_certificate_chain(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Generate certificate chain file for a signed certificate"
    parser = subparsers.add_parser("generate-certificate-chain", help=info, description=info)
    parser.set_defaults(func=func or commands.generate_certificate_chain)


def register_generate_certificate_files(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Generate self-signed certificate files for local development"
    parser = subparsers.add_parser("generate-certificate-files", help=info, description=info)
    parser.set_defaults(func=func or commands.generate_certificate_files)


def register_generate_django_secret_key(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Generate a Django secret key"
    parser = subparsers.add_parser("generate-django-secret-key", help=info, description=info)
    parser.set_defaults(func=func or commands.generate_django_secret_key)


def register_generate_secure_password(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Generate a secure password"
    parser = subparsers.add_parser("generate-secure-password", help=info, description=info)
    parser.add_argument(
        "--length", type=int, default=12, help="Length of the password (default: 12)"
    )
    parser.set_defaults(func=func or commands.generate_secure_password)


def register_init_workspace(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Initialize workspace for Github Codespaces or local development"
    parser = subparsers.add_parser("init-workspace", help=info, description=info)
    parser.set_defaults(func=func or commands.init_workspace)


def register_lint(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Lint the source code with ruff, pyright and djlint"
    parser = subparsers.add_parser("lint", help=info, description=info)
    parser.set_defaults(func=func or commands.lint)


def register_randomize_env_secrets(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Randomize secrets in the .env file"
    parser = subparsers.add_parser("randomize-env-secrets", help=info, description=info)
    parser.set_defaults(func=func or commands.randomize_env_secrets)


def register_shell(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Open a Python shell in the specified container"
    parser = subparsers.add_parser("shell", help=info, description=info)
    parser.add_argument(
        "--container", type=str, default="web", help="Container name (default: web)"
    )
    parser.set_defaults(func=func or commands.shell)


def register_show_outdated(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Show outdated dependencies"
    parser = subparsers.add_parser("show-outdated", help=info, description=info)
    parser.set_defaults(func=func or commands.show_outdated)


def register_stack_deploy(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Deploy stack with docker swarm"
    parser = subparsers.add_parser("stack-deploy", help=info, description=info)
    parser.add_argument("--build", action="store_true", help="Build images")
    parser.set_defaults(func=func or commands.stack_deploy)


def register_stack_rm(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Remove stack from docker swarm"
    parser = subparsers.add_parser("stack-rm", help=info, description=info)
    parser.set_defaults(func=func or commands.stack_rm)


def register_test(subparsers: argparse._SubParsersAction, func: Callable | None = None):
    info = "Run the test suite with pytest"
    parser = subparsers.add_parser("test", help=info, description=info)
    parser.set_defaults(func=func or commands.test)


def register_try_github_actions(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Try Github Actions locally using Act"
    parser = subparsers.add_parser("try-github-actions", help=info, description=info)
    parser.set_defaults(func=func or commands.try_github_actions)


def register_upgrade_postgres_volume(
    subparsers: argparse._SubParsersAction, func: Callable | None = None
):
    info = "Upgrade PostgreSQL volume data"
    parser = subparsers.add_parser("upgrade-postgres-volume", help=info, description=info)
    parser.add_argument(
        "--version",
        type=str,
        default="latest",
        help="PostgreSQL version to upgrade to (default: latest)",
    )
    parser.set_defaults(func=func or commands.upgrade_postgres_volume)
