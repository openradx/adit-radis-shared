from pathlib import Path

from adit_radis_shared import invoke_tasks
from adit_radis_shared.invoke_tasks import (  # noqa: F401
    compose_down,
    compose_up,
    format,
    init_workspace,
    lint,
    show_outdated,
    stack_deploy,
    stack_rm,
    test,
    try_github_actions,
)

invoke_tasks.PROJECT_NAME = "example_project"
invoke_tasks.PROJECT_DIR = Path(__file__).resolve().parent
