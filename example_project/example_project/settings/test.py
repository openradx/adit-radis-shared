from .base import *  # noqa: F403

DEBUG = False

# We must force the background worker that is started in a acceptance test
# as a subprocess to use the test database.
if not DATABASES["default"]["NAME"].startswith("test_"):  # noqa: F405
    test_database = "test_" + DATABASES["default"]["NAME"]  # noqa: F405
    DATABASES["default"]["NAME"] = test_database  # noqa: F405
    DATABASES["default"]["TEST"] = {"NAME": test_database}  # noqa: F405

DEBUG_TOOLBAR_CONFIG = {"SHOW_TOOLBAR_CALLBACK": lambda request: False}

# No real backups as a side effect of the periodic task framework tests
# (backup_db itself is tested with the dbbackup command mocked out).
BACKUP_ENABLED = False
