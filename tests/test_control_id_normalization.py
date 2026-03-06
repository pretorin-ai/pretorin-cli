"""Tests for control ID normalization across client and agent paths."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest

from pretorin.agent.tools import create_platform_tools
from pretorin.client.api import PretorianClient
from pretorin.client.models import (
    ComplianceArtifact,
    ComponentDefinition,
    EvidenceCreate,
    ImplementationStatement,
)
from pretorin.utils import normalize_control_id


@pytest.mark.asyncio
async def test_client_get_control_normalizes_control_id_in_path() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"id": "ac-02", "title": "Account Management"})  # type: ignore[method-assign]

    await client.get_control("fedramp-moderate", "ac-2")

    client._request.assert_awaited_once_with("GET", "/frameworks/fedramp-moderate/controls/ac-02")


@pytest.mark.asyncio
async def test_client_create_evidence_normalizes_control_id_in_payload() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"id": "ev-1"})  # type: ignore[method-assign]

    evidence = EvidenceCreate(
        name="RBAC config",
        description="Role mapping",
        control_id="ac-2",
        framework_id="fedramp-moderate",
    )
    await client.create_evidence("sys-1", evidence)

    client._request.assert_awaited_once()
    await_args = client._request.await_args
    assert await_args is not None
    _method, _path = await_args.args
    payload = cast(dict[str, Any], await_args.kwargs["json"])
    assert payload["control_id"] == "ac-02"


@pytest.mark.asyncio
async def test_client_submit_artifact_normalizes_root_and_nested_control_ids() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"artifact_id": "art-1"})  # type: ignore[method-assign]

    artifact = ComplianceArtifact(
        framework_id="fedramp-moderate",
        control_id="ac-2",
        component=ComponentDefinition(
            component_id="app",
            title="App",
            description="Service",
            control_implementations=[
                ImplementationStatement(
                    control_id="ac-2",
                    description="Implemented with RBAC",
                    implementation_status="implemented",
                )
            ],
        ),
    )
    await client.submit_artifact(artifact)

    client._request.assert_awaited_once()
    await_args = client._request.await_args
    assert await_args is not None
    payload = cast(dict[str, Any], await_args.kwargs["json"])
    assert payload["control_id"] == "ac-02"
    assert payload["component"]["control_implementations"][0]["control_id"] == "ac-02"


@pytest.mark.asyncio
async def test_agent_tool_update_control_status_normalizes_control_id() -> None:
    mock_client = AsyncMock()
    mock_client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    mock_client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    mock_client.get_control = AsyncMock(return_value=AsyncMock())
    mock_client.update_control_status = AsyncMock(return_value={"ok": True})

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["update_control_status"].handler(
        system_id="sys-1",
        control_id="ac-2",
        status="implemented",
        framework_id="fedramp-moderate",
    )

    mock_client.update_control_status.assert_awaited_once_with(
        "sys-1",
        "ac-2",
        "implemented",
        "fedramp-moderate",
    )


@pytest.mark.asyncio
async def test_agent_tool_search_evidence_normalizes_control_id_filter() -> None:
    mock_client = AsyncMock()
    mock_client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    mock_client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    mock_client.get_control = AsyncMock(return_value=AsyncMock())
    mock_client.list_evidence = AsyncMock(return_value=[])

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["search_evidence"].handler(
        system_id="sys-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
        limit=10,
    )

    mock_client.list_evidence.assert_awaited_once_with(
        system_id="sys-1",
        framework_id="fedramp-moderate",
        control_id="ac-02",
        limit=10,
    )


@pytest.mark.asyncio
async def test_agent_tool_add_control_note_normalizes_control_id() -> None:
    mock_client = AsyncMock()
    mock_client.add_control_note = AsyncMock(return_value={"ok": True})

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["add_control_note"].handler(
        system_id="sys-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
        content="Need manual SSO upload",
    )

    mock_client.add_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-2",
        content="Need manual SSO upload",
        framework_id="fedramp-moderate",
        source="cli",
    )


@pytest.mark.asyncio
async def test_agent_tool_get_control_notes_normalizes_control_id() -> None:
    mock_client = AsyncMock()
    mock_client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    mock_client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    mock_client.get_control = AsyncMock(return_value=AsyncMock())
    mock_client.list_control_notes = AsyncMock(return_value=[])

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["get_control_notes"].handler(
        system_id="sys-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
    )

    mock_client.list_control_notes.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
    )


@pytest.mark.asyncio
async def test_agent_tool_link_evidence_normalizes_control_id() -> None:
    mock_client = AsyncMock()
    mock_client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    mock_client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    mock_client.get_control = AsyncMock(return_value=AsyncMock())
    mock_client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["link_evidence"].handler(
        system_id="sys-1",
        evidence_id="ev-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
    )

    mock_client.link_evidence_to_control.assert_awaited_once_with(
        evidence_id="ev-1",
        control_id="ac-2",
        system_id="sys-1",
        framework_id="fedramp-moderate",
    )


# =========================================================================
# CMMC / non-NIST control ID passthrough
# =========================================================================


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("AC.L1-3.1.1", "AC.L1-3.1.1"),
        ("AC.L2-3.1.3", "AC.L2-3.1.3"),
        ("IA.L1-3.5.1", "IA.L1-3.5.1"),
        ("PE.L1-3.10.1", "PE.L1-3.10.1"),
        ("SI.L1-3.14.5", "SI.L1-3.14.5"),
        ("03.01.01", "03.01.01"),
        ("03.05.01", "03.05.01"),
    ],
)
def test_normalize_passes_cmmc_and_800_171_ids_unchanged(raw: str, expected: str) -> None:
    assert normalize_control_id(raw) == expected


# =========================================================================
# get_control_implementation requires framework_id
# =========================================================================


@pytest.mark.asyncio
async def test_client_get_control_implementation_cmmc_with_framework_id() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"control_id": "ac.l1-3.1.1", "status": "not_started"})  # type: ignore[method-assign]

    await client.get_control_implementation("sys-1", "AC.L1-3.1.1", "cmmc-l1")

    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/controls/AC.L1-3.1.1",
        params={"framework_id": "cmmc-l1"},
    )


@pytest.mark.asyncio
async def test_client_get_narrative_uses_scoped_endpoint() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"control_id": "ac-02", "framework_id": "fedramp-moderate"})  # type: ignore[method-assign]

    await client.get_narrative("sys-1", "ac-2", "fedramp-moderate")

    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/controls/ac-02/narrative",
        params={"framework_id": "fedramp-moderate"},
    )


@pytest.mark.asyncio
async def test_agent_tool_get_control_implementation_requires_framework_id() -> None:
    mock_client = AsyncMock()
    mock_client.get_control_implementation = AsyncMock(
        return_value=AsyncMock(model_dump=lambda: {"control_id": "ac.l1-3.1.1"})
    )

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["get_control_implementation"].handler(
        system_id="sys-1",
        control_id="AC.L1-3.1.1",
        framework_id="cmmc-l1",
    )

    mock_client.get_control_implementation.assert_awaited_once_with(
        "sys-1",
        "AC.L1-3.1.1",
        "cmmc-l1",
    )


@pytest.mark.asyncio
async def test_client_list_control_notes_uses_scoped_endpoint() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"notes": [{"content": "Scoped note"}]})  # type: ignore[method-assign]

    notes = await client.list_control_notes("sys-1", "ac-2", "fedramp-moderate")

    assert notes == [{"content": "Scoped note"}]
    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/controls/ac-02/notes",
        params={"framework_id": "fedramp-moderate"},
    )


@pytest.mark.asyncio
async def test_client_list_evidence_uses_scoped_public_endpoint() -> None:
    client = PretorianClient(api_key="test", api_base_url="https://api.example.com")
    client._request = AsyncMock(return_value={"evidence": []})  # type: ignore[method-assign]

    evidence = await client.list_evidence("sys-1", "fedramp-moderate", control_id="ac-2", limit=10)

    assert evidence == []
    client._request.assert_awaited_once_with(
        "GET",
        "/systems/sys-1/evidence",
        params={"limit": 10, "framework_id": "fedramp-moderate", "control_id": "ac-02"},
    )
