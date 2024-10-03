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

    from .models import ProjectSettings, SiteProfile

    site_id = settings.SITE_ID
    site_profile_exists = SiteProfile.objects.filter(site_id=site_id).exists()

    if not site_profile_exists:
        Site.objects.update_or_create(
            pk=site_id,
            defaults={
                "domain": settings.SITE_DOMAIN,
                "name": settings.SITE_NAME,
            },
        )

        SiteProfile.objects.create(
            site_id=site_id,
            uses_https=settings.SITE_USES_HTTPS,
            meta_keywords=settings.SITE_META_KEYWORDS,
            meta_description=settings.SITE_META_DESCRIPTION,
            project_url=settings.SITE_PROJECT_URL,
        )

    if not ProjectSettings.objects.exists():
        ProjectSettings.objects.create()
