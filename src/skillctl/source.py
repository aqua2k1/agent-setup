"""Fetch Git trees as data, without a worktree, checkout filters, or hooks."""

import os
import re
import selectors
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from .config import valid_path
from .contracts import FetchedSkill, InvalidSkill, SkillError, SkillSpec
from .render import skill_name

_TIMEOUT = 60
_MAX_OUTPUT = 8 * 1024 * 1024
_MAX_FILE = 16 * 1024 * 1024
_MAX_TREE = 128 * 1024 * 1024
# Large asset-based skills (e.g. icon libraries) can exceed 10,000 entries.
# Keep byte/depth limits in addition to this metadata-count bound.
_MAX_ENTRIES = 20000
_HEX = re.compile(r"[0-9a-fA-F]{40}(?:[0-9a-fA-F]{24})?\Z")
_SCP = re.compile(r"(?:[a-zA-Z0-9_.-]+@)?[a-zA-Z0-9_.-]+:[^\s]+\Z")


def _repository(repo: str) -> str:
    if not isinstance(repo, str) or not repo or "\x00" in repo or any(ord(c) < 32 for c in repo):
        raise SkillError("Invalid repository URL")
    if repo.startswith("/"):
        return repo
    if repo.startswith("-"):
        raise SkillError("Option-like repository URL")
    if "://" not in repo:
        if _SCP.fullmatch(repo):
            host, remote_path = repo.split(":", 1)
            if (
                host.split("@")[-1].startswith("-")
                or remote_path.startswith(("-", ":"))
                or re.fullmatch(r"[A-Za-z0-9_./~+-]+", remote_path) is None
            ):
                raise SkillError("Unsafe SSH repository")
            return repo
        raise SkillError("Unsupported repository URL")
    try:
        url = urlsplit(repo)
        if url.scheme not in {"https", "ssh"} or not url.hostname or not url.path:
            raise ValueError("Unsupported repository URL")
        if url.hostname.startswith("-") or url.query or url.fragment:
            raise ValueError("Invalid repository URL")
        if url.port is not None and not 1 <= url.port <= 65535:
            raise ValueError("Invalid port")
        if url.path.lstrip("/").startswith("-"):
            raise ValueError("Option-like repository path")
        if url.scheme == "ssh" and (
            url.password is not None
            or (url.username is not None and re.fullmatch(r"[A-Za-z0-9_.-]+", url.username) is None)
            or re.fullmatch(r"/[A-Za-z0-9_./~+-]+", url.path) is None
        ):
            raise ValueError("Unsafe SSH repository")
    except ValueError as exc:
        raise SkillError(f"Invalid repository URL: {exc}") from exc
    return repo


def _ref(ref: str | None) -> str:
    if ref is None:
        return "HEAD"
    if not isinstance(ref, str) or not ref or ref.startswith("-"):
        raise SkillError("Invalid Git ref")
    if _HEX.fullmatch(ref):
        return ref
    # Leave legal Unicode and punctuation to Git's own refname validator; reject
    # refspec/revision operators and option-like refs before invoking Git.
    if (
        any(ord(char) < 33 or ord(char) == 127 for char in ref)
        or any(char in ref for char in ":~^?*[\\")
        or "@{" in ref
        or ref == "@"
        or (ref.startswith("refs/") and not ref.startswith(("refs/heads/", "refs/tags/")))
    ):
        raise SkillError("Invalid Git ref")
    return ref


def _git(args: list[str], directory: Path, limit: int = _MAX_OUTPUT, allow_file: bool = False) -> bytes:
    # Ignore caller-supplied Git configuration, helpers, and executable overrides.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": os.devnull,
                "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"})
    command = [
        "git", "-c", f"core.hooksPath={os.devnull}", "-c", "gc.auto=0",
        "-c", "uploadpack.packObjectsHook=",
        "-c", "protocol.allow=never", "-c", "protocol.https.allow=always",
        "-c", "protocol.ssh.allow=always",
        "-c", f"protocol.file.allow={'always' if allow_file else 'never'}",
        *args,
    ]
    try:
        with subprocess.Popen(command, cwd=directory, env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
            selector = selectors.DefaultSelector()
            try:
                selector.register(process.stdout, selectors.EVENT_READ)
                selector.register(process.stderr, selectors.EVENT_READ)
                output = bytearray()
                errors = bytearray()
                deadline = time.monotonic() + _TIMEOUT
                while selector.get_map():
                    ready = selector.select(max(0, deadline - time.monotonic()))
                    if not ready:
                        raise SkillError("Git command timed out")
                    for event, _ in ready:
                        chunk = os.read(event.fileobj.fileno(), 65536)
                        if not chunk:
                            selector.unregister(event.fileobj)
                        elif event.fileobj is process.stdout:
                            output.extend(chunk)
                            if len(output) > limit:
                                raise SkillError("Git output exceeds size limit")
                        elif len(errors) < 32768:
                            errors.extend(chunk[:32768 - len(errors)])
                if process.wait(timeout=max(0.01, deadline - time.monotonic())):
                    raise SkillError(errors.decode("utf-8", "replace").strip() or "Git command failed")
                return bytes(output)
            finally:
                selector.close()
                if process.poll() is None:
                    process.kill()
                    process.wait()
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SkillError(f"Cannot run Git: {exc}") from exc


def _sha(data: bytes) -> str:
    try:
        value = data.decode("ascii", "strict").strip()
    except UnicodeError as exc:
        raise InvalidSkill("Invalid Git object identifier") from exc
    if not _HEX.fullmatch(value):
        raise InvalidSkill("Invalid Git object identifier")
    return value.lower()


def _entries(raw: bytes):
    for record in raw.split(b"\x00"):
        if not record:
            continue
        try:
            header, name = record.split(b"\t", 1)
            mode, kind, sha = header.decode("ascii").split(" ")
            filename = name.decode("utf-8", "strict")
            if not filename or filename in {".", ".."} or "/" in filename or "\\" in filename or "\x00" in filename:
                raise ValueError("Unsafe Git entry name")
            yield mode, kind, _sha(sha.encode("ascii")), filename
        except (UnicodeError, ValueError) as exc:
            raise InvalidSkill(f"Invalid Git tree entry: {exc}") from exc


def _tree_entries(tree: str, gitdir: Path):
    return list(_entries(_git(["-C", str(gitdir), "ls-tree", "-z", tree], gitdir)))


def _extract(tree: str, destination: Path, gitdir: Path) -> None:
    count = 0
    total = 0

    def visit(tree_id: str, directory: Path, depth: int) -> None:
        nonlocal count, total
        if depth > 64:
            raise InvalidSkill("Skill tree exceeds maximum depth")
        for mode, kind, sha, name in _tree_entries(tree_id, gitdir):
            count += 1
            if count > _MAX_ENTRIES:
                raise InvalidSkill("Skill tree has too many entries")
            if name.casefold() == ".git":
                raise InvalidSkill("Skill tree contains .git")
            if mode == "040000" and kind == "tree":
                child = directory / name
                child.mkdir()
                visit(sha, child, depth + 1)
            elif mode in {"100644", "100755"} and kind == "blob":
                raw_size = _git(["-C", str(gitdir), "cat-file", "-s", sha], gitdir, 128)
                try:
                    size = int(raw_size)
                except ValueError as exc:
                    raise InvalidSkill("Invalid Git blob size") from exc
                if size > _MAX_FILE or total + size > _MAX_TREE:
                    raise InvalidSkill("Skill tree exceeds size limit")
                data = _git(["-C", str(gitdir), "cat-file", "blob", sha], gitdir, size)
                if len(data) != size:
                    raise InvalidSkill("Git blob changed during fetch")
                total += size
                target = directory / name
                with target.open("xb") as stream:
                    stream.write(data)
                target.chmod(0o755 if mode == "100755" else 0o644)
            else:
                raise InvalidSkill(f"Unsupported Git entry (symlink/submodule): {name}")

    visit(tree, destination, 0)


def fetch_skill(spec: SkillSpec, workspace: Path) -> FetchedSkill:
    """Fetch one subtree into an empty caller-owned workspace; never check it out."""
    if not isinstance(spec, SkillSpec):
        raise SkillError("Invalid skill specification")
    repo = _repository(spec.repo)
    ref = _ref(spec.ref)
    if not valid_path(spec.path):
        raise SkillError("Invalid skill subpath")
    try:
        if workspace.is_symlink() or not workspace.is_dir() or any(workspace.iterdir()):
            raise SkillError("Workspace must be an existing empty directory")
    except OSError as exc:
        raise SkillError(f"Cannot access workspace: {exc}") from exc
    destination = workspace / "skill"
    success = False
    try:
        if ref != "HEAD" and not _HEX.fullmatch(ref):
            qualified = ref if ref.startswith("refs/") else f"refs/heads/{ref}"
            _git(["check-ref-format", qualified], workspace, 128)
        with tempfile.TemporaryDirectory(prefix=".git-objects-", dir=workspace) as scratch:
            gitdir = Path(scratch) / "repo.git"
            _git(["init", "--bare", "-q", "--", str(gitdir)], workspace)
            _git(["-C", str(gitdir), "fetch", "--no-tags", "--depth=1", "--", repo, ref], workspace,
                 allow_file=repo.startswith("/"))
            commit = _sha(_git(["-C", str(gitdir), "rev-parse", "--verify", "FETCH_HEAD^{commit}"], workspace, 128))
            tree = _sha(_git(["-C", str(gitdir), "rev-parse", "--verify", f"{commit}^{{tree}}"], workspace, 128))
            parts = [] if spec.path == "." else [part for part in spec.path.split("/") if part not in {"", "."}]
            for part in parts:
                if part == ".git" or part.casefold() == ".git":
                    raise InvalidSkill("Cannot select .git")
                match = next((entry for entry in _tree_entries(tree, gitdir) if entry[3] == part), None)
                if match is None or match[0] != "040000" or match[1] != "tree":
                    raise InvalidSkill(f"Missing skill directory: {spec.path}")
                tree = match[2]
            destination.mkdir()
            _extract(tree, destination, gitdir)
        metadata = destination / "SKILL.md"
        if not metadata.is_file():
            raise InvalidSkill("Skill root is missing SKILL.md")
        try:
            skill_name(metadata.read_text(encoding="utf-8"))
        except UnicodeError as exc:
            raise InvalidSkill("SKILL.md is not valid UTF-8") from exc
        success = True
        return FetchedSkill(destination, commit)
    except (OSError, UnicodeError, ValueError) as exc:
        raise SkillError(f"Cannot fetch skill: {exc}") from exc
    finally:
        # The caller owns the workspace; do not leave an incomplete skill there.
        if not success and destination.is_dir():
            shutil.rmtree(destination)
