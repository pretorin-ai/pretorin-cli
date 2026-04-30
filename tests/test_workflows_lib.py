"""Tests for the workflows_lib registry and MCP discovery handlers.

Smoke-level coverage: the four built-in workflow playbooks load, their
manifests pass schema validation, MCP list/get handlers return the right
shapes. The bodies themselves are prose the calling agent reads — content
review is the human's job.
"""

from __future__ import annotations

import json

import pytest

from pretorin.mcp.handlers.workflow_lib import (
    handle_get_workflow_lib,
    handle_list_workflows,
)
from pretorin.workflows_lib.manifest import WorkflowManifest
from pretorin.workflows_lib.registry import get_workflow, load_all

_BUILTIN_IDS = {
    "single-control",
    "scope-question",
    "policy-question",
    "campaign",
}


# =============================================================================
# Registry
# =============================================================================


def test_load_all_returns_every_builtin_workflow() -> None:
    workflows = load_all()
    ids = {w.manifest.id for w in workflows}
    for wid in _BUILTIN_IDS:
        assert wid in ids, f"missing built-in workflow: {wid}"


@pytest.mark.parametrize("workflow_id", sorted(_BUILTIN_IDS))
def test_get_workflow_finds_each_builtin(workflow_id: str) -> None:
    loaded = get_workflow(workflow_id)
    assert loaded is not None
    assert loaded.manifest.id == workflow_id
    assert loaded.body.strip(), f"{workflow_id} body must not be empty"


def test_get_workflow_unknown_returns_none() -> None:
    assert get_workflow("does-not-exist") is None


@pytest.mark.parametrize("workflow_id", sorted(_BUILTIN_IDS))
def test_each_workflow_has_a_self_contained_description(workflow_id: str) -> None:
    """Description and use_when must be substantive — they're what the
    engagement layer matches against."""
    loaded = get_workflow(workflow_id)
    assert loaded is not None
    assert len(loaded.manifest.description) >= 50
    assert len(loaded.manifest.use_when) >= 30


def test_workflow_iterates_over_values_match_design_enum() -> None:
    expected = {
        "single-control": "single_control",
        "scope-question": "scope_questions",
        "policy-question": "policy_questions",
        "campaign": "campaign_items",
    }
    for wid, iterates in expected.items():
        loaded = get_workflow(wid)
        assert loaded is not None
        assert loaded.manifest.iterates_over == iterates


# =============================================================================
# Manifest pydantic shape (lightweight; full schema tests live with the model)
# =============================================================================


def test_manifest_rejects_invalid_id() -> None:
    with pytest.raises(Exception):
        WorkflowManifest(
            id="UPPER-case-bad",
            version="0.1.0",
            name="Test",
            description="x" * 60,
            use_when="x" * 35,
            produces="evidence",
            iterates_over="single_control",
        )


def test_manifest_minimal_valid() -> None:
    m = WorkflowManifest(
        id="my-workflow",
        version="0.1.0",
        name="My Workflow",
        description="x" * 60,
        use_when="x" * 35,
        produces="evidence",
        iterates_over="single_control",
    )
    assert m.id == "my-workflow"
    assert m.recipes_commonly_used == []
    assert m.contract_version == 1


# =============================================================================
# MCP handlers
# =============================================================================


def _payload(response):
    """MCP handlers return either list[TextContent] (success → JSON) or
    CallToolResult (error → "Error: <msg>" text). Returns parsed JSON for
    success, raises if called against an error response."""
    if isinstance(response, list):
        text = response[0].text
    else:
        text = response.content[0].text
    return json.loads(text)


def _error_text(response) -> str:
    """Extract the error message from a CallToolResult error response."""
    if isinstance(response, list):
        return response[0].text
    return response.content[0].text


@pytest.mark.asyncio
async def test_handle_list_workflows_returns_all() -> None:
    result = await handle_list_workflows(None, {})  # type: ignore[arg-type]
    payload = _payload(result)
    assert payload["total"] == len(_BUILTIN_IDS)
    ids = {w["id"] for w in payload["workflows"]}
    assert ids == _BUILTIN_IDS


@pytest.mark.asyncio
async def test_handle_list_workflows_filter_by_iterates_over() -> None:
    result = await handle_list_workflows(
        None,  # type: ignore[arg-type]
        {"iterates_over": "scope_questions"},
    )
    payload = _payload(result)
    assert payload["total"] == 1
    assert payload["workflows"][0]["id"] == "scope-question"


@pytest.mark.asyncio
async def test_handle_get_workflow_returns_body_and_manifest() -> None:
    result = await handle_get_workflow_lib(
        None,  # type: ignore[arg-type]
        {"workflow_id": "single-control"},
    )
    payload = _payload(result)
    assert payload["id"] == "single-control"
    assert payload["manifest"]["iterates_over"] == "single_control"
    assert "Single Control Update" in payload["body"]


@pytest.mark.asyncio
async def test_handle_get_workflow_unknown_id_errors() -> None:
    result = await handle_get_workflow_lib(
        None,  # type: ignore[arg-type]
        {"workflow_id": "no-such-thing"},
    )
    assert "No workflow found" in _error_text(result)


@pytest.mark.asyncio
async def test_handle_get_workflow_missing_id_errors() -> None:
    result = await handle_get_workflow_lib(None, {})  # type: ignore[arg-type]
    assert "workflow_id" in _error_text(result)
