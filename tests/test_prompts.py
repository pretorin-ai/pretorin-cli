"""Substring assertions for prompts updated by issue #77.

Full-text snapshots would force a fixture update on every tune of the prompt.
We instead pin the facts that matter: every valid evidence_type is listed, and
the model is told that an empty evidence_recommendations list is acceptable.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from pretorin.agent.skills import SKILLS, _WORKFLOW_GUARDRAILS
from pretorin.agent.tools import create_platform_tools
from pretorin.mcp.helpers import VALID_EVIDENCE_TYPES
from pretorin.workflows.ai_generation import _build_generation_task


def test_generation_prompt_lists_every_evidence_type() -> None:
    prompt = _build_generation_task("sys-1", "Demo", "fedramp-moderate", "ac-02")
    for evidence_type in VALID_EVIDENCE_TYPES:
        assert evidence_type in prompt, f"missing enum value: {evidence_type}"


def test_generation_prompt_permits_empty_evidence_list() -> None:
    prompt = _build_generation_task("sys-1", "Demo", "fedramp-moderate", "ac-02")
    lower = prompt.lower()
    assert "empty evidence_recommendations" in lower
    assert "recommended_notes" in prompt


def test_workflow_guardrails_include_concrete_artifact_language() -> None:
    lower = _WORKFLOW_GUARDRAILS.lower()
    assert "concrete" in lower and "auditable" in lower
    assert "file paths" in lower or "file path" in lower
    assert "empty evidence_recommendations list is a valid" in lower


def test_workflow_guardrails_list_every_evidence_type_for_todo_block() -> None:
    for evidence_type in VALID_EVIDENCE_TYPES:
        assert evidence_type in _WORKFLOW_GUARDRAILS, f"[[PRETORIN_TODO]] enum missing: {evidence_type}"


def test_skill_tool_names_reference_existing_agent_tools() -> None:
    """Every tool_name in a Skill must correspond to an actual ToolDefinition."""
    mock_client = MagicMock()
    defined_tools = create_platform_tools(mock_client)
    defined_names = {t.name for t in defined_tools}

    for skill_name, skill in SKILLS.items():
        for tool_name in skill.tool_names:
            assert tool_name in defined_names, (
                f"Skill {skill_name!r} references tool {tool_name!r} which does not exist in agent/tools.py"
            )
