# dbbackup Migration Plan (adit consumer)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bump adit's `adit-radis-shared` pin to `0.22.0`, migrate adit's settings to the new `STORAGES["dbbackup"]` format, drop the now-redundant local `backup_db` task, and supersede PR #329.

**Architecture:** Mechanical consumer migration. The shared library now provides the periodic `backup_db` task; adit just needs to bring in the new shared release, update its settings to the new django-dbbackup config format, and remove its local copy of the task.

**Tech Stack:** Django 5.1.6+, django-dbbackup 5.3.0+, Procrastinate 3.0.2+, Python 3.12+, uv.

**Working directory:** `/workspaces/adit-radis-workspace/projects/adit`

**Branch:** `feat/dbbackup-shared-and-5.3-migration` (create new from `main`).

**Prerequisite:** The shared plan (`2026-05-06-dbbackup-shared-task.md`) is fully complete, including the `0.22.0` tag pushed to `openradx/adit-radis-shared`. Confirm with: `gh api repos/openradx/adit-radis-shared/git/refs/tags/0.22.0` — should return 200 OK.

**Spec:** `docs/superpowers/specs/2026-05-06-dbbackup-shared-design.md` in adit-radis-shared.

---

## File map

- **Modify** `pyproject.toml` — bump `adit-radis-shared` pin to `0.22.0`; bump `django-dbbackup>=5.3.0`.
- **Modify** `adit/settings/base.py` — replace legacy `DBBACKUP_STORAGE` block (lines ~343–348) with new `STORAGES` dict.
- **Modify** `adit/settings/production.py` — change `STORAGES = {…}` full-replacement to a single `STORAGES["staticfiles"] = …` override.
- **Modify** `adit/core/tasks.py` — delete the `backup_db` function (lines ~50–53). Keep `check_disk_space` and the rest of the file.
- **No changes** to `adit/settings/development.py` or `adit/settings/test.py` (inherit from base).

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

### Task 3: Migrate `adit/settings/base.py` to new `STORAGES` format

**Files:**
- Modify: `adit/settings/base.py` (the `# django-dbbackup` block, currently around lines 343–348)

- [ ] **Step 1: Replace the legacy block**

In `adit/settings/base.py`, find:

```python
# django-dbbackup
DBBACKUP_STORAGE = "django.core.files.storage.FileSystemStorage"
DBBACKUP_STORAGE_OPTIONS = {
    "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-adit")
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
            "location": env.str("DBBACKUP_STORAGE_LOCATION", default="/tmp/backups-adit")
        },
    },
}
DBBACKUP_CLEANUP_KEEP = 30
BACKUP_ENABLED = env.bool("BACKUP_ENABLED", default=True)
BACKUP_CRON = env.str("BACKUP_CRON", default="0 3 * * *")
```

The `default` and `staticfiles` entries restate Django's built-in defaults so that `development.py` and `test.py` (which don't override `STORAGES`) keep working unchanged. The `BACKUP_ENABLED` line gives operators a runtime opt-out (e.g. for a test environment); the shared `backup_db` task no-ops when this is `False`. The `BACKUP_CRON` line lets the cron schedule be overridden via env without touching code.

- [ ] **Step 2: Sanity-check that no `DBBACKUP_STORAGE` references remain**

Run: `grep -n "DBBACKUP_STORAGE\b\|DBBACKUP_STORAGE_OPTIONS" adit/settings/base.py`
Expected: no output.

- [ ] **Step 3: Commit**

```bash
git add adit/settings/base.py
git commit -m "refactor(settings): migrate base settings to STORAGES dict for dbbackup 5.3+"
```

---

### Task 4: Migrate `adit/settings/production.py` to targeted `STORAGES` override

**Files:**
- Modify: `adit/settings/production.py` (the `STORAGES = {…}` block, around lines 15–22)

- [ ] **Step 1: Replace the full-replacement block with a targeted override**

In `adit/settings/production.py`, find:

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

This preserves the `default` and `dbbackup` entries from `base.py` while overriding only `staticfiles` for production.

- [ ] **Step 2: Verify the file imports correctly**

Run: `uv run python -c "from adit.settings import production; print(production.STORAGES)"`
Expected: prints a dict with three keys (`default`, `staticfiles`, `dbbackup`). The `staticfiles` `BACKEND` is the whitenoise one. The `dbbackup` `OPTIONS["location"]` is `/tmp/backups-adit` (or whatever `DBBACKUP_STORAGE_LOCATION` is set to in the env). No `RuntimeError`.

- [ ] **Step 3: Commit**

```bash
git add adit/settings/production.py
git commit -m "refactor(settings): override only staticfiles in production STORAGES"
```

---

### Task 5: Delete the local `backup_db` task

**Files:**
- Modify: `adit/core/tasks.py` (the `backup_db` function and its `@app.periodic` decorator, around lines 50–53)

- [ ] **Step 1: Remove the local task**

In `adit/core/tasks.py`, find and delete:

```python
@app.periodic(cron="0 3 * * * ")  # every day at 3am
@app.task
def backup_db(*args, **kwargs):
    call_command("dbbackup", "--clean", "-v 2")
```

(Also delete the blank line above this block if it leaves a double blank line.)

Keep the rest of the file intact, including `check_disk_space` and `_run_dicom_task` and `process_dicom_task`.

- [ ] **Step 2: Check whether `call_command` is still used elsewhere in the file**

Run: `grep -n "call_command" adit/core/tasks.py`
Expected: at least one remaining usage. If `grep` returns nothing, also remove the `from django.core.management import call_command` import at the top of the file.

- [ ] **Step 3: Verify the file imports cleanly**

Run: `uv run python -c "from adit.core import tasks; print(getattr(tasks, 'backup_db', 'gone'))"`
Expected: prints `gone` (the local function no longer exists in this module). No import errors.

- [ ] **Step 4: Confirm the shared task is reachable**

Run: `uv run python -c "from adit_radis_shared.common.tasks import backup_db; print(backup_db)"`
Expected: prints the shared procrastinate task object. No errors.

- [ ] **Step 5: Commit**

```bash
git add adit/core/tasks.py
git commit -m "refactor(core): drop local backup_db task in favor of shared one"
```

---

### Task 6: Run lint and full test suite

- [ ] **Step 1: Lint**

Run: `uv run cli lint`
Expected: passes. Common gotchas:
- pyright may warn about an unused import if `call_command` was only used by `backup_db` and Step 5/2 missed it.
- ruff may flag any leftover blank-line issues from the deletion.

Fix inline before proceeding.

- [ ] **Step 2: Tests** (containers must be running)

Run: `uv run cli test`
Expected: all tests pass. The settings-import path is exercised implicitly during test setup; a stray legacy `DBBACKUP_STORAGE` would surface here as a `RuntimeError`.

- [ ] **Step 3: Commit any lint/test fixups (if needed)**

Only if Steps 1 or 2 required code changes. Skip otherwise.

---

### Task 7: Smoke-test end-to-end

Verification only — no commits.

- [ ] **Step 1: Bring up dev containers**

Run: `uv run cli compose-up -d` (or `--watch` if you want hot-reload)
Expected: web, worker, postgres come up. No `RuntimeError` in worker logs about deprecated dbbackup settings.

- [ ] **Step 2: Confirm only the shared `backup_db` is registered**

Run: `docker compose logs worker | grep -i "backup_db"`
Expected: log lines reference `adit_radis_shared.common.tasks.backup_db` (the shared task), and **not** `adit.core.tasks.backup_db`. If both appear, Task 5 didn't fully remove the local copy — go back and re-check.

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
- Migrate `adit/settings/base.py` to the new `STORAGES["dbbackup"]` format (legacy `DBBACKUP_STORAGE`/`DBBACKUP_STORAGE_OPTIONS` raise at import time in 5.3+).
- Drop the local `backup_db` from `adit/core/tasks.py`; the shared task is auto-registered via procrastinate's app discovery.

Supersedes #329.

## Test plan
- [x] `uv run cli lint` passes
- [x] `uv run cli test` passes
- [x] `./manage.py dbbackup --clean -v 2` runs successfully and writes a backup file
- [x] Worker logs show only the shared `backup_db` task is registered (no duplicate from `adit.core.tasks`)
EOF
)"
```

Expected: PR URL printed.

---

### Task 9: Close PR #329 with a pointer

- [ ] **Step 1: Comment on PR #329 and close it**

Run:

```bash
gh pr close 329 --repo openradx/adit --comment "Superseded by #<this-PR-number>, which moves the backup_db task into adit-radis-shared and applies the django-dbbackup 5.3+ migration. Thanks for the diff — the new PR uses your STORAGES shape with one tweak (staticfiles lives in base.py so dev/test inherit it cleanly)."
```

Replace `<this-PR-number>` with the PR number from Task 8 Step 2.

Expected: PR #329 closes with a comment linking forward.

---

## Notes

- This PR depends on `0.22.0` of adit-radis-shared being tagged. If that hasn't shipped yet, do not open this PR.
- Renovate may have an in-flight PR bumping `django-dbbackup` against the legacy settings; close it once this PR merges (or rebase if it raced).
