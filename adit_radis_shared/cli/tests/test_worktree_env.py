import json
import subprocess
from pathlib import Path

import pytest

from adit_radis_shared.cli import worktree_env


@pytest.fixture
def registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    registry = tmp_path / "dev-ports"
    monkeypatch.setattr(worktree_env, "REGISTRY", registry)
    return registry


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


def test_claims_skips_records_of_another_shape(tmp_path: Path, registry: Path):
    other = tmp_path / "other"
    other.mkdir()
    records = {
        "valid.json": {"checkout": str(other), "ports": {"WEB_DEV_PORT": 8100}},
        "deleted.json": {"checkout": str(tmp_path / "deleted"), "ports": {"WEB_DEV_PORT": 8200}},
        "list.json": [],
        "no-ports.json": {"checkout": str(other)},
        "bad-port.json": {"checkout": str(other), "ports": {"WEB_DEV_PORT": "x"}},
    }
    registry.mkdir()
    for name, record in records.items():
        (registry / name).write_text(json.dumps(record))
    (registry / "truncated.json").write_text("{")

    assert worktree_env.claims(tmp_path / "self") == [(str(other), "WEB_DEV_PORT", 8100)]
    assert not (registry / "deleted.json").exists()
    assert (registry / "list.json").exists()


def test_render_records_the_slot_and_is_stable(tmp_path: Path):
    updates = {"WEB_DEV_PORT": "8100", "STACK_NAME": "project_wt1_wt", "NEW_PORT": "9100"}

    once = worktree_env.render("# Ports\nWEB_DEV_PORT=8000\n# STACK_NAME=x\n", 1, tmp_path, updates)

    assert once.splitlines()[0].startswith(f"# worktree slot: 1 of {tmp_path} (ports ")
    assert worktree_env.parse_env(once) == updates
    assert worktree_env.render(once, 1, tmp_path, updates) == once


MAIN_ENV = "WEB_DEV_PORT=48000\nSITE_URL=http://localhost:48000/\n"


def checkouts(tmp_path: Path) -> tuple[Path, Path]:
    """A main checkout with MAIN_ENV and a linked worktree of it."""
    main = tmp_path / "main"
    main.mkdir()
    (main / "docker-compose.dev.yml").write_text("    ports:\n      - ${WEB_DEV_PORT:-8000}:8000\n")
    git("init", "-q", cwd=main)
    git("add", "docker-compose.dev.yml", cwd=main)
    git("commit", "-q", "-m", "init", cwd=main)
    (main / ".env").write_text(MAIN_ENV)
    worktree = tmp_path / "feature"
    git("worktree", "add", "-q", str(worktree), cwd=main)
    return main, worktree


def set_in_env(path: Path, var: str, value: str) -> None:
    lines = path.read_text().splitlines()
    path.write_text(
        "".join(f"{var}={value}\n" if line.startswith(f"{var}=") else f"{line}\n" for line in lines)
    )


def test_configure_gives_a_linked_worktree_its_own_ports_and_stack(tmp_path: Path, registry: Path):
    main, worktree = checkouts(tmp_path)

    worktree_env.configure(main, "project")
    worktree_env.configure(worktree, "project")

    env = (worktree / ".env").read_text()
    assert env.startswith(f"# worktree slot: 1 of {worktree.resolve()} (ports ")
    assert worktree_env.parse_env(env) == {
        "WEB_DEV_PORT": "48100",
        "SITE_URL": "http://localhost:48100/",
        "STACK_NAME": "project_wt1_feature",
    }
    assert (main / ".env").read_text() == MAIN_ENV
    assert len(list(registry.glob("*.json"))) == 2


def test_configure_moves_its_own_urls_and_keeps_those_set_by_hand(tmp_path: Path, registry: Path):
    _, worktree = checkouts(tmp_path)
    env_file = worktree / ".env"
    worktree_env.configure(worktree, "project")

    for port in ("48150", "48160"):
        set_in_env(env_file, "WEB_DEV_PORT", port)
        worktree_env.configure(worktree, "project")
        assert (
            worktree_env.parse_env(env_file.read_text())["SITE_URL"] == f"http://localhost:{port}/"
        )

    set_in_env(env_file, "SITE_URL", "https://tunnel.example/")
    set_in_env(env_file, "WEB_DEV_PORT", "48170")
    worktree_env.configure(worktree, "project")
    assert worktree_env.parse_env(env_file.read_text())["SITE_URL"] == "https://tunnel.example/"


def test_configure_records_no_ports_when_env_cannot_be_written(
    tmp_path: Path, registry: Path, monkeypatch: pytest.MonkeyPatch
):
    main, worktree = checkouts(tmp_path)
    replace_file = worktree_env.replace_file

    def failing_for_env(path: Path, text: str) -> None:
        if path.name == ".env":
            raise OSError("read-only")
        replace_file(path, text)

    monkeypatch.setattr(worktree_env, "replace_file", failing_for_env)
    worktree_env.configure(main, "project")
    with pytest.raises(OSError):
        worktree_env.configure(worktree, "project")

    assert [json.loads(file.read_text())["checkout"] for file in registry.glob("*.json")] == [
        str(main.resolve())
    ]
