# dbbackup Shared Task Implementation Plan (adit-radis-shared)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the duplicated `backup_db` periodic task into adit-radis-shared, bump `django-dbbackup` to ≥5.3.0, and migrate `example_project` settings to the new `STORAGES["dbbackup"]` format.

**Architecture:** Add a single periodic task `backup_db` to `adit_radis_shared/common/tasks.py` next to the existing shared periodic tasks. Procrastinate auto-discovers it in any consumer that already has `adit_radis_shared.common` in `INSTALLED_APPS`. Migrate the example app's settings to prove out the pattern. Tag a new release `0.22.0` for consumers to pin.

**Tech Stack:** Django 5.1.6+, django-dbbackup 5.3.0+, Procrastinate 3.0.2+, Python 3.12+, uv.

**Working directory:** `/workspaces/adit-radis-workspace/projects/adit-radis-shared`

**Branch:** `feat/move-backup-task-to-shared` (already exists with the design spec). All commits land on this branch.

**Spec:** `docs/superpowers/specs/2026-05-06-dbbackup-shared-design.md`

---

## File map

- **Modify** `pyproject.toml` — bump `django-dbbackup>=5.3.0`.
- **Modify** `example_project/example_project/settings/base.py` — replace legacy `DBBACKUP_STORAGE`/`DBBACKUP_STORAGE_OPTIONS` block with new `STORAGES` dict; fix copy-paste default `/tmp/backups-radis` → `/tmp/backups-example`.
- **Modify** `example_project/example_project/settings/production.py` — change `STORAGES = {…}` full-replacement to single targeted `STORAGES["staticfiles"] = …` override.
- **Modify** `adit_radis_shared/common/tasks.py` — append `backup_db` periodic task.
- **No changes** to `example_project/example_project/settings/development.py` or `test.py` (inherit from base).
- **No new tests** (per spec — D was chosen during brainstorming).
- **No changes** to `adit_radis_shared/cli/commands.py` (the existing `db-backup`/`db-restore` CLI commands shell out to the management command, which picks up the new settings transparently).

---

### Task 1: Bump `django-dbbackup` dependency to ≥5.3.0

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Edit the dependency**

In `pyproject.toml`, change the existing line:

```toml
    "django-dbbackup>=4.2.1",
```

to:

```toml
    "django-dbbackup>=5.3.0",
```

- [ ] **Step 2: Update lockfile and install**

Run: `uv sync`
Expected: `uv.lock` updates `django-dbbackup` to a 5.3.x version. No errors.

- [ ] **Step 3: Verify the resolved version**

Run: `uv tree | grep django-dbbackup`
Expected: shows `django-dbbackup v5.3.x` (some 5.3+ patch version).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore(deps): bump django-dbbackup to >=5.3.0"
```

---

### Task 2: Migrate `example_project` `base.py` to new `STORAGES` format

**Files:**
- Modify: `example_project/example_project/settings/base.py` (lines 230–235, the `# django-dbbackup` block)

- [ ] **Step 1: Replace the legacy block**

In `example_project/example_project/settings/base.py`, find this block (around line 230):

```python
# django-dbbackup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {
    "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-radis")
}
DBBACKUP_CLEANUP_KEEP = 30
```

Replace it with:

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
            "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-example")
        },
    },
}
DBBACKUP_CLEANUP_KEEP = 30
BACKUP_ENABLED = env.bool("BACKUP_ENABLED", default=True)
```

Three things change:
1. The legacy `DBBACKUP_STORAGE` / `DBBACKUP_STORAGE_OPTIONS` keys are replaced by a `STORAGES` dict that defines all three named storages (`default`, `staticfiles`, `dbbackup`).
2. The default location string changes from `"/tmp/backups-radis"` (copy-paste leftover) to `"/tmp/backups-example"`.
3. A new `BACKUP_ENABLED` setting (default `True`) is added so the shared periodic task can be no-op'd via env.

- [ ] **Step 2: Sanity-check that no `DBBACKUP_STORAGE` references remain**

Run: `grep -n "DBBACKUP_STORAGE\b\|DBBACKUP_STORAGE_OPTIONS" example_project/example_project/settings/base.py`
Expected: no output (no matches).

- [ ] **Step 3: Confirm `DBBACKUP_CLEANUP_KEEP` is still set**

Run: `grep -n "DBBACKUP_CLEANUP_KEEP" example_project/example_project/settings/base.py`
Expected: one line, `DBBACKUP_CLEANUP_KEEP = 30`.

- [ ] **Step 4: Commit**

```bash
git add example_project/example_project/settings/base.py
git commit -m "refactor(example_project): migrate base settings to STORAGES dict for dbbackup 5.3+"
```

---

### Task 3: Migrate `example_project` `production.py` to targeted `STORAGES` override

**Files:**
- Modify: `example_project/example_project/settings/production.py` (lines 15–22, the `STORAGES = {…}` block)

- [ ] **Step 1: Replace the full-replacement block with a targeted override**

In `example_project/example_project/settings/production.py`, find:

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

This preserves the `default` and `dbbackup` entries inherited from base while overriding only `staticfiles` for production.

- [ ] **Step 2: Verify the file still imports correctly**

Run: `uv run python -c "from example_project.settings import production; print(production.STORAGES)"`
Expected: prints a dict with three keys (`default`, `staticfiles`, `dbbackup`). The `staticfiles` `BACKEND` is the whitenoise one. No `RuntimeError`.

- [ ] **Step 3: Commit**

```bash
git add example_project/example_project/settings/production.py
git commit -m "refactor(example_project): override only staticfiles in production STORAGES"
```

---

### Task 4: Add `backup_db` periodic task to shared `common/tasks.py`

**Files:**
- Modify: `adit_radis_shared/common/tasks.py`

- [ ] **Step 1: Append the new task to the end of the file**

In `adit_radis_shared/common/tasks.py`, append at the bottom (after `retry_stalled_jobs`):

```python


@app.periodic(cron=getattr(settings, "DBBACKUP_CRON", "0 3 * * *"))
@app.task(queueing_lock="backup_db")
def backup_db(timestamp: int):
    if not getattr(settings, "BACKUP_ENABLED", True):
        return
    call_command("dbbackup", "--clean", "-v", "2")
```

`settings`, `call_command`, and `app` are already imported at the top of the file — no new imports needed. The signature `(timestamp: int)` matches procrastinate's periodic-task convention used by `retry_stalled_jobs` directly above. The `queueing_lock` prevents pile-ups if a backup ever runs longer than the cron interval. The `BACKUP_ENABLED` gate (default `True` via `getattr`) lets a consumer opt out of running the actual backup without disabling the periodic task itself.

- [ ] **Step 2: Verify the file imports cleanly**

Run: `uv run python -c "from adit_radis_shared.common import tasks; print(tasks.backup_db)"`
Expected: prints something like `<Task(name='adit_radis_shared.common.tasks.backup_db')>` (or similar procrastinate task repr). No errors.

- [ ] **Step 3: Commit**

```bash
git add adit_radis_shared/common/tasks.py
git commit -m "feat(common): add shared backup_db periodic task"
```

---

### Task 5: Run lint and full test suite

- [ ] **Step 1: Lint**

Run: `uv run cli lint`
Expected: passes. If pyright complains about any new code, fix inline before proceeding.

- [ ] **Step 2: Tests** (containers must be running; if not, run `uv run cli compose-up -d` first)

Run: `uv run cli test`
Expected: all tests pass. The existing test suite covers settings import implicitly — if anything imports `dbbackup.settings` during test setup, a stray legacy setting would surface here as a `RuntimeError`.

- [ ] **Step 3: Commit any lint fixes (if needed)**

If lint or tests required code fixes, commit them with a message describing the fix. If nothing needed fixing, skip this step.

---

### Task 6: Smoke-test the periodic task and dbbackup command end-to-end

This is verification-only — no commits.

- [ ] **Step 1: Bring up dev containers (if not already up)**

Run: `uv run cli compose-up -d`
Expected: web, worker, and postgres containers running. No startup errors in the worker logs.

- [ ] **Step 2: Confirm the task is registered**

Run: `docker compose logs worker | grep -i "backup_db"`
Expected: at least one log line referencing `backup_db` from procrastinate's startup task discovery (alongside `retry_stalled_jobs`). If your stack's worker log format differs, alternatively check that `worker` started cleanly with no `RuntimeError` mentioning deprecated dbbackup settings.

- [ ] **Step 3: Manually run `dbbackup` against `example_project`**

Run: `docker compose exec web ./manage.py dbbackup --clean -v 2`
Expected: command exits 0 and prints something like `Backing up Database…` and `Writing file …`. A backup file appears under `/backups` in the web container (the host mount is `${BACKUP_DIR}` per `docker-compose.base.yml`).

Verify the file landed:

```bash
docker compose exec web ls -la /backups
```

Expected: at least one `*.psql.bin` file (or similar dbbackup-named file) with a recent timestamp.

- [ ] **Step 4: Confirm no deprecation `RuntimeError`**

Run: `docker compose exec web uv run python -c "import dbbackup.settings"`
Expected: exits 0 with no output. If a `RuntimeError` mentions `DBBACKUP_STORAGE` or `DBBACKUP_STORAGE_OPTIONS`, a legacy setting leaked through — re-check Tasks 2 and 3.

If anything fails here, fix and recommit before opening the PR.

---

### Task 7: Open the PR

- [ ] **Step 1: Push the branch**

Run: `git push -u origin feat/move-backup-task-to-shared`

- [ ] **Step 2: Create the PR**

Run:

```bash
gh pr create --title "feat: add shared backup_db task and migrate to django-dbbackup 5.3+" --body "$(cat <<'EOF'
## Summary
- Bump `django-dbbackup` to ≥5.3.0 (legacy `DBBACKUP_STORAGE`/`DBBACKUP_STORAGE_OPTIONS` settings now raise at import time).
- Migrate `example_project` settings to the new `STORAGES["dbbackup"]` format (with the `default`/`staticfiles` entries restated in `base.py` so dev and test inherit them cleanly).
- Add a shared `backup_db` periodic task in `adit_radis_shared/common/tasks.py`. Cron is configurable via `settings.DBBACKUP_CRON`, defaulting to `"0 3 * * *"`. Procrastinate auto-discovers it in any consumer that already has `adit_radis_shared.common` in `INSTALLED_APPS`.
- Fix copy-paste leftover in example_project's default backup location: `/tmp/backups-radis` → `/tmp/backups-example`.

Once merged and tagged as `0.22.0`, adit and radis will bump their pin and drop their local `backup_db` copies. Supersedes openradx/adit#329.

Spec: `docs/superpowers/specs/2026-05-06-dbbackup-shared-design.md`

## Test plan
- [x] `uv run cli lint` passes
- [x] `uv run cli test` passes
- [x] `./manage.py dbbackup --clean -v 2` runs successfully against the dev stack and writes a backup file to `/backups`
- [x] Worker starts without `RuntimeError` and registers `backup_db` as a periodic task
EOF
)"
```

Expected: PR URL printed.

---

### Task 8: After merge — tag the new release

This step happens after the PR is reviewed and merged into `main`.

- [ ] **Step 1: Pull latest main**

Run: `git switch main && git pull --ff-only origin main`

- [ ] **Step 2: Tag the new version**

Run:

```bash
git tag -a 0.22.0 -m "Add shared backup_db task; require django-dbbackup>=5.3.0"
git push origin 0.22.0
```

(`0.22.0` follows the existing `0.21.0` tag — minor bump because of the new shared task and the breaking dep change that requires consumers to migrate their own settings.)

- [ ] **Step 3: Confirm the tag is visible on GitHub**

Run: `gh release view 0.22.0` (if a release object is desired) or `gh api repos/openradx/adit-radis-shared/git/refs/tags/0.22.0`
Expected: the tag exists upstream. Adit and radis can now bump their pin to `@0.22.0` (see the consumer plans).

---

## Notes

- The periodic task in `common/tasks.py` will be active in **every** consumer that has `adit_radis_shared.common` installed (all of them today). This is the intended consolidation — there is no opt-out flag in this change.
- This release is a breaking change for consumers because they must remove their legacy `DBBACKUP_STORAGE`/`DBBACKUP_STORAGE_OPTIONS` settings and add the new `STORAGES` dict. Failing to migrate causes `RuntimeError` at app startup. Call this out in the GitHub release notes.
