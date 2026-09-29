"""Validate skill frontmatter and apply configured fields without touching its body."""

from datetime import time
from io import StringIO
from typing import Mapping

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .config import valid_name
from .contracts import InvalidSkill, SkillError


def _split(markdown: str) -> tuple[str, str, str, str]:
    if not isinstance(markdown, str):
        raise InvalidSkill("Skill markdown must be text")
    bom = "\ufeff" if markdown.startswith("\ufeff") else ""
    text = markdown[len(bom):]
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].rstrip("\r\n") != "---" or not lines[0].endswith(("\n", "\r")):
        raise InvalidSkill("SKILL.md must begin with YAML frontmatter")
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r\n") == "---":
            return bom, lines[0], "".join(lines[1:index]), "".join(lines[index:])
    raise InvalidSkill("SKILL.md has no closing frontmatter delimiter")


def _frontmatter(markdown: str):
    bom, opening, yaml_text, tail = _split(markdown)
    yaml = YAML(typ="rt")
    yaml.allow_duplicate_keys = False
    try:
        metadata = yaml.load(yaml_text)
    except (YAMLError, ValueError, TypeError) as exc:
        raise InvalidSkill(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(metadata, Mapping):
        raise InvalidSkill("Skill frontmatter must be a mapping")
    return bom, opening, metadata, tail, yaml


def _validate_metadata(metadata: Mapping) -> None:
    if not valid_name(metadata.get("name")):
        raise InvalidSkill("Skill frontmatter needs a valid name")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise InvalidSkill("Skill frontmatter needs a nonblank description (max 1024 characters)")


def _yaml_value(value):
    """YAML has no time-of-day scalar; encode TOML times as ISO strings."""
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _yaml_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_yaml_value(item) for item in value]
    return value


def _same_value(left, right) -> bool:
    """Avoid rewriting unchanged YAML, without conflating bools and numbers."""
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        return left.keys() == right.keys() and all(
            _same_value(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _same_value(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        return (isinstance(left, int) and isinstance(right, int) or
                isinstance(left, float) and isinstance(right, float)) and left == right
    return left == right


def render_skill(markdown: str, overrides: Mapping[str, object]) -> str:
    """Replace complete frontmatter fields, keeping the body byte-for-byte intact."""
    if not isinstance(overrides, Mapping):
        raise SkillError("Frontmatter overrides must be a mapping")
    for key in overrides:
        if not isinstance(key, str):
            raise SkillError(f"Invalid frontmatter override: {key!r}")
    bom, opening, metadata, tail, yaml = _frontmatter(markdown)
    original_name = metadata.get("name")
    if not valid_name(original_name):
        raise InvalidSkill("Skill frontmatter needs a valid name")
    if "name" in overrides and overrides["name"] != original_name:
        raise InvalidSkill("Frontmatter override cannot change the skill name")
    changes = {}
    for key, value in overrides.items():
        converted = _yaml_value(value)
        if key not in metadata or not _same_value(metadata[key], converted):
            changes[key] = converted
    metadata.update(changes)
    _validate_metadata(metadata)
    if not changes:
        return markdown
    output = StringIO()
    try:
        yaml.dump(metadata, output)
    except (YAMLError, ValueError, TypeError) as exc:
        raise InvalidSkill(f"Cannot render YAML frontmatter: {exc}") from exc
    # Preserve the original delimiter and body; only YAML content is rewritten.
    newline = "\r\n" if opening.endswith("\r\n") else "\n"
    generated = output.getvalue().replace("\n", newline)
    return bom + opening + generated + tail


def skill_name(markdown: str) -> str:
    """Validate a skill and return its declared name."""
    metadata = _frontmatter(markdown)[2]
    _validate_metadata(metadata)
    return metadata["name"]
