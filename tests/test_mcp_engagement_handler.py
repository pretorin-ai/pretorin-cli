"""Integration tests for the pretorin_start_task MCP handler.

The handler chains entity validation → cross-check → inspect → rule
selection → optional ambiguity override. These tests stub the platform
client and verify each branch.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.engagement import handle_start_task


def _success_payload(response):
    if isinstance(response, list):
        text = response[0].text
    else:
        text = response.content[0].text
    return json.loads(text)


def _error_text(response) -> str:
    if isinstance(response, list):
        return response[0].text
    return response.content[0].text


def _client_for_routing(*, systems=(), frameworks=()):
    client = MagicMock()
    client.list_systems = AsyncMock(return_value=list(systems))
    framework_objs = MagicMock()
    framework_objs.frameworks = list(frameworks)
    client.list_frameworks = AsyncMock(return_value=framework_objs)
    client.get_control = AsyncMock(return_value=MagicMock())
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": []})
    # Inspect calls — best-effort, return empty.
    client.get_workflow_state = AsyncMock(return_value={})
    client.get_pending_families = AsyncMock(return_value={})
    client.get_pending_scope_questions = AsyncMock(return_value={})
    client.list_org_policies = AsyncMock(return_value={"policies": []})
    return client


# =============================================================================
# Input validation
# =============================================================================


@pytest.mark.asyncio
async def test_missing_entities_argument_errors() -> None:
    client = _client_for_routing()
    response = await handle_start_task(client, {})
    assert "entities" in _error_text(response)


@pytest.mark.asyncio
async def test_invalid_intent_verb_errors() -> None:
    client = _client_for_routing()
    response = await handle_start_task(
        client,
        {"entities": {"intent_verb": "nonsense", "raw_prompt": "x"}},
    )
    assert "schema validation" in _error_text(response)


# =============================================================================
# Hard errors from cross-check
# =============================================================================


@pytest.mark.asyncio
async def test_hallucinated_system_id_returns_mcp_error() -> None:
    client = _client_for_routing(systems=[{"id": "sys-1", "name": "Primary"}])
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "work_on",
                "raw_prompt": "test",
                "system_id": "sys-zz",
            }
        },
    )
    assert "not found" in _error_text(response)


# =============================================================================
# Successful routing
# =============================================================================


@pytest.mark.asyncio
async def test_inspect_status_returns_no_workflow() -> None:
    client = _client_for_routing()
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "inspect_status",
                "raw_prompt": "what's the status",
            },
            "skip_inspect": True,
        },
    )
    payload = _success_payload(response)
    assert payload["selected_workflow"] is None
    assert payload["ambiguous"] is False


@pytest.mark.asyncio
async def test_single_control_routes_to_single_control_workflow() -> None:
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_for_routing(
        systems=[{"id": "sys-1", "name": "Primary"}],
        frameworks=[f],
    )
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "nist-800-53-r5"}]})
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "work_on",
                "raw_prompt": "draft AC-2 for Primary",
                "system_id": "sys-1",
                "framework_id": "nist-800-53-r5",
                "control_ids": ["ac-2"],
            },
            "skip_inspect": True,
        },
    )
    payload = _success_payload(response)
    assert payload["selected_workflow"] == "single-control"
    assert payload["workflow_params"]["control_id"] == "ac-2"
    assert payload["ambiguous"] is False


# =============================================================================
# Ambiguity overrides
# =============================================================================


@pytest.mark.asyncio
async def test_cross_system_intent_returns_ambiguous() -> None:
    """Even if the rules would route, cross-system writes need confirmation."""
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_for_routing(
        systems=[{"id": "sys-other", "name": "Other"}],
        frameworks=[f],
    )
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "work_on",
                "raw_prompt": "draft AC-2",
                "system_id": "sys-other",
                "framework_id": "nist-800-53-r5",
                "control_ids": ["ac-2"],
            },
            "active_system_id": "sys-active",
            "skip_inspect": True,
        },
    )
    payload = _success_payload(response)
    assert payload["ambiguous"] is True
    assert payload["selected_workflow"] is None
    assert "active CLI context" in (payload["ambiguity_reason"] or "")


# =============================================================================
# Inspect bundling
# =============================================================================


@pytest.mark.asyncio
async def test_inspect_summary_populated_when_not_skipped() -> None:
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_for_routing(
        systems=[{"id": "sys-1", "name": "Primary"}],
        frameworks=[f],
    )
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "nist-800-53-r5"}]})
    client.get_workflow_state = AsyncMock(return_value={"stage": "drafting"})
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "work_on",
                "raw_prompt": "AC-2",
                "system_id": "sys-1",
                "framework_id": "nist-800-53-r5",
                "control_ids": ["ac-2"],
            },
        },
    )
    payload = _success_payload(response)
    assert payload["inspect_summary"]["workflow_state"] == {"stage": "drafting"}


@pytest.mark.asyncio
async def test_inspect_resilient_to_platform_failures() -> None:
    """Inspect failures don't fail the whole call — they surface in errors."""
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_for_routing(
        systems=[{"id": "sys-1", "name": "Primary"}],
        frameworks=[f],
    )
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "nist-800-53-r5"}]})
    client.get_workflow_state = AsyncMock(side_effect=PretorianClientError("upstream timeout"))
    response = await handle_start_task(
        client,
        {
            "entities": {
                "intent_verb": "work_on",
                "raw_prompt": "x",
                "system_id": "sys-1",
                "framework_id": "nist-800-53-r5",
                "control_ids": ["ac-2"],
            },
        },
    )
    payload = _success_payload(response)
    assert payload["selected_workflow"] == "single-control"
    assert "error" in payload["inspect_summary"]["workflow_state"]
