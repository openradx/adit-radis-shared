from adit_radis_shared.common.management.base.procrastinate_worker import ProcrastinateServerCommand


class Command(ProcrastinateServerCommand):
    paths_to_watch = [
        "./example_project",
        "../adit_radis_shared",
    ]
