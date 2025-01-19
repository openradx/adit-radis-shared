from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


class CommonConfig(AppConfig):
    name = "adit_radis_shared.common"

    def ready(self):
        # Put calls to db stuff in this signal handler
        post_migrate.connect(init_db, sender=self)


def init_db(**kwargs):
    from django.contrib.sites.models import Site

    from .models import ProjectSettings

    Site.objects.update_or_create(
        pk=settings.SITE_ID,
        defaults={
            "domain": settings.SITE_DOMAIN,
            "name": settings.SITE_NAME,
        },
    )

    if not ProjectSettings.objects.exists():
        ProjectSettings.objects.create()
