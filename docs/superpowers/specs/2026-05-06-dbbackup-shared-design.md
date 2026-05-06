# Move `backup_db` periodic task into adit-radis-shared and migrate to django-dbbackup 5.3+ settings format

**Date:** 2026-05-06
**Status:** Draft — pending user review

## Background

The 3am `backup_db` periodic task is currently duplicated in `adit/core/tasks.py` and `radis/core/tasks.py`, with both copies calling `dbbackup --clean -v 2` against legacy `DBBACKUP_STORAGE` / `DBBACKUP_STORAGE_OPTIONS` settings.

`django-dbbackup` 5.3.0 (released 2026-04-10) deprecated those settings: importing `dbbackup.settings` now raises `RuntimeError` when they are present. Renovate picked up the bump in adit/radis lockfiles (the projects only constrain `>=4.2.1`), so the periodic task crashes at 3am every night.

PR [openradx/adit#329](https://github.com/openradx/adit/pull/329) proposes a fix scoped to adit only: bump `django-dbbackup>=5.3.0` and migrate the settings to the new `STORAGES["dbbackup"]` format. Its approach is correct, but it leaves the duplicated task in place and does not address radis.

## Goal

Eliminate the duplicate `backup_db` task and unblock the nightly backup in both adit and radis by:

1. Moving `backup_db` into `adit_radis_shared.common.tasks` (alongside the existing shared periodic tasks `retry_stalled_jobs` and `broadcast_mail`).
2. Migrating settings in all three projects (adit, radis, example_project) to the new django-dbbackup 5.3+ `STORAGES` format.
3. Bumping `django-dbbackup>=5.3.0` in shared, adit, and radis.

PR #329 is superseded by this work and will be closed.

## Non-goals

- No abstraction over the per-project `STORAGES` dict beyond what already exists. Each consumer continues to write the dict in its own `settings/base.py` with its own backup location default.
- No automated regression test for the legacy-settings trap. The new dbbackup raises at import time, so the failure surfaces immediately on app startup if anyone reintroduces the legacy keys.
- No change to `dbbackup --clean -v 2` flags. Hardcoded in shared; matches existing behavior in both projects.
- ~~No opt-in/opt-out gating for the shared task.~~ **Revised during PR review:** added a `DBBACKUP_ENABLED` setting (default `True`) that gates the task body. The default preserves current behavior for adit/radis/example; consumers (or test/CI environments) can no-op the periodic task by setting `DBBACKUP_ENABLED=false` in env. Doesn't change the docker-compose contract — `BACKUP_DIR` is still required for the stack to come up, since true compose-level opt-out (conditional volume mounts) isn't worth the complexity for hypothetical consumers.

## Architecture

### Where things land

**`adit-radis-shared`**
- `pyproject.toml`: bump `django-dbbackup>=5.3.0`.
- `adit_radis_shared/common/tasks.py`: add the periodic `backup_db` task.
- `example_project/example_project/settings/base.py`, `development.py`, `production.py`: migrate to the new `STORAGES` format (see "Settings shape" below).
- Tag a new release `0.22.0` after merge.

**`adit`** (consumer)
- `pyproject.toml`: bump `adit-radis-shared @ git+...@0.22.0` and `django-dbbackup>=5.3.0`.
- `adit/settings/base.py`, `development.py`, `production.py`: migrate to the new `STORAGES` format.
- `adit/core/tasks.py`: delete the local `backup_db` function (keep `check_disk_space` and the rest of the file).
- Close PR #329 with a pointer to this consumer PR.

**`radis`** (consumer)
- `pyproject.toml`: bump `adit-radis-shared @ git+...@0.22.0` and `django-dbbackup>=5.3.0`.
- `radis/settings/base.py`, `development.py`, `production.py`: migrate to the new `STORAGES` format.
- `radis/core/tasks.py`: only contains `backup_db`; delete the file outright.

### Procrastinate task discovery

`adit_radis_shared.common` is already in `INSTALLED_APPS` of all three consumers. Procrastinate's Django integration auto-discovers `tasks.py` in installed apps, so adding `backup_db` to `common/tasks.py` registers it automatically in every consumer — no wiring changes needed.

## Settings shape (per-consumer pattern)

Each consumer's `settings/` package follows the same pattern. The only thing that differs across consumers is the default backup location string.

**`base.py`** — defines the full STORAGES dict including `staticfiles` so dev and test inherit it without further work:

```python
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-<project>")},
    },
}
DBBACKUP_CLEANUP_KEEP = 30
```

The legacy `DBBACKUP_STORAGE = ...` and `DBBACKUP_STORAGE_OPTIONS = {...}` lines are removed. `DBBACKUP_CLEANUP_KEEP` stays — it remains a valid dbbackup-native setting in 5.3+.

**`development.py`** — no STORAGES override needed; inherits from base.

**`production.py`** — was a full `STORAGES = {...}` replacement; becomes a single targeted override:

```python
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
```

**`test.py`** — no STORAGES override needed; inherits from base.

### Per-consumer default location strings

| Consumer | Default `DBBACKUP_STORAGE_LOCATION` |
|---|---|
| `adit` | `/tmp/backups-adit` (unchanged) |
| `radis` | `/tmp/backups-radis` (unchanged) |
| `example_project` | `/tmp/backups-example` (**fix**: currently `/tmp/backups-radis`, copy-paste leftover) |

## The shared `backup_db` task

Lives in `adit_radis_shared/common/tasks.py` next to the existing periodic tasks. Cron is configurable via Django settings; defaults match current behavior in both adit and radis.

```python
from django.conf import settings as django_settings

@app.periodic(cron=getattr(django_settings, "DBBACKUP_CRON", "0 3 * * *"))
@app.task(queueing_lock="backup_db")
def backup_db(timestamp: int):
    if not getattr(django_settings, "DBBACKUP_ENABLED", True):
        return
    call_command("dbbackup", "--clean", "-v", "2")
```

Each consumer's `base.py` adds:

```python
DBBACKUP_ENABLED = env.bool("DBBACKUP_ENABLED", default=True)
```

Choices:

- **Cron via settings**, default `"0 3 * * *"`. Consumers override by setting `DBBACKUP_CRON` in their Django settings.
- **`DBBACKUP_ENABLED` flag**, default `True`. Lets a consumer (or test/CI environment) no-op the task body via env without touching code. Procrastinate still wakes the task at the cron interval; the body returns early. Inexpensive at scale.
- **`queueing_lock="backup_db"`** prevents pile-ups if a backup ever runs longer than the cron interval.
- **`timestamp: int` signature** matches procrastinate's periodic-task convention used by the existing `retry_stalled_jobs` in this same file.
- **Flags `--clean -v 2` hardcoded** — matches existing behavior; not a parameter today.

## Sequencing & release

The work crosses three repos. adit and radis pin `adit-radis-shared` by git tag, so a release in shared must precede the consumer PRs. Until both consumer PRs ship, the 3am crash continues.

1. **Shared PR** — bump dep, add task, migrate `example_project` settings (including the location-default fix). Verify locally per "Verification" below. Merge.
2. **Tag `0.22.0`** in adit-radis-shared. Release notes call out the breaking dep bump and the consumer migration steps required.
3. **adit PR** and **radis PR** in parallel — bump shared pin, bump direct `django-dbbackup`, migrate settings, delete local `backup_db`. Each PR is independently testable and mergeable.
4. **Close PR #329** with a comment pointing to the adit consumer PR.

The user explicitly chose this sequence (plan A) over a quick-fix-then-refactor sequence (plan B/C). Adit and radis stay broken at 3am until steps 3 and 4 land. If the gap becomes painful, a settings-only hotfix can be merged in either consumer without waiting for shared; but the default plan is to wait for the proper chain.

## Verification (no new automated tests)

Each PR runs the standard validation:

```bash
uv run cli lint
uv run cli test
uv run cli compose-up -- --watch
```

**Shared PR specifically:**
- Bring up dev containers; confirm `backup_db` is registered as a periodic task in procrastinate (e.g., visible alongside `retry_stalled_jobs` in worker logs at startup).
- Manually trigger: `docker compose exec web ./manage.py dbbackup --clean -v 2` against `example_project`. Confirm a backup file lands under the configured location (`/tmp/backups-example` by default, or `/backups` inside the worker container per `BACKUP_DIR` mount).
- Confirm `dbbackup.settings` imports cleanly at startup — no `RuntimeError` about deprecated settings.

**Consumer PRs (adit, radis):**
- Same `dbbackup` smoke test in dev: `./manage.py dbbackup --clean -v 2`, confirm a file appears in the mounted `/backups`.
- Confirm only the shared `backup_db` is registered as a periodic task (no leftover duplicate from the local `core/tasks.py`).
- For radis: confirm `radis/core/tasks.py` deletion does not break any imports referencing it.

If pyright or other static checks complain about removed imports in `core/tasks.py`, clean those up as part of the consumer PRs.

## Why this won't be a flag day

- The shared release is independent: shipping `0.22.0` does not affect any running consumer until that consumer bumps its pin.
- adit and radis can land their PRs independently and in any order. Each PR is self-contained: it bumps the pin, migrates settings, and removes the local task in one atomic change. There is no intermediate state where a consumer references a function that no longer exists or where the new task is registered twice.
- Rollback is straightforward at every step: revert the consumer PR to go back to the legacy local task (with whatever django-dbbackup version was lockfile-pinned at the time).

## Open risks

- **Renovate may auto-PR a `django-dbbackup` bump again** before the consumer PRs land. The lockfile constraint of `>=4.2.1` allows it. Mitigation: land the consumer PRs promptly after the shared release; if Renovate beats us to it, the merge conflict is trivial.
- **`DBBACKUP_CLEANUP_KEEP` deprecation** is not currently a concern (still supported in 5.3.0), but worth re-checking against the upstream changelog at implementation time.
- **`example_project` default location change** (from `/tmp/backups-radis` to `/tmp/backups-example`) is a behavior change in the example only; no production impact, but call it out in the PR description.
