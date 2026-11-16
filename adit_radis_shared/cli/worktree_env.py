"""Give a git worktree of a project its own host ports and compose stack.

Claude Code copies the main checkout's .env into each worktree it creates
(.worktreeinclude), so without this the CLI would run a worktree's stack as the
main checkout's compose project, on its database and host ports.

Each linked worktree gets a slot N >= 1; the main checkout is slot 0. Every host
port docker-compose.dev.yml publishes becomes the main checkout's value
+ N * PORT_STEP, and STACK_NAME becomes <project>_wt<N>_<worktree>. The slot is recorded at the top
of the worktree's .env, with the worktree's path, so a copy of that .env elsewhere
is not taken for the slot's owner. Later runs keep what the worktree's .env sets
apart from the main checkout's values, ports and names alike, and only fill in the
rest; a worktree set up by hand before keeps its own the same way. --slot rewrites
them all. In the main checkout nothing changes. A linked worktree git can't read
stops the command instead, since its .env is still the main checkout's.

A new worktree takes the first slot that no other worktree of the repository holds
and none of whose ports is in use at that moment; it keeps that slot afterwards.
Runs take turns on a lock in the repository's git common directory, so worktrees
set up at once get different slots.

commands.worktree_guard runs configure() before every CLI command;
`uv run cli worktree-env --slot N` picks the slot by hand.
"""

import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

ENV_EXAMPLE = "example.env"

PORT_STEP = 100
MAX_SLOT = 50

MARKER = re.compile(r"^# worktree slot: (\d+) of (.+) \(ports ")
MARKER_LINE = re.compile(r"^# worktree slot: ")
ASSIGNMENT = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=(.*?)\r?$")
# A host port docker-compose.dev.yml publishes, "- ${VAR:-8000}:8000", with the
# default that applies when .env leaves VAR unset.
PUBLISHED_PORT = re.compile(r"^\s*-\s*[\"']?\$\{(\w+):-(\d+)\}:", re.MULTILINE)


def dev_ports(root: Path) -> dict[str, int]:
    """Every host port the development stack publishes, by its variable in .env."""
    text = (root / "docker-compose.dev.yml").read_text(encoding="utf-8")
    return {var: int(port) for var, port in PUBLISHED_PORT.findall(text)}


def names(project: str, worktree: str, slot: int) -> dict[str, str]:
    # The compose project the CLI runs (CommandHelper.get_stack_name).
    return {"STACK_NAME": f"{project}_wt{slot}_{worktree}"}


def say(*parts: object) -> None:
    # Messages go to stderr, so the output of the command this runs before
    # stays pipeable.
    print(*parts, file=sys.stderr)


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def worktree_roots(cwd: Path) -> list[Path]:
    """All worktrees of the repository, the main checkout first.

    Empty for a bare repository, which has no main checkout to take ports from.
    """
    entries = git("worktree", "list", "--porcelain", cwd=cwd).split("\n\n")
    if "bare" in entries[0].splitlines():
        return []
    return [Path(entry.splitlines()[0].removeprefix("worktree ")).resolve() for entry in entries]


def parse_env(text: str) -> dict[str, str]:
    """Raw values by name; like dotenv, a later assignment wins."""
    env: dict[str, str] = {}
    for line in text.splitlines():
        if match := ASSIGNMENT.match(line):
            env[match[1]] = match[2].strip()
    return env


def unquote(value: str) -> str:
    """The value as dotenv reads it: inside its quotes, or before an inline comment."""
    if value and value[0] in "\"'" and (end := value.find(value[0], 1)) != -1:
        return value[1:end]
    return value.split(" #", 1)[0].strip()


def port_value(env: dict[str, str], var: str, default: int) -> int:
    try:
        return int(unquote(env.get(var, "")))
    except ValueError:
        return default


def marker(env_file: Path) -> tuple[int, Path] | None:
    """The slot recorded in `env_file`, and the checkout it was recorded for."""
    if not env_file.is_file():
        return None
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if MARKER_LINE.match(line):
            match = MARKER.match(line)
            return (int(match[1]), Path(match[2])) if match else (0, Path())
    return None


def own_slot(checkout: Path) -> int | None:
    """The slot `checkout` holds; None for a .env copied from another checkout."""
    found = marker(checkout / ".env")
    return found[0] if found and found[1] == checkout else None


def in_use(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.2):
            return True
    except OSError:
        return False


def shifted(base: dict[str, int], slot: int) -> dict[str, int]:
    return {var: port + slot * PORT_STEP for var, port in base.items()}


@contextmanager
def repo_lock(common_dir: Path) -> Iterator[None]:
    """Hold the repository's lock while this run picks a slot and writes .env.

    Two worktrees set up at once, as parallel agents do, would otherwise both
    see the same slot as free.
    """
    path = common_dir / "worktree-env.lock"
    try:
        lock = path.open("a")
    except OSError as error:  # e.g. a read-only git directory
        say(f"warning: could not lock {path}: {error}")
        yield
        return
    with lock:
        try:
            if sys.platform == "win32":
                import msvcrt

                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)  # gives up after 10 s
            else:
                import fcntl

                fcntl.flock(lock, fcntl.LOCK_EX)
        except OSError as error:  # e.g. ENOLCK on a network filesystem
            say(f"warning: could not lock {path}: {error}")
        yield


def replace_file(path: Path, text: str) -> None:
    """Write `text` to `path` through a temporary file, so no reader sees half of it."""
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
    try:
        tmp_path.write_text(text, encoding="utf-8")
        if path.exists():
            shutil.copymode(path, tmp_path)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)  # a no-op once the replace has moved it


def clashes(base: dict[str, int], slot: int, taken: set[int]) -> set[int]:
    """Ports of `slot` that the main checkout or a taken slot also publishes.

    Two dev ports a multiple of PORT_STEP apart meet in some pair of slots,
    e.g. 80 at slot 10 and 1080 at slot 0.
    """
    others = {port for other in {0, *taken} for port in shifted(base, other).values()}
    return set(shifted(base, slot).values()) & others


def choose_slot(base: dict[str, int], taken: set[int]) -> int:
    open_slots = [
        slot
        for slot in range(1, MAX_SLOT + 1)
        if slot not in taken and not clashes(base, slot, taken)
    ]
    for slot in open_slots:
        busy = [port for port in shifted(base, slot).values() if in_use(port)]
        if not busy:
            return slot
        say(f"slot {slot}: ports {busy} are in use, trying the next one")
    sys.exit(f"error: no free slot below {MAX_SLOT + 1}")


def render(text: str, slot: int, root: Path, updates: dict[str, str]) -> str:
    """Apply `updates` to .env text in place, keeping its comments and order.

    The last assignment of a variable is replaced; a variable that is only
    present commented out is uncommented; any other is appended.
    """
    lines = [line for line in text.splitlines(keepends=True) if not MARKER_LINE.match(line)]
    appended = []
    for var, value in updates.items():
        assigned = [
            i for i, line in enumerate(lines) if (m := ASSIGNMENT.match(line)) and m[1] == var
        ]
        commented = re.compile(rf"^\s*#\s*{var}\s*=")
        if assigned:
            index = assigned[-1]
        elif found := [i for i, line in enumerate(lines) if commented.match(line)]:
            index = found[0]
        else:
            appended.append(f"{var}={value}\n")
            continue
        lines[index] = f"{var}={value}\n"
    if appended:
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines += ["\n# Worktree (uv run cli worktree-env)\n", *appended]
    header = (
        f"# worktree slot: {slot} of {root} (ports are the main checkout's"
        f" + {slot * PORT_STEP}; written by uv run cli worktree-env)\n"
    )
    return header + "".join(lines)


def configure(root: Path, project: str, requested: int | None = None) -> None:
    """Give `root` its own ports and names if it is a linked worktree.

    `project` names the stack (<project>_wt<N>_<worktree>); `requested` is a slot
    to use instead of the next free one.
    """
    try:
        root = Path(git("rev-parse", "--show-toplevel", cwd=root)).resolve()
    except (OSError, subprocess.CalledProcessError) as error:
        detail = str(getattr(error, "stderr", None) or error).strip()
        if (root / ".git").is_file():
            # A linked worktree (its .git file points at a path missing here, or git
            # refuses its owner) still has the main checkout's .env, so its commands
            # would reach the main checkout's stack and database.
            sys.exit(
                f"error: git can't read this worktree ({detail}), so its ports and stack"
                " name can't be set up, and its commands would reach the main checkout's"
                " stack. Make git read it first: `git worktree repair <path>` from the main"
                " checkout after a move, `git config --global --add safe.directory <path>`"
                " for a folder git refuses as another user's."
            )
        # A copy without git, or a main checkout git refuses to read: the command must
        # still run.
        say(f"Not a git checkout git can read ({detail}).")
        say("Worktree ports are not managed here.")
        return
    git_dir = Path(git("rev-parse", "--absolute-git-dir", cwd=root)).resolve()
    common_dir = (root / git("rev-parse", "--git-common-dir", cwd=root)).resolve()
    if git_dir == common_dir:  # the main checkout, also with a separate git dir or a submodule
        if requested is not None:
            sys.exit("error: --slot applies to linked worktrees; the main checkout keeps its ports")
        return
    with repo_lock(common_dir):
        _configure(root, project, requested)


def _configure(root: Path, project: str, requested: int | None) -> None:
    roots = worktree_roots(root)
    if not roots:
        say("Bare repository: worktree ports are not managed.")
        return
    main_root, *linked = roots
    if not (main_root / ".git").exists():
        # With a separate git dir or in a submodule, git lists the git dir instead.
        say(f"No main checkout at {main_root}: worktree ports are not managed.")
        return
    env_file = root / ".env"
    main_env_file = main_root / ".env"
    # Without a main .env, a worktree's .env comes from the example.
    base_file = main_env_file if main_env_file.is_file() else root / ENV_EXAMPLE
    main_env = parse_env(base_file.read_text(encoding="utf-8"))
    base = {var: port_value(main_env, var, default) for var, default in dev_ports(root).items()}

    if not env_file.is_file():
        shutil.copy2(base_file, env_file)
        say(f"Created .env from {base_file}")

    current = parse_env(env_file.read_text(encoding="utf-8"))
    copied = marker(env_file) is not None and own_slot(root) is None
    # What this worktree sets apart from the main checkout is its own.
    kept = {var: value for var, value in current.items() if value != main_env.get(var)}
    taken = {
        slot: other for other in linked if other != root and (slot := own_slot(other)) is not None
    }
    if requested is not None:
        if not 1 <= requested <= MAX_SLOT:
            sys.exit(f"error: --slot must be between 1 and {MAX_SLOT}")
        if requested in taken:
            sys.exit(f"error: slot {requested} is taken by {taken[requested]}")
        if clash := clashes(base, requested, set(taken)):
            sys.exit(f"error: slot {requested} would reuse ports {sorted(clash)}")
        slot = requested
        kept = {}
    elif (own := own_slot(root)) is not None and own not in taken:
        slot = own
    else:
        if marker(env_file):
            kept = {}  # a copy of another worktree's .env, or a slot held twice
        slot = choose_slot(base, set(taken))

    ports = {var: port_value(kept, var, port) for var, port in shifted(base, slot).items()}
    # Short enough for a DNS label (<service>.<project>.internal) with any suffix.
    worktree = re.sub(r"[^a-z0-9_-]+", "-", root.name.lower())[:32].strip("-_")
    updates = {var: str(port) for var, port in ports.items()}
    # The slot keeps the names apart where worktree directory names coincide.
    named = names(project, worktree or "worktree", slot)
    updates |= {var: kept.get(var, value) for var, value in named.items()}
    # The names in a copy are another worktree's, so nothing of this one's is left.
    if not copied and (
        renamed := [
            f"{var}={current[var]}"
            for var in named
            if current.get(var) not in (None, updates[var], main_env.get(var))
        ]
    ):
        say(
            f"note: {', '.join(renamed)} change; what still runs under the old names"
            " keeps its containers, ports and volumes until you stop it"
        )

    text = env_file.read_text(encoding="utf-8")
    rendered = render(text, slot, root, updates)
    if rendered == text:
        say(f"Worktree slot {slot}: .env is up to date.")
        return
    replace_file(env_file, rendered)
    say(f"Worktree slot {slot}; .env now sets:")
    for var, value in updates.items():
        say(f"  {var}={value}")
