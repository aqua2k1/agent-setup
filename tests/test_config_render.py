import tomllib

import pytest

from skillctl.config import load_config, save_config
from skillctl.contracts import SkillError, SkillSpec
from skillctl.render import render_skill, skill_name

from conftest import markdown


def test_config_missing_roundtrip_and_defaults(tmp_path):
    path = tmp_path / "new" / "config.toml"
    assert load_config(path) == {}
    specs = {
        "demo": SkillSpec("/tmp/repository", "catalog/demo", "v1", {"disable-model-invocation": False}),
        "other": SkillSpec("https://example.invalid/repo.git"),
    }
    save_config(path, specs)
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    assert list(document) == ["skills"]
    assert [entry["name"] for entry in document["skills"]] == ["demo", "other"]
    assert document["skills"][0]["frontmatter"] == {"disable-model-invocation": False}
    assert "frontmatter = {" in path.read_text(encoding="utf-8")
    assert list(load_config(path)) == ["demo", "other"]
    assert load_config(path) == specs
    path.write_text('[[skills]]\nname = "demo"\nrepo = "/tmp/repository"\n', encoding="utf-8")
    assert load_config(path) == {"demo": SkillSpec("/tmp/repository")}


def test_local_config_roundtrip_and_defaults(tmp_path):
    path = tmp_path / "config.toml"
    specs = {"personal": SkillSpec("local", frontmatter={"disable-model-invocation": False})}
    save_config(path, specs)
    document = tomllib.loads(path.read_text(encoding="utf-8"))
    assert len(document["skills"]) == 1
    assert document["skills"][0]["name"] == "personal"
    assert document["skills"][0]["frontmatter"] == {"disable-model-invocation": False}
    assert "frontmatter = {" in path.read_text(encoding="utf-8")
    assert load_config(path) == specs
    path.write_text('[[skills]]\nname = "personal"\nrepo = "local"\n', encoding="utf-8")
    assert load_config(path) == {"personal": SkillSpec("local")}


def test_save_preserves_comments_on_retained_entries(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text(
        '# user heading\n[[skills]]\nname = "other"\n# other note\nrepo = "/tmp/b"\n'
        '\n[[skills]]\nname = "demo"\n# important note\nrepo = "/tmp/a" # keep this note\n'
        'frontmatter = { disable-model-invocation = false } # invocation note\n',
        encoding="utf-8",
    )
    specs = load_config(path)
    assert list(specs) == ["other", "demo"]
    save_config(path, {**specs, "third": SkillSpec("/tmp/c")})
    text = path.read_text(encoding="utf-8")
    for comment in ("# user heading", "# important note", "# keep this note", "# other note", "# invocation note"):
        assert comment in text
    assert [entry["name"] for entry in tomllib.loads(text)["skills"]] == ["other", "demo", "third"]
    assert tomllib.loads(text)["skills"][1]["frontmatter"] == {"disable-model-invocation": False}
    assert "frontmatter = {" in text
    assert list(load_config(path)) == ["other", "demo", "third"]
    assert load_config(path)["third"] == SkillSpec("/tmp/c")


def test_empty_config_document_and_save(tmp_path):
    path = tmp_path / "config.toml"
    for text in ("", "skills = []\n"):
        path.write_text(text, encoding="utf-8")
        assert load_config(path) == {}
    save_config(path, {})
    assert tomllib.loads(path.read_text(encoding="utf-8")) == {"skills": []}
    assert load_config(path) == {}


def test_legacy_mapping_config_is_rejected(tmp_path):
    path = tmp_path / "config.toml"
    path.write_text('[skills.demo]\nrepo = "/tmp/x"\n', encoding="utf-8")
    with pytest.raises(SkillError):
        load_config(path)


@pytest.mark.parametrize(
    "text",
    [
        "not TOML = [",
        'other = "unsupported"\n',
        '[[skills]]\nname = "Bad"\nrepo = "/tmp/x"\n',
        '[[skills]]\nname = "a--b"\nrepo = "/tmp/x"\n',
        f'[[skills]]\nname = {"a" * 65!r}\nrepo = "/tmp/x"\n',
        '[[skills]]\nrepo = "/tmp/x"\n',
        '[[skills]]\nname = 1\nrepo = "/tmp/x"\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\n[[skills]]\nname = "demo"\nrepo = "/tmp/y"\n',
        'skills = [1]\n',
        'skills = ["demo"]\n',
        'skills = "demo"\n',
        '[[skills]]\nname = "demo"\n',
        '[[skills]]\nname = "demo"\nrepo = ""\n',
        '[[skills]]\nname = "demo"\nrepo = 5\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\nextra = 1\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\npath = "../secret"\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\npath = "/absolute"\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\npath = "a\\\\b"\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\npath = "a/./../b"\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\nref = 17\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\nfrontmatter = { disable-model-invocation = "false" }\n',
        '[[skills]]\nname = "demo"\nrepo = "/tmp/x"\nfrontmatter = { other = true }\n',
        '[[skills]]\nname = "demo"\nrepo = "local"\npath = "catalog/demo"\n',
        '[[skills]]\nname = "demo"\nrepo = "local"\nref = "main"\n',
    ],
)
def test_bad_config_is_rejected(tmp_path, text):
    path = tmp_path / "config.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(SkillError):
        load_config(path)


def test_render_explicit_true_false_inheritance_and_idempotence():
    original = markdown(invocation=True, body="\n# Body\n  exact spacing  \n")
    false = render_skill(original, {"disable-model-invocation": False})
    assert "disable-model-invocation: false" in false
    assert false.endswith("\n# Body\n  exact spacing  \n")
    assert render_skill(false, {"disable-model-invocation": False}) == false
    assert "disable-model-invocation: true" in render_skill(false, {"disable-model-invocation": True})
    assert "disable-model-invocation: true" in render_skill(original, {})
    assert skill_name(false) == "demo"


def test_render_accepts_frontmatter_ending_at_eof_without_newline():
    original = "---\nname: demo\ndescription: Valid\ndisable-model-invocation: true\n---"
    assert skill_name(original) == "demo"
    rendered = render_skill(original, {"disable-model-invocation": False})
    assert skill_name(rendered) == "demo"
    assert "disable-model-invocation: false" in rendered
    assert render_skill(rendered, {"disable-model-invocation": False}) == rendered


def test_render_missing_upstream_field_can_be_added_and_inherited():
    original = "---\nname: demo\ndescription: Some text\nextra: retained\n---\nbody\n"
    assert "disable-model-invocation" not in render_skill(original, {})
    rendered = render_skill(original, {"disable-model-invocation": False})
    assert "disable-model-invocation: false" in rendered
    assert "extra: retained" in rendered
    assert rendered.endswith("body\n")
    assert render_skill(rendered, {"disable-model-invocation": False}) == rendered
    assert skill_name("\ufeff" + original) == "demo"


@pytest.mark.parametrize(
    "text",
    [
        "# Missing frontmatter\n",
        "prefix\n---\nname: demo\ndescription: text\n---\n",
        "---\nname: Bad_Name\ndescription: text\n---\n",
        "---\nname: demo\ndescription: '  '\n---\n",
        "---\nname: demo\ndescription: 123\n---\n",
        "---\nname: demo\ndescription: text\nname: other\n---\n",
        "---\nname: demo\ndescription: [broken\n---\n",
        "---\nname: demo\ndescription: text\ndisable-model-invocation: 'false'\n---\n",
        "---\nname: demo\ndescription: " + "x" * 1025 + "\n---\n",
    ],
)
def test_render_rejects_invalid_metadata(text):
    with pytest.raises(SkillError):
        render_skill(text, {})
    with pytest.raises(SkillError):
        skill_name(text)


@pytest.mark.parametrize("overrides", [{"unknown": True}, {"disable-model-invocation": "false"}])
def test_render_rejects_invalid_overrides(overrides):
    with pytest.raises(SkillError):
        render_skill(markdown(), overrides)
