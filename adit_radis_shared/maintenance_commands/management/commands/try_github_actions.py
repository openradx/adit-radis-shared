from typing import Annotated

from typer import Option

from ..base.maintenance_command import MaintenanceCommand


class Command(MaintenanceCommand):
    """Try Github Actions locally using Act"""

    def handle(
        self,
        simulate: Annotated[bool, Option(help="Simulate the command")] = False,
    ):
        act_path = self.project_path / "bin" / "act"
        if not act_path.exists():
            print("Installing act...")
            self.execute_cmd(
                "curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash",
                hidden=True,
            )

        self.execute_cmd(
            f"{act_path} -P ubuntu-latest=catthehacker/ubuntu:act-latest", simulate=simulate
        )
