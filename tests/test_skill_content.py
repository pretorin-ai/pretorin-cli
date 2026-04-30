"""Smoke tests for the bundled `pretorin` skill content.

The skill ships at ``pretorin-skill/SKILL.md`` and is what
``pretorin skill install`` copies into ``~/.claude/skills/pretorin/`` and
the equivalent codex path. These tests pin the high-value invariants —
frontmatter parses, the recipe surface is documented, the legacy
``pretorin scan`` references stay deleted.

The full hand-curated SKILL.md content review is the human's job. This file
catches drift, not prose quality.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

_SKILL_MD = Path(__file__).resolve().parent.parent / "pretorin-skill" / "SKILL.md"


@pytest.fixture(scope="module")
def skill_text() -> str:
    return _SKILL_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def skill_frontmatter(skill_text: str) -> dict[str, object]:
    """Parse the YAML frontmatter block at the top of SKILL.md."""
    if not skill_text.startswith("---\n"):
        pytest.fail("SKILL.md must start with a YAML frontmatter delimiter")
    end = skill_text.find("\n---\n", 4)
    if end == -1:
        pytest.fail("SKILL.md frontmatter is not closed by '---'")
    raw = skill_text[4:end]
    parsed = yaml.safe_load(raw)
    assert isinstance(parsed, dict), "SKILL.md frontmatter must be a YAML mapping"
    return parsed


def test_skill_md_exists() -> None:
    assert _SKILL_MD.is_file(), f"missing {_SKILL_MD}"


def test_frontmatter_has_required_fields(skill_frontmatter: dict[str, object]) -> None:
    """Claude Code's skill spec requires name + description + version."""
    for field in ("name", "description", "version"):
        assert field in skill_frontmatter, f"frontmatter missing required field: {field}"


def test_skill_name_is_pretorin(skill_frontmatter: dict[str, object]) -> None:
    assert skill_frontmatter["name"] == "pretorin"


def test_skill_documents_recipe_lifecycle(skill_text: str) -> None:
    """Calling agents need to know about the four recipe lifecycle tools."""
    for tool_name in (
        "pretorin_list_recipes",
        "pretorin_get_recipe",
        "pretorin_start_recipe",
        "pretorin_end_recipe",
    ):
        assert tool_name in skill_text, f"SKILL.md should document MCP tool: {tool_name}"


def test_skill_documents_per_script_tool_pattern(skill_text: str) -> None:
    """The dynamic per-recipe-script tools follow a discoverable name pattern."""
    assert "pretorin_recipe_<safe_id>__<script>" in skill_text or "pretorin_recipe_" in skill_text


def test_skill_lists_each_builtin_recipe_id(skill_text: str) -> None:
    """The eight recipes shipped with pretorin should all appear by id."""
    for recipe_id in (
        "code-evidence-capture",
        "inspec-baseline",
        "openscap-baseline",
        "cloud-aws-baseline",
        "cloud-azure-baseline",
        "manual-attestation",
        "scope-q-answer",
        "policy-q-answer",
    ):
        assert recipe_id in skill_text, f"SKILL.md should mention built-in recipe: {recipe_id}"


def test_skill_documents_workflow_lifecycle(skill_text: str) -> None:
    """The workflow discovery tools must be documented for the agent to find them."""
    for tool_name in ("pretorin_list_workflows", "pretorin_get_workflow"):
        assert tool_name in skill_text, f"SKILL.md should document MCP tool: {tool_name}"


def test_skill_documents_engagement_entry_point(skill_text: str) -> None:
    """pretorin_start_task is the routing entry point — without it the agent
    freelances and breaks the audit chain."""
    assert "pretorin_start_task" in skill_text
    # Must be flagged as the FIRST call so the agent doesn't skip it.
    assert "FIRST" in skill_text or "first" in skill_text


def test_skill_lists_each_builtin_workflow_id(skill_text: str) -> None:
    for workflow_id in ("single-control", "scope-question", "policy-question", "campaign"):
        assert workflow_id in skill_text, f"SKILL.md should mention built-in workflow: {workflow_id}"


def test_skill_contains_recipe_workflow_section(skill_text: str) -> None:
    """The lifecycle section gives the agent a concrete sequence to follow."""
    assert "## Recipe Workflow" in skill_text


def test_skill_does_not_mention_legacy_scan_command(skill_text: str) -> None:
    """The legacy `pretorin scan` was removed; SKILL.md must not bring it back."""
    assert "pretorin scan " not in skill_text
    assert "ScanOrchestrator" not in skill_text
