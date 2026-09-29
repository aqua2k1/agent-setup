"""Validate skill frontmatter and apply invocation overrides without touching its body."""

from io import StringIO
from typing import Mapping

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .config import valid_name
from .contracts import InvalidSkill, SkillError

_INVOCATION = "disable-model-invocation"


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


def _frontmatter(markdown: str, overrides: Mapping[str, bool]):
    bom, opening, yaml_text, tail = _split(markdown)
    yaml = YAML(typ="rt")
    yaml.allow_duplicate_keys = False
    try:
        metadata = yaml.load(yaml_text)
    except (YAMLError, ValueError, TypeError) as exc:
        raise InvalidSkill(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(metadata, Mapping):
        raise InvalidSkill("Skill frontmatter must be a mapping")
    if not valid_name(metadata.get("name")):
        raise InvalidSkill("Skill frontmatter needs a valid name")
    description = metadata.get("description")
    if not isinstance(description, str) or not description.strip() or len(description) > 1024:
        raise InvalidSkill("Skill frontmatter needs a nonblank description (max 1024 characters)")
    if _INVOCATION in metadata and _INVOCATION not in overrides and type(metadata[_INVOCATION]) is not bool:
        raise InvalidSkill("disable-model-invocation must be a boolean")
    return bom, opening, metadata, tail, yaml


def render_skill(markdown: str, overrides: Mapping[str, bool]) -> str:
    """Apply validated frontmatter overrides, keeping the body byte-for-byte intact."""
    if not isinstance(overrides, Mapping):
        raise SkillError("Frontmatter overrides must be a mapping")
    for key, value in overrides.items():
        if key != _INVOCATION or type(value) is not bool:
            raise SkillError(f"Invalid frontmatter override: {key!r}")
    bom, opening, metadata, tail, yaml = _frontmatter(markdown, overrides)
    if not overrides or (
        _INVOCATION in metadata and metadata[_INVOCATION] is overrides[_INVOCATION]
    ):
        return markdown
    metadata[_INVOCATION] = overrides[_INVOCATION]
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
    return _frontmatter(markdown, {})[2]["name"]
