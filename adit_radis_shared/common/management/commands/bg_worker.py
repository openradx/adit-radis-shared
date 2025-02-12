from django.conf import settings

from adit_radis_shared.common.management.base.procrastinate_worker import ProcrastinateServerCommand


class Command(ProcrastinateServerCommand):
    paths_to_watch = settings.SOURCE_PATHS
