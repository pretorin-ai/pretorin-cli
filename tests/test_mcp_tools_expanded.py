"""Tests for expanded MCP tools (18 total).

Tests verify tool listing, dispatch, and error handling using mocked API responses.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from pretorin.client.api import NotFoundError, PretorianClientError
from pretorin.mcp.server import call_tool, list_tools


class TestToolListing:
    """Verify all 18 tools are registered."""

    def test_all_tools_listed(self) -> None:
        tools = asyncio.run(list_tools())
        tool_names = [t.name for t in tools]

        expected = [
            # Original 7
            "pretorin_list_frameworks",
            "pretorin_get_framework",
            "pretorin_list_control_families",
            "pretorin_list_controls",
            "pretorin_get_control",
            "pretorin_get_control_references",
            "pretorin_get_document_requirements",
            # New 11
            "pretorin_list_systems",
            "pretorin_get_system",
            "pretorin_get_compliance_status",
            "pretorin_search_evidence",
            "pretorin_create_evidence",
            "pretorin_link_evidence",
            "pretorin_generate_narrative",
            "pretorin_get_narrative",
            "pretorin_push_monitoring_event",
            "pretorin_update_control_status",
            "pretorin_get_control_implementation",
        ]

        assert len(tools) == 18
        for name in expected:
            assert name in tool_names, f"Missing tool: {name}"

    def test_all_tools_have_descriptions(self) -> None:
        tools = asyncio.run(list_tools())
        for tool in tools:
            assert tool.description, f"Tool {tool.name} has no description"

    def test_all_tools_have_input_schemas(self) -> None:
        tools = asyncio.run(list_tools())
        for tool in tools:
            assert tool.inputSchema, f"Tool {tool.name} has no input schema"
            assert tool.inputSchema.get("type") == "object"


def _make_mock_client(**overrides: Any) -> AsyncMock:
    """Create a properly configured mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _run_tool(name: str, arguments: dict[str, Any], mock_client: AsyncMock) -> list[Any]:
    """Run a tool call with a mocked client via async context manager patch."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("pretorin.mcp.server.PretorianClient", return_value=ctx):
        return asyncio.run(call_tool(name, arguments))


def _parse_result(result: list[Any]) -> Any:
    """Parse the JSON text from a tool result."""
    assert len(result) == 1
    return json.loads(result[0].text)


class TestSystemTools:
    """Test system-related MCP tools."""

    def test_list_systems(self) -> None:
        client = _make_mock_client(
            list_systems=[
                {"id": "sys-1", "name": "Test System", "description": "A test", "security_impact_level": "moderate"},
            ]
        )
        result = _run_tool("pretorin_list_systems", {}, client)
        data = _parse_result(result)
        assert data["total"] == 1
        assert data["systems"][0]["name"] == "Test System"

    def test_get_system(self) -> None:
        from pretorin.client.models import SystemDetail

        system = SystemDetail(
            id="sys-1", name="Test System", description="Desc",
            frameworks=[{"id": "fedramp-moderate"}], security_impact_level="moderate",
        )
        client = _make_mock_client(get_system=system)
        result = _run_tool("pretorin_get_system", {"system_id": "sys-1"}, client)
        data = _parse_result(result)
        assert data["id"] == "sys-1"
        assert data["name"] == "Test System"

    def test_get_compliance_status(self) -> None:
        status_data = {"system_id": "sys-1", "frameworks": [{"id": "fedramp-moderate", "progress": 75}]}
        client = _make_mock_client(get_system_compliance_status=status_data)
        result = _run_tool("pretorin_get_compliance_status", {"system_id": "sys-1"}, client)
        data = _parse_result(result)
        assert data["system_id"] == "sys-1"


class TestEvidenceTools:
    """Test evidence-related MCP tools."""

    def test_search_evidence(self) -> None:
        from pretorin.client.models import EvidenceItemResponse

        evidence = [
            EvidenceItemResponse(
                id="ev-1",
                name="RBAC Config",
                description="Role config",
                evidence_type="configuration",
            ),
        ]
        client = _make_mock_client(list_evidence=evidence)
        result = _run_tool("pretorin_search_evidence", {"control_id": "ac-2"}, client)
        data = _parse_result(result)
        assert data["total"] == 1
        assert data["evidence"][0]["name"] == "RBAC Config"

    def test_create_evidence(self) -> None:
        client = _make_mock_client(create_evidence={"id": "ev-new", "name": "New Evidence"})
        result = _run_tool("pretorin_create_evidence", {"name": "New Evidence", "description": "Test"}, client)
        data = _parse_result(result)
        assert data["id"] == "ev-new"

    def test_link_evidence(self) -> None:
        client = _make_mock_client(link_evidence_to_control={"linked": True})
        result = _run_tool("pretorin_link_evidence", {"evidence_id": "ev-1", "control_id": "ac-2"}, client)
        data = _parse_result(result)
        assert data["linked"] is True


class TestNarrativeTools:
    """Test narrative-related MCP tools."""

    def test_generate_narrative(self) -> None:
        client = _make_mock_client(generate_narrative={
            "control_id": "ac-2",
            "narrative": "This system implements AC-2 through...",
            "ai_confidence_score": 0.85,
        })
        result = _run_tool("pretorin_generate_narrative", {
            "system_id": "sys-1",
            "control_id": "ac-2",
            "framework_id": "fedramp-moderate",
        }, client)
        data = _parse_result(result)
        assert data["control_id"] == "ac-2"
        assert "narrative" in data

    def test_get_narrative(self) -> None:
        from pretorin.client.models import NarrativeResponse

        narrative = NarrativeResponse(
            control_id="ac-2", framework_id="fedramp-moderate",
            narrative="Existing narrative", ai_confidence_score=0.9, status="approved",
        )
        client = _make_mock_client(get_narrative=narrative)
        result = _run_tool("pretorin_get_narrative", {"system_id": "sys-1", "control_id": "ac-2"}, client)
        data = _parse_result(result)
        assert data["narrative"] == "Existing narrative"


class TestMonitoringTools:
    """Test monitoring-related MCP tools."""

    def test_push_monitoring_event(self) -> None:
        client = _make_mock_client(create_monitoring_event={
            "id": "evt-1", "title": "Scan Complete", "severity": "high",
        })
        result = _run_tool("pretorin_push_monitoring_event", {
            "system_id": "sys-1",
            "title": "Scan Complete",
            "severity": "high",
        }, client)
        data = _parse_result(result)
        assert data["id"] == "evt-1"


class TestControlImplementationTools:
    """Test control implementation tools."""

    def test_update_control_status(self) -> None:
        client = _make_mock_client(update_control_status={
            "control_id": "ac-2", "status": "implemented",
        })
        result = _run_tool("pretorin_update_control_status", {
            "system_id": "sys-1",
            "control_id": "ac-2",
            "status": "implemented",
        }, client)
        data = _parse_result(result)
        assert data["status"] == "implemented"

    def test_get_control_implementation(self) -> None:
        from pretorin.client.models import ControlImplementationResponse

        impl = ControlImplementationResponse(
            control_id="ac-2", status="partial", narrative="In progress",
            evidence_count=3, notes=[{"content": "Working on it"}],
        )
        client = _make_mock_client(get_control_implementation=impl)
        result = _run_tool("pretorin_get_control_implementation", {
            "system_id": "sys-1",
            "control_id": "ac-2",
        }, client)
        data = _parse_result(result)
        assert data["control_id"] == "ac-2"
        assert data["evidence_count"] == 3


class TestErrorHandling:
    """Test error handling in tool dispatch."""

    def test_unknown_tool_returns_error(self) -> None:
        client = _make_mock_client()
        result = _run_tool("pretorin_nonexistent_tool", {}, client)
        text = result[0].text
        assert "Error" in text
        assert "Unknown tool" in text

    def test_not_configured_returns_error(self) -> None:
        client = AsyncMock()
        client.is_configured = False
        result = _run_tool("pretorin_list_systems", {}, client)
        text = result[0].text
        assert "Error" in text
        assert "Not authenticated" in text

    def test_not_found_returns_error(self) -> None:
        client = _make_mock_client()
        client.get_system = AsyncMock(side_effect=NotFoundError("System not found", 404))
        result = _run_tool("pretorin_get_system", {"system_id": "bad-id"}, client)
        text = result[0].text
        assert "Error" in text
        assert "Not found" in text

    def test_api_error_returns_error(self) -> None:
        client = _make_mock_client()
        client.list_systems = AsyncMock(side_effect=PretorianClientError("Server error", 500))
        result = _run_tool("pretorin_list_systems", {}, client)
        text = result[0].text
        assert "Error" in text
        assert "Server error" in text
