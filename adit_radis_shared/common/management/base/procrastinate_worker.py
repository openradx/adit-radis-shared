import logging
import shlex
import subprocess

from .server_command import ServerCommand

logger = logging.getLogger(__name__)


class ProcrastinateServerCommand(ServerCommand):
    help = "Starts a Procrastinate worker"
    server_name = "Procrastinate worker"
    worker_process: subprocess.Popen | None

    def __init__(self, *args, **kwargs):
        self.worker_process = None
        super().__init__(*args, **kwargs)

    def add_arguments(self, parser):
        super().add_arguments(parser)

        parser.add_argument(
            "-q",
            "--queues",
            help="Comma-separated names of the queues to listen to (empty string for all queues)",
        )
        parser.add_argument(
            "-l",
            "--loglevel",
            default="warning",
            choices=["warning", "info", "debug"],
            help="Logging level.",
        )
        parser.add_argument(
            "-c",
            "--concurrency",
            type=int,
            default=1,
            help="Number of child processes processing the queue (defaults to number of CPUs).",
        )

    def run_server(self, **options):
        cmd = "./manage.py procrastinate"

        # https://procrastinate.readthedocs.io/en/stable/howto/basics/command_line.html
        if options["loglevel"] == "debug":
            cmd += " -v 1"

        cmd += " worker --delete-jobs=always"

        concurrency = options["concurrency"]
        if concurrency > 1:
            cmd += f" --concurrency {concurrency}"

        self.worker_process = subprocess.Popen(shlex.split(cmd))
        self.worker_process.wait()

    def on_shutdown(self):
        assert self.worker_process
        self.worker_process.terminate()
        self.worker_process.wait()
