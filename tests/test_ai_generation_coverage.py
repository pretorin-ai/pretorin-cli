"""Tests for src/pretorin/workflows/ai_generation.py.

Covers _strip_json_fence, _extract_json_object, _string_list, _dict_list,
_build_generation_task, and draft_control_artifacts (success + error paths).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from pretorin.workflows.ai_generation import (
    _build_generation_task,
    _dict_list,
    _extract_json_object,
    _string_list,
    _strip_json_fence,
)

# ---------------------------------------------------------------------------
# _strip_json_fence
# ---------------------------------------------------------------------------


class TestStripJsonFence:
    def test_plain_json_unchanged(self) -> None:
        raw = '{"key": "value"}'
        assert _strip_json_fence(raw) == raw

    def test_json_fenced_block_stripped(self) -> None:
        raw = '```json\n{"key": "value"}\n```'
        result = _strip_json_fence(raw)
        assert result == '{"key": "value"}'

    def test_plain_fence_block_stripped(self) -> None:
        raw = '```\n{"key": "value"}\n```'
        result = _strip_json_fence(raw)
        assert result == '{"key": "value"}'

    def test_leading_trailing_whitespace_stripped(self) -> None:
        raw = "  \n  {}\n  "
        result = _strip_json_fence(raw)
        assert result == "{}"

    def test_fence_without_closing_backticks(self) -> None:
        raw = "```json\n{}"
        result = _strip_json_fence(raw)
        # Opening fence removed but no closing fence to strip
        assert "{}" in result


# ---------------------------------------------------------------------------
# _extract_json_object
# ---------------------------------------------------------------------------


class TestExtractJsonObject:
    def test_valid_json_object(self) -> None:
        text = '{"narrative_draft": "test", "evidence_gap_assessment": "gap"}'
        result = _extract_json_object(text)
        assert result == {"narrative_draft": "test", "evidence_gap_assessment": "gap"}

    def test_json_object_with_surrounding_prose(self) -> None:
        text = 'Here is the output:\n{"key": "val"}\nEnd of output.'
        result = _extract_json_object(text)
        assert result == {"key": "val"}

    def test_non_json_returns_none(self) -> None:
        result = _extract_json_object("This is just plain text with no JSON.")
        assert result is None

    def test_non_dict_json_returns_none(self) -> None:
        # A JSON array is not a dict
        result = _extract_json_object("[1, 2, 3]")
        assert result is None

    def test_fenced_json_parsed(self) -> None:
        text = '```json\n{"status": "ok"}\n```'
        result = _extract_json_object(text)
        assert result == {"status": "ok"}

    def test_malformed_json_returns_none(self) -> None:
        result = _extract_json_object("{broken json !!}")
        assert result is None


# ---------------------------------------------------------------------------
# _string_list
# ---------------------------------------------------------------------------


class TestStringList:
    def test_list_of_strings_returned_as_is(self) -> None:
        assert _string_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_none_values_filtered_out(self) -> None:
        assert _string_list(["a", None, "b"]) == ["a", "b"]

    def test_non_list_returns_empty(self) -> None:
        assert _string_list("not a list") == []
        assert _string_list(None) == []
        assert _string_list(42) == []

    def test_mixed_types_coerced_to_string(self) -> None:
        result = _string_list([1, 2, 3])
        assert result == ["1", "2", "3"]


# ---------------------------------------------------------------------------
# _dict_list
# ---------------------------------------------------------------------------


class TestDictList:
    def test_list_of_dicts_returned(self) -> None:
        data = [{"name": "doc.pdf", "type": "policy_document"}]
        result = _dict_list(data)
        assert result == [{"name": "doc.pdf", "type": "policy_document"}]

    def test_non_dict_items_filtered(self) -> None:
        data = [{"name": "valid"}, "not-a-dict", 42, None]
        result = _dict_list(data)
        assert len(result) == 1
        assert result[0] == {"name": "valid"}

    def test_non_list_returns_empty(self) -> None:
        assert _dict_list("not a list") == []
        assert _dict_list(None) == []

    def test_none_values_in_dict_excluded(self) -> None:
        data = [{"key": "value", "other": None}]
        result = _dict_list(data)
        # None values are excluded by the `if val is not None` guard
        assert result == [{"key": "value"}]


# ---------------------------------------------------------------------------
# _build_generation_task
# ---------------------------------------------------------------------------


class TestBuildGenerationTask:
    def test_output_contains_system_info(self) -> None:
        task = _build_generation_task("sys-abc", "My System", "fedramp-moderate", "ac-02")
        assert "sys-abc" in task
        assert "My System" in task

    def test_output_contains_framework_and_control(self) -> None:
        task = _build_generation_task("sys-1", "Sys", "fedramp-moderate", "ac-02")
        assert "fedramp-moderate" in task
        assert "ac-02" in task

    def test_output_contains_json_shape_guidance(self) -> None:
        task = _build_generation_task("sys-1", "Sys", "fw", "ctrl")
        assert "narrative_draft" in task
        assert "evidence_gap_assessment" in task
        assert "recommended_notes" in task
        assert "evidence_recommendations" in task

    def test_returns_string(self) -> None:
        result = _build_generation_task("s", "n", "f", "c")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# draft_control_artifacts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_draft_control_artifacts_success() -> None:
    """Successful run: agent returns valid JSON, parse_status is 'json'."""
    raw_response = (
        '{"narrative_draft": "test narrative", "evidence_gap_assessment": "gap text",'
        ' "recommended_notes": ["note1"], "evidence_recommendations":'
        ' [{"name": "doc", "evidence_type": "policy_document", "description": "desc"}]}'
    )

    with (
        patch(
            "pretorin.workflows.ai_generation.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "fedramp-moderate"),
        ),
        patch("pretorin.agent.codex_agent.CodexAgent") as mock_agent,
    ):
        mock_agent_instance = mock_agent.return_value
        mock_agent_instance.run = AsyncMock(return_value=SimpleNamespace(response=raw_response))

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary System"))

        from pretorin.workflows.ai_generation import draft_control_artifacts

        result = await draft_control_artifacts(
            client,
            system="sys-1",
            framework_id="fedramp-moderate",
            control_id="ac-02",
        )

    assert result["parse_status"] == "json"
    assert result["system_id"] == "sys-1"
    assert result["system_name"] == "Primary System"
    assert result["framework_id"] == "fedramp-moderate"
    assert result["control_id"] == "ac-02"
    assert result["narrative_draft"] == "test narrative"
    assert result["evidence_gap_assessment"] == "gap text"
    assert result["recommended_notes"] == ["note1"]
    assert len(result["evidence_recommendations"]) == 1
    # WS5d: every drafting call records the recipe-selection decision so the
    # audit trail captures whether a recipe drove the draft or freelance did.
    assert "recipe_selection" in result
    assert "fallback_to_freelance" in result["recipe_selection"]


@pytest.mark.asyncio
async def test_draft_control_artifacts_raw_fallback_on_non_json_response() -> None:
    """When agent returns non-JSON, parse_status is 'raw_fallback'."""
    with (
        patch(
            "pretorin.workflows.ai_generation.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-2", "nist-800-53-r5"),
        ),
        patch("pretorin.agent.codex_agent.CodexAgent") as mock_agent,
    ):
        mock_agent_instance = mock_agent.return_value
        mock_agent_instance.run = AsyncMock(
            return_value=SimpleNamespace(response="Sorry, I cannot complete this task.")
        )

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Fallback System"))

        from pretorin.workflows.ai_generation import draft_control_artifacts

        result = await draft_control_artifacts(
            client,
            system="sys-2",
            framework_id="nist-800-53-r5",
            control_id="ac-2",
        )

    assert result["parse_status"] == "raw_fallback"
    assert result["narrative_draft"] is None
    assert result["recommended_notes"] == []


@pytest.mark.asyncio
async def test_draft_control_artifacts_runtime_error_raises_client_error() -> None:
    """RuntimeError from the agent is re-raised as PretorianClientError."""
    from pretorin.client.api import PretorianClientError

    with (
        patch(
            "pretorin.workflows.ai_generation.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-3", "fedramp-moderate"),
        ),
        patch("pretorin.agent.codex_agent.CodexAgent") as mock_agent,
    ):
        mock_agent_instance = mock_agent.return_value
        mock_agent_instance.run = AsyncMock(side_effect=RuntimeError("agent crashed"))

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Error System"))

        from pretorin.workflows.ai_generation import draft_control_artifacts

        with pytest.raises(PretorianClientError, match="agent crashed"):
            await draft_control_artifacts(
                client,
                system="sys-3",
                framework_id="fedramp-moderate",
                control_id="sc-07",
            )


@pytest.mark.asyncio
async def test_draft_control_artifacts_normalizes_control_id() -> None:
    """Control ID is zero-padded before being passed to the agent task."""
    captured_tasks: list[str] = []

    with (
        patch(
            "pretorin.workflows.ai_generation.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-4", "fedramp-moderate"),
        ),
        patch("pretorin.agent.codex_agent.CodexAgent") as mock_agent,
    ):
        mock_agent_instance = mock_agent.return_value

        async def capture_run(task: str, **kwargs: object) -> SimpleNamespace:
            captured_tasks.append(task)
            return SimpleNamespace(response='{"narrative_draft": "x", "evidence_gap_assessment": "y"}')

        mock_agent_instance.run = capture_run

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Norm System"))

        from pretorin.workflows.ai_generation import draft_control_artifacts

        result = await draft_control_artifacts(
            client,
            system="sys-4",
            framework_id="fedramp-moderate",
            control_id="ac-2",  # un-padded
        )

    # The normalized control ID (ac-02) should appear in the task text
    assert "ac-02" in captured_tasks[0]
    assert result["control_id"] == "ac-02"
