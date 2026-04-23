"""Drift lints for the /visualgen skill.

These tests don't cover runtime behavior — they catch drift between the skill's
Markdown content and the server's actual tool surface / config constants. When
someone renames a tool or removes an aspect ratio from config.py, the skill
silently going stale is the failure mode we want to prevent.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / ".claude" / "skills" / "visualgen"

TEMPLATE_NAMES = [
    "hero-video",
    "hero-image",
    "background-loop",
    "product-shot",
    "illustration",
    "og-social-card",
]

REFERENCE_NAMES = ["prompt-anatomy", "cost-cheatsheet"]

SKILL_TOOL_NAMES = [
    "submit_video",
    "check_video",
    "list_videos",
    "generate_image",
    "list_images",
    "get_pricing",
]


def _read(path: Path) -> str:
    assert path.exists(), f"Missing: {path.relative_to(REPO)}"
    return path.read_text(encoding="utf-8")


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Parse a YAML-ish frontmatter block (name: value, description: value)."""
    assert text.startswith("---\n"), "Frontmatter must start with '---' on its own line"
    end = text.find("\n---\n", 4)
    assert end != -1, "Frontmatter must close with '---' on its own line"
    block = text[4:end]
    out: dict[str, str] = {}
    current_key: str | None = None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line[0].isalpha() and ":" in line:
            key, _, value = line.partition(":")
            current_key = key.strip()
            out[current_key] = value.strip()
        elif current_key is not None:
            out[current_key] = (out[current_key] + " " + line.strip()).strip()
    return out


def test_skill_md_exists_with_frontmatter() -> None:
    text = _read(SKILL_DIR / "SKILL.md")
    fm = _parse_frontmatter(text)
    assert fm.get("name") == "visualgen"
    desc = fm.get("description", "")
    assert desc.startswith("Use whenever"), f"description must start with 'Use whenever', got: {desc[:60]!r}"


@pytest.mark.parametrize("name", TEMPLATE_NAMES)
def test_template_exists_with_h1(name: str) -> None:
    text = _read(SKILL_DIR / "templates" / f"{name}.md")
    first_line = text.splitlines()[0]
    assert first_line.startswith("# "), f"Template {name} must start with an h1 heading"


@pytest.mark.parametrize("name", REFERENCE_NAMES)
def test_reference_exists_with_h1(name: str) -> None:
    text = _read(SKILL_DIR / "reference" / f"{name}.md")
    first_line = text.splitlines()[0]
    assert first_line.startswith("# "), f"Reference {name} must start with an h1 heading"


def test_skill_mentions_all_tool_names() -> None:
    """Every tool the skill names must exist in server.py."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    server_text = _read(REPO / "src" / "visualgen_mcp" / "server.py")
    for tool in SKILL_TOOL_NAMES:
        assert tool in skill_text, f"SKILL.md should mention tool {tool!r}"
        assert re.search(rf"^def {re.escape(tool)}\(", server_text, re.MULTILINE), (
            f"Tool {tool!r} named in skill does not exist as `def {tool}(` in server.py"
        )


def test_skill_aspect_ratios_match_config() -> None:
    """Every aspect ratio the skill names must be in config.py's allowlists."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    config_text = _read(REPO / "src" / "visualgen_mcp" / "config.py")
    for ratio in ["16:9", "9:16", "1:1", "4:3", "3:4"]:
        if ratio in skill_text:
            assert ratio in config_text, (
                f"Skill mentions aspect ratio {ratio!r} but it's not in config.py"
            )


def test_skill_video_tiers_match_config() -> None:
    """Every Veo tier name the skill mentions must match VIDEO_MODELS keys."""
    skill_text = _read(SKILL_DIR / "SKILL.md")
    for tier in ["lite", "fast", "standard"]:
        assert tier in skill_text, f"SKILL.md should mention tier {tier!r}"
    # The server's keys are the source of truth; if this changes, update the list above.
    from visualgen_mcp.config import VIDEO_MODELS

    assert set(VIDEO_MODELS.keys()) == {"lite", "fast", "standard"}
