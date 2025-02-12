from typing import Annotated

from django_typer.management import command
from typer import Context, Exit, Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Start stack with docker compose"""

    @command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
    def handle(
        self,
        ctx: Context,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        if not self.check_compose_up():
            print(
                "Acceptance tests need dev containers running.\n"
                "Run 'poetry run ./manage.py compose_up' first."
            )
            raise Exit(1)

        cmd = (
            f"{self.build_compose_cmd()} exec "
            f"--env DJANGO_SETTINGS_MODULE={self.project_name}.settings.test web pytest "
        )
        cmd += " ".join(ctx.args)
        self.execute_cmd(cmd, simulate=simulate)
