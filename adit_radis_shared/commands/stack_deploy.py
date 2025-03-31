import argparse
import sys

import argcomplete

from .helper import CommandHelper


class Namespace(argparse.Namespace):
    build: bool


def call():
    """Deploy stack with docker swarm"""
    parser = argparse.ArgumentParser(description="Deploy stack with docker swarm")
    parser.add_argument("--build", action="store_true", help="Build images")
    argcomplete.autocomplete(parser)
    args = parser.parse_args(namespace=Namespace())

    helper = CommandHelper()
    helper.prepare_environment()

    if not helper.is_production():
        sys.exit(
            "stack-deploy task can only be used in production environment. "
            "Check ENVIRONMENT setting in .env file."
        )

    if args.build:
        cmd = f"{helper.build_compose_cmd()} build"
        cmd += f" --build-arg PROJECT_VERSION={helper.get_project_version()}-local"
        helper.execute_cmd(cmd)

    # Docker Swarm Mode does not support .env files so we load the .env file manually
    # and pass the content as an environment variables.
    env = helper.load_config_from_env_file()

    cmd = "docker stack deploy --detach "
    cmd += f" -c {helper.get_compose_base_file()}"
    cmd += f" -c {helper.get_compose_env_file()}"
    cmd += f" {helper.get_stack_name()}"
    helper.execute_cmd(cmd, env=env)
