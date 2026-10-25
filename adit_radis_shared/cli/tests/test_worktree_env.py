import subprocess
from pathlib import Path

import pytest

from adit_radis_shared.cli import worktree_env


def git(*args: str, cwd: Path) -> None:
    subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


def test_dev_ports_reads_the_published_host_ports(tmp_path: Path):
    (tmp_path / "docker-compose.dev.yml").write_text(
        "services:\n"
        "  web:\n"
        "    ports:\n"
        "      - ${WEB_DEV_PORT:-8000}:8000\n"
        "      - ${REMOTE_DEBUGGING_PORT:-5678}:${REMOTE_DEBUGGING_PORT:-5678}\n"
        "    command: >\n"
        "      wait-for-it -s postgres.local:5432 -t ${WAIT_POSTGRES_TIMEOUT:-180}\n"
        "  orthanc1:\n"
        "    ports:\n"
        '      - "${ORTHANC1_DEV_PORT:-7501}:7501"\n'
    )

    assert worktree_env.dev_ports(tmp_path) == {
        "WEB_DEV_PORT": 8000,
        "REMOTE_DEBUGGING_PORT": 5678,
        "ORTHANC1_DEV_PORT": 7501,
    }


def test_render_records_the_slot_and_is_stable(tmp_path: Path):
    updates = {"WEB_DEV_PORT": "8100", "STACK_NAME": "project_wt1_wt", "NEW_PORT": "9100"}

    once = worktree_env.render("# Ports\nWEB_DEV_PORT=8000\n# STACK_NAME=x\n", 1, tmp_path, updates)

    assert once.splitlines()[0].startswith(f"# worktree slot: 1 of {tmp_path} (ports ")
    assert worktree_env.parse_env(once) == updates
    assert worktree_env.render(once, 1, tmp_path, updates) == once


MAIN_ENV = "WEB_DEV_PORT=48000\n"


def checkouts(tmp_path: Path, *names: str) -> tuple[Path, ...]:
    """A main checkout with MAIN_ENV and linked worktrees of it (default: one, "feature")."""
    main = tmp_path / "main"
    main.mkdir()
    (main / "docker-compose.dev.yml").write_text("    ports:\n      - ${WEB_DEV_PORT:-8000}:8000\n")
    git("init", "-q", cwd=main)
    git("add", "docker-compose.dev.yml", cwd=main)
    git("commit", "-q", "-m", "init", cwd=main)
    (main / ".env").write_text(MAIN_ENV)
    worktrees = [tmp_path / name for name in names or ("feature",)]
    for worktree in worktrees:
        git("worktree", "add", "-q", str(worktree), cwd=main)
    return main, *worktrees


def set_in_env(path: Path, var: str, value: str) -> None:
    lines = path.read_text().splitlines()
    path.write_text(
        "".join(f"{var}={value}\n" if line.startswith(f"{var}=") else f"{line}\n" for line in lines)
    )


def test_configure_gives_a_linked_worktree_its_own_ports_and_stack(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    main, worktree = checkouts(tmp_path)

    worktree_env.configure(main, "project")
    assert capsys.readouterr().out == ""
    worktree_env.configure(worktree, "project")

    env = (worktree / ".env").read_text()
    assert env.startswith(f"# worktree slot: 1 of {worktree.resolve()} (ports ")
    assert worktree_env.parse_env(env) == {
        "WEB_DEV_PORT": "48100",
        "STACK_NAME": "project_wt1_feature",
    }
    assert (main / ".env").read_text() == MAIN_ENV


def test_configure_keeps_a_port_changed_by_hand(tmp_path: Path):
    _, worktree = checkouts(tmp_path)
    env_file = worktree / ".env"
    worktree_env.configure(worktree, "project")

    set_in_env(env_file, "WEB_DEV_PORT", "48150")
    worktree_env.configure(worktree, "project")

    assert worktree_env.parse_env(env_file.read_text())["WEB_DEV_PORT"] == "48150"


def test_configure_gives_each_worktree_its_own_slot_and_keeps_it(tmp_path: Path):
    _, first, second = checkouts(tmp_path, "first", "second")

    worktree_env.configure(first, "project")
    worktree_env.configure(second, "project")
    worktree_env.configure(first, "project")

    assert worktree_env.parse_env((first / ".env").read_text())["WEB_DEV_PORT"] == "48100"
    assert worktree_env.parse_env((second / ".env").read_text())["WEB_DEV_PORT"] == "48200"


def test_configure_skips_a_slot_whose_ports_are_in_use(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _, worktree = checkouts(tmp_path)
    monkeypatch.setattr(worktree_env, "in_use", lambda port: port == 48100)

    worktree_env.configure(worktree, "project")

    env = worktree_env.parse_env((worktree / ".env").read_text())
    assert env["WEB_DEV_PORT"] == "48200"
    assert env["STACK_NAME"] == "project_wt2_feature"


def test_configure_refuses_a_slot_for_the_main_checkout(tmp_path: Path):
    main, _ = checkouts(tmp_path)

    with pytest.raises(SystemExit, match="main checkout"):
        worktree_env.configure(main, "project", 3)
    assert (main / ".env").read_text() == MAIN_ENV


def test_configure_leaves_a_worktree_alone_when_git_lists_no_main_checkout(tmp_path: Path):
    main = tmp_path / "main"
    main.mkdir()
    git("init", "-q", f"--separate-git-dir={tmp_path / 'main.git'}", cwd=main)
    git("commit", "-q", "--allow-empty", "-m", "init", cwd=main)
    (main / ".env").write_text(MAIN_ENV)
    worktree = tmp_path / "feature"
    git("worktree", "add", "-q", str(worktree), cwd=main)

    worktree_env.configure(worktree, "project")

    assert not (worktree / ".env").exists()


def test_configure_runs_unlocked_when_the_lock_cannot_be_opened(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
):
    main, worktree = checkouts(tmp_path)
    (main / ".git" / "worktree-env.lock").mkdir()

    worktree_env.configure(worktree, "project")

    assert "warning: could not lock" in capsys.readouterr().out
    assert worktree_env.parse_env((worktree / ".env").read_text())["WEB_DEV_PORT"] == "48100"
