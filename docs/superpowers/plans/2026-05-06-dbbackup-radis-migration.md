# dbbackup Migration Plan (radis consumer)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bump radis's `adit-radis-shared` pin to `0.22.0`, migrate radis's settings to the new `STORAGES["dbbackup"]` format, and delete the now-redundant `radis/core/tasks.py` file.

**Architecture:** Mechanical consumer migration, mirroring the adit migration. The shared library now provides the periodic `backup_db` task; radis just needs to bring in the new shared release, update its settings, and delete its local task file (which only contained `backup_db` and becomes empty after the deletion).

**Tech Stack:** Django 5.1.6+, django-dbbackup 5.3.0+, Procrastinate 3.0.2+, Python 3.12+, uv.

**Working directory:** `/workspaces/adit-radis-workspace/projects/radis`

**Branch:** `feat/dbbackup-shared-and-5.3-migration` (create new from `main`).

**Prerequisite:** The shared plan (`2026-05-06-dbbackup-shared-task.md`) is fully complete, including the `0.22.0` tag pushed to `openradx/adit-radis-shared`. Confirm with: `gh api repos/openradx/adit-radis-shared/git/refs/tags/0.22.0` — should return 200 OK.

**Spec:** `docs/superpowers/specs/2026-05-06-dbbackup-shared-design.md` in adit-radis-shared.

---

## File map

- **Modify** `pyproject.toml` — bump `adit-radis-shared` pin to `0.22.0`; bump `django-dbbackup>=5.3.0`.
- **Modify** `radis/settings/base.py` — replace legacy `DBBACKUP_STORAGE` block (lines ~307–312) with new `STORAGES` dict.
- **Modify** `radis/settings/production.py` — change `STORAGES = {…}` full-replacement to single `STORAGES["staticfiles"] = …` override.
- **Delete** `radis/core/tasks.py` — currently contains only `backup_db` and becomes empty after removal.
- **No changes** to `radis/settings/development.py` or `radis/settings/test.py`.

---

### Task 1: Create the feature branch

- [ ] **Step 1: Make sure main is clean and up-to-date**

Run: `git status && git switch main && git pull --ff-only origin main`
Expected: clean working tree on `main` at the latest commit.

- [ ] **Step 2: Create the branch**

Run: `git switch -c feat/dbbackup-shared-and-5.3-migration`
Expected: switched to a new branch.

---

### Task 2: Bump `adit-radis-shared` pin and `django-dbbackup`

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Bump the shared library pin**

In `pyproject.toml`, change:

```toml
    "adit-radis-shared @ git+https://github.com/openradx/adit-radis-shared.git@0.21.0",
```

to:

```toml
    "adit-radis-shared @ git+https://github.com/openradx/adit-radis-shared.git@0.22.0",
```

- [ ] **Step 2: Bump django-dbbackup**

In `pyproject.toml`, change:

```toml
    "django-dbbackup>=4.2.1",
```

to:

```toml
    "django-dbbackup>=5.3.0",
```

- [ ] **Step 3: Update lockfile**

Run: `uv sync`
Expected: `uv.lock` updates both `adit-radis-shared` (to `0.22.0`) and `django-dbbackup` (to a `5.3.x` version). No errors.

- [ ] **Step 4: Verify the resolved versions**

Run: `uv tree | grep -E "adit-radis-shared|django-dbbackup"`
Expected: shows `adit-radis-shared 0.22.0` and `django-dbbackup v5.3.x`.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): bump adit-radis-shared to 0.22.0 and django-dbbackup to >=5.3.0"
```

---

### Task 3: Migrate `radis/settings/base.py` to new `STORAGES` format

**Files:**
- Modify: `radis/settings/base.py` (the `# django-dbbackup` block, currently around lines 307–312)

- [ ] **Step 1: Replace the legacy block**

In `radis/settings/base.py`, find:

```python
# django-dbbackup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {
    "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-radis")
}
DBBACKUP_CLEANUP_KEEP = 30
```

Replace with:

```python
# Django default storage and django-dbbackup
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "dbbackup": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {
            "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-radis")
        },
    },
}
DBBACKUP_CLEANUP_KEEP = 30
```

The default location string remains `/tmp/backups-radis` — same as before. The `default`/`staticfiles` entries restate Django's built-in defaults so dev and test inherit them unchanged.

- [ ] **Step 2: Sanity-check that no `DBBACKUP_STORAGE` references remain**

Run: `grep -n "DBBACKUP_STORAGE\b\|DBBACKUP_STORAGE_OPTIONS" radis/settings/base.py`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add radis/settings/base.py
git commit -m "refactor(settings): migrate base settings to STORAGES dict for dbbackup 5.3+"
```

---

### Task 4: Migrate `radis/settings/production.py` to targeted `STORAGES` override

**Files:**
- Modify: `radis/settings/production.py` (the `STORAGES = {…}` block, around lines 15–22)

- [ ] **Step 1: Replace the full-replacement block with a targeted override**

In `radis/settings/production.py`, find:

```python
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
```

Replace with:

```python
STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
}
```

- [ ] **Step 2: Verify the file imports correctly**

Run: `uv run python -c "from radis.settings import production; print(production.STORAGES)"`
Expected: prints a dict with three keys (`default`, `staticfiles`, `dbbackup`). The `staticfiles` `BACKEND` is the whitenoise one. No `RuntimeError`.

- [ ] **Step 3: Commit**

```bash
git add radis/settings/production.py
git commit -m "refactor(settings): override only staticfiles in production STORAGES"
```

---

### Task 5: Delete `radis/core/tasks.py`

**Files:**
- Delete: `radis/core/tasks.py`

The current contents of this file are:

```python
import logging

from django.core.management import call_command
from procrastinate.contrib.django import app

logger = logging.getLogger(__name__)


@app.periodic(cron="0 3 * * * ")  # every day at 3am
@app.task
def backup_db(*args, **kwargs):
    call_command("dbbackup", "--clean", "-v 2")
```

It only contains `backup_db`, which now lives in `adit_radis_shared.common.tasks`. The file becomes empty after removal, so we delete it outright.

- [ ] **Step 1: Confirm nothing imports `radis.core.tasks`**

Run: `grep -rn "radis\.core\.tasks\|radis\.core import tasks\|from \.tasks\|from \.\.tasks" radis 2>/dev/null | grep -v __pycache__`
Expected: no output. (Verified absent at planning time, but re-check before deleting.)

If anything turns up, stop and surface it — the deletion would break those callers and we'd need a different approach.

- [ ] **Step 2: Delete the file**

Run: `rm radis/core/tasks.py`

- [ ] **Step 3: Confirm the shared task is reachable**

Run: `uv run python -c "from adit_radis_shared.common.tasks import backup_db; print(backup_db)"`
Expected: prints the shared procrastinate task object. No errors.

- [ ] **Step 4: Commit**

```bash
git add -A radis/core/tasks.py
git commit -m "refactor(core): drop local backup_db task in favor of shared one"
```

(`-A` is needed here so git records the deletion.)

---

### Task 6: Run lint and full test suite

- [ ] **Step 1: Lint**

Run: `uv run cli lint`
Expected: passes. If anything breaks (e.g. an unrelated pyright complaint stirred up by removed imports), fix inline.

- [ ] **Step 2: Tests** (containers must be running)

Run: `uv run cli test`
Expected: all tests pass.

- [ ] **Step 3: Commit any lint/test fixups (if needed)**

Only if Steps 1 or 2 required code changes.

---

### Task 7: Smoke-test end-to-end

Verification only — no commits.

- [ ] **Step 1: Bring up dev containers**

Run: `uv run cli compose-up -d`
Expected: web, worker, postgres come up. No `RuntimeError` in worker logs.

- [ ] **Step 2: Confirm only the shared `backup_db` is registered**

Run: `docker compose logs worker | grep -i "backup_db"`
Expected: log lines reference `adit_radis_shared.common.tasks.backup_db` only. There should be no `radis.core.tasks` reference because the file no longer exists.

- [ ] **Step 3: Manually run `dbbackup`**

Run: `docker compose exec web ./manage.py dbbackup --clean -v 2`
Expected: command exits 0; a backup file lands under `/backups` in the container.

```bash
docker compose exec web ls -la /backups
```

Expected: at least one recent backup file.

- [ ] **Step 4: Confirm no deprecation `RuntimeError`**

Run: `docker compose exec web uv run python -c "import dbbackup.settings"`
Expected: exits 0 with no output.

If anything fails, fix and recommit before opening the PR.

---

### Task 8: Open the PR

- [ ] **Step 1: Push the branch**

Run: `git push -u origin feat/dbbackup-shared-and-5.3-migration`

- [ ] **Step 2: Create the PR**

Run:

```bash
gh pr create --title "feat: migrate to django-dbbackup 5.3+ and use shared backup_db task" --body "$(cat <<'EOF'
## Summary
- Bump `adit-radis-shared` to `0.22.0` (which adds a shared `backup_db` periodic task).
- Bump `django-dbbackup` to `>=5.3.0`.
- Migrate `radis/settings/base.py` to the new `STORAGES["dbbackup"]` format (legacy settings raise at import time in 5.3+).
- Delete `radis/core/tasks.py`; the shared task is auto-registered via procrastinate's app discovery.

Fixes the nightly backup crash caused by Renovate-induced `django-dbbackup` 5.x upgrade against the legacy settings format.

## Test plan
- [x] `uv run cli lint` passes
- [x] `uv run cli test` passes
- [x] `./manage.py dbbackup --clean -v 2` runs successfully and writes a backup file
- [x] Worker logs show only the shared `backup_db` task is registered
EOF
)"
```

Expected: PR URL printed.

---

## Notes

- This PR depends on `0.22.0` of adit-radis-shared being tagged. If that hasn't shipped yet, do not open this PR.
- Renovate may have an in-flight PR bumping `django-dbbackup` against the legacy settings; close it once this PR merges (or rebase if it raced).
