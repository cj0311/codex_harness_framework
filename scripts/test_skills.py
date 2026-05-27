"""Validate repository-local Codex skill metadata."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SKILLS = (
    "codex-harness-planner",
    "codex-harness-review",
)


def _frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    end = text.index("\n---", 4)
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def test_codex_skills_have_required_frontmatter():
    for name in SKILLS:
        skill = ROOT / ".codex" / "skills" / name / "SKILL.md"
        fields = _frontmatter(skill)

        assert fields["name"] == name
        assert fields["description"]
        assert "TODO" not in fields["description"]


def test_codex_skills_have_openai_metadata():
    for name in SKILLS:
        metadata = ROOT / ".codex" / "skills" / name / "agents" / "openai.yaml"
        text = metadata.read_text(encoding="utf-8")

        assert "display_name:" in text
        assert "short_description:" in text
        assert "default_prompt:" in text
