"""Tests for control ID normalization across client and agent paths."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pretorin.agent.tools import create_platform_tools
from pretorin.client.api import PretorianClient
from pretorin.client.models import ComplianceArtifact, ComponentDefinition, EvidenceCreate, ImplementationStatement


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
    _method, _path = client._request.await_args.args
    payload = client._request.await_args.kwargs["json"]
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
    payload = client._request.await_args.kwargs["json"]
    assert payload["control_id"] == "ac-02"
    assert payload["component"]["control_implementations"][0]["control_id"] == "ac-02"


@pytest.mark.asyncio
async def test_agent_tool_update_control_status_normalizes_control_id() -> None:
    mock_client = AsyncMock()
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
        "ac-02",
        "implemented",
        "fedramp-moderate",
    )


@pytest.mark.asyncio
async def test_agent_tool_search_evidence_normalizes_control_id_filter() -> None:
    mock_client = AsyncMock()
    mock_client.list_evidence = AsyncMock(return_value=[])

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["search_evidence"].handler(control_id="ac-2", framework_id="fedramp-moderate", limit=10)

    mock_client.list_evidence.assert_awaited_once_with(
        control_id="ac-02",
        framework_id="fedramp-moderate",
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
        control_id="ac-02",
        content="Need manual SSO upload",
        framework_id="fedramp-moderate",
        source="cli",
    )


@pytest.mark.asyncio
async def test_agent_tool_get_control_notes_normalizes_control_id() -> None:
    mock_client = AsyncMock()
    mock_client.list_control_notes = AsyncMock(return_value=[])

    tools = {tool.name: tool for tool in create_platform_tools(mock_client)}
    await tools["get_control_notes"].handler(
        system_id="sys-1",
        control_id="ac-2",
        framework_id="fedramp-moderate",
    )

    mock_client.list_control_notes.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        framework_id="fedramp-moderate",
    )


@pytest.mark.asyncio
async def test_agent_tool_link_evidence_normalizes_control_id() -> None:
    mock_client = AsyncMock()
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
        control_id="ac-02",
        system_id="sys-1",
        framework_id="fedramp-moderate",
    )
