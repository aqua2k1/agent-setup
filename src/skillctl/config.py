"""Read and write the skill registry without losing retained TOML comments."""

import os
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Mapping

import tomlkit
from tomlkit.exceptions import TOMLKitError
from tomlkit.items import InlineTable, Table

from .contracts import SkillError, SkillSpec

_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
_FIELDS = frozenset({"name", "repo", "path", "ref", "frontmatter"})


def valid_name(name: object) -> bool:
    return isinstance(name, str) and len(name) <= 64 and _NAME.fullmatch(name) is not None


def valid_path(path: object) -> bool:
    return (
        isinstance(path, str)
        and bool(path)
        and "\\" not in path
        and "\x00" not in path
        and not PurePosixPath(path).is_absolute()
        and ".." not in path.split("/")
    )


def _plain(value):
    """Unwrap TOMLKit containers and scalars, including nested fields."""
    return value.unwrap() if hasattr(value, "unwrap") else value


def _same_value(left, right) -> bool:
    left, right = _plain(left), _plain(right)
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(
            _same_value(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_value(a, b) for a, b in zip(left, right)
        )
    return type(left) is type(right) and left == right


def _validate_spec(name: str, spec: SkillSpec) -> None:
    if not valid_name(name):
        raise SkillError(f"Invalid skill name: {name!r}")
    if not isinstance(spec, SkillSpec):
        raise SkillError(f"Invalid specification for {name!r}")
    if not isinstance(spec.repo, str) or not spec.repo.strip():
        raise SkillError(f"Invalid repository for {name!r}")
    if not valid_path(spec.path):
        raise SkillError(f"Invalid path for {name!r}")
    if spec.ref is not None and (not isinstance(spec.ref, str) or not spec.ref):
        raise SkillError(f"Invalid ref for {name!r}")
    if spec.repo == "local" and (spec.path != "." or spec.ref is not None):
        raise SkillError(f"Local skill {name!r} cannot specify a Git path or ref")
    if not isinstance(spec.frontmatter, Mapping):
        raise SkillError(f"Invalid frontmatter for {name!r}")
    for key in spec.frontmatter:
        if not isinstance(key, str):
            raise SkillError(f"Invalid frontmatter override for {name!r}: {key!r}")


def _parse(document: object) -> dict[str, SkillSpec]:
    if not isinstance(document, Mapping) or set(document) - {"skills"}:
        raise SkillError("Configuration must contain only a skills array")
    skills = document.get("skills", [])
    if not isinstance(skills, list):
        raise SkillError("skills must be an array; use [[skills]] with an explicit name")
    result: dict[str, SkillSpec] = {}
    for entry in skills:
        if not isinstance(entry, Mapping):
            raise SkillError("Each skills entry must be a TOML table")
        name = entry.get("name")
        if not valid_name(name):
            raise SkillError(f"Invalid or missing skill name: {name!r}")
        if name in result:
            raise SkillError(f"Duplicate skill name: {name!r}")
        if set(entry) - _FIELDS:
            raise SkillError(f"Unknown fields in skill {name!r}")
        frontmatter = entry.get("frontmatter", {})
        if not isinstance(frontmatter, Mapping):
            raise SkillError(f"Invalid frontmatter for {name!r}")
        spec = SkillSpec(
            repo=entry.get("repo"),
            path=entry.get("path", "."),
            ref=entry.get("ref"),
            frontmatter=_plain(frontmatter),
        )
        _validate_spec(name, spec)
        result[name] = spec
    return result


def _read_document(path: Path):
    try:
        return tomlkit.parse(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return tomlkit.document()
    except (OSError, UnicodeError, TOMLKitError, ValueError) as exc:
        raise SkillError(f"Cannot read config {path}: {exc}") from exc


def load_config(path: Path) -> dict[str, SkillSpec]:
    """Load a TOML skill registry; absent files represent empty registries."""
    return _parse(_read_document(path))


def save_config(path: Path, specs: Mapping[str, SkillSpec]) -> None:
    """Atomically update the registry, retaining comments on surviving entries."""
    try:
        desired = dict(specs)
        for name, spec in desired.items():
            _validate_spec(name, spec)
        document = _read_document(path)
        _parse(document)  # Never silently discard malformed existing configuration.
        retained = {
            entry["name"]: entry for entry in document.get("skills", [])
            if entry["name"] in desired
        }
        names = list(retained) + [name for name in desired if name not in retained]
        skills = tomlkit.aot()
        for name in names:
            spec = desired[name]
            original = retained.get(name)
            if isinstance(original, Table):
                entry = original
            else:
                entry = tomlkit.table()
                if original is not None:
                    entry.update(original)
            if "name" not in entry:
                entry["name"] = name
            if entry.get("repo") != spec.repo:
                entry["repo"] = spec.repo
            # Leave unchanged defaults (and their comments) alone.
            if entry.get("path", ".") != spec.path:
                if spec.path == ".":
                    entry.pop("path", None)
                else:
                    entry["path"] = spec.path
            if entry.get("ref") != spec.ref:
                if spec.ref is None:
                    entry.pop("ref", None)
                else:
                    entry["ref"] = spec.ref
            if not spec.frontmatter:
                entry.pop("frontmatter", None)
            else:
                previous = entry.get("frontmatter")
                if isinstance(previous, InlineTable):
                    overrides = previous
                else:
                    overrides = tomlkit.inline_table()
                    if previous is not None:
                        comment = previous.trivia.comment
                        if comment:
                            overrides.comment(comment.lstrip("#").strip())
                    entry["frontmatter"] = overrides
                for key in list(overrides):
                    if key not in spec.frontmatter:
                        del overrides[key]
                for key, value in spec.frontmatter.items():
                    if key not in overrides or not _same_value(overrides[key], value):
                        overrides[key] = value
            skills.append(entry)
        document["skills"] = skills if names else tomlkit.array()
        content = tomlkit.dumps(document)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
                delete=False,
            ) as temp:
                temp_name = temp.name
                temp.write(content)
                temp.flush()
                os.fsync(temp.fileno())
            os.replace(temp_name, path)
        finally:
            if temp_name is not None and os.path.exists(temp_name):
                os.unlink(temp_name)
    except SkillError:
        raise
    except (OSError, UnicodeError, TOMLKitError, ValueError, TypeError) as exc:
        raise SkillError(f"Cannot save config {path}: {exc}") from exc
