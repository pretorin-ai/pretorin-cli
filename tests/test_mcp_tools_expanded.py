"""Tests for expanded MCP tools.

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
    """Verify expected tools are registered."""

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
            "pretorin_get_controls_batch",
            "pretorin_get_control_references",
            "pretorin_get_document_requirements",
            # System & compliance 3
            "pretorin_list_systems",
            "pretorin_get_system",
            "pretorin_get_compliance_status",
            # Evidence 4
            "pretorin_search_evidence",
            "pretorin_create_evidence",
            "pretorin_create_evidence_batch",
            "pretorin_link_evidence",
            # Narrative 2
            "pretorin_get_narrative",
            "pretorin_generate_control_artifacts",
            # Notes 2
            "pretorin_add_control_note",
            "pretorin_get_control_notes",
            # Monitoring 1
            "pretorin_push_monitoring_event",
            # Control context & scope 2
            "pretorin_get_control_context",
            "pretorin_get_scope",
            # Scope & policy questionnaire 4
            "pretorin_patch_scope_qa",
            "pretorin_list_org_policies",
            "pretorin_get_org_policy_questionnaire",
            "pretorin_patch_org_policy_qa",
            # Control implementation 3
            "pretorin_update_narrative",
            "pretorin_update_control_status",
            "pretorin_get_control_implementation",
        ]

        assert len(tools) == 64
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

    def test_control_id_schemas_use_shared_guidance(self) -> None:
        tools = asyncio.run(list_tools())
        with_control_id = [t for t in tools if "control_id" in t.inputSchema.get("properties", {})]

        assert with_control_id, "Expected at least one tool with a control_id parameter"

        for tool in with_control_id:
            control_field = tool.inputSchema["properties"]["control_id"]
            description = control_field.get("description", "")
            required = tool.inputSchema.get("required", [])

            assert "zero-padded" in description
            assert "ac-02" in description
            assert "AC.L2-3.1.1" in description
            assert control_field.get("examples") == ["ac-02", "sc-07", "AC.L2-3.1.1", "03.01.01"]

            if "control_id" in required:
                assert not description.startswith("Optional:")
            else:
                assert description.startswith("Optional:")


def _make_mock_client(**overrides: Any) -> AsyncMock:
    """Create a properly configured mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]})
    client.get_control = AsyncMock(return_value=AsyncMock(id="ac-02"))
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _run_tool(name: str, arguments: dict[str, Any], mock_client: AsyncMock) -> Any:
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
            id="sys-1",
            name="Test System",
            description="Desc",
            frameworks=[{"id": "fedramp-moderate"}],
            security_impact_level="moderate",
        )
        client = _make_mock_client(get_system=system)
        result = _run_tool("pretorin_get_system", {"system_id": "sys-1"}, client)
        data = _parse_result(result)
        assert data["id"] == "sys-1"
        assert data["name"] == "Test System"

    def test_get_system_resolves_system_name(self) -> None:
        from pretorin.client.models import SystemDetail

        system = SystemDetail(
            id="sys-1",
            name="Test System",
            description="Desc",
            frameworks=[{"id": "fedramp-moderate"}],
            security_impact_level="moderate",
        )
        client = _make_mock_client(get_system=system)
        _run_tool("pretorin_get_system", {"system_id": "test"}, client)
        client.get_system.assert_awaited_once_with("sys-1")

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
        result = _run_tool(
            "pretorin_search_evidence",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
            },
            client,
        )
        data = _parse_result(result)
        assert data["total"] == 1
        assert data["evidence"][0]["name"] == "RBAC Config"
        client.list_evidence.assert_awaited_once_with(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            control_id="ac-02",
            limit=20,
        )

    def test_search_evidence_accepts_system_id(self) -> None:
        client = _make_mock_client(list_evidence=[])
        _run_tool(
            "pretorin_search_evidence",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
            },
            client,
        )
        client.list_evidence.assert_awaited_once_with(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            control_id="ac-02",
            limit=20,
        )

    def test_search_evidence_resolves_system_name(self) -> None:
        client = _make_mock_client(list_evidence=[])
        _run_tool(
            "pretorin_search_evidence",
            {
                "system_id": "test",
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
            },
            client,
        )
        client.list_evidence.assert_awaited_once_with(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            control_id="ac-02",
            limit=20,
        )

    def test_create_evidence(self) -> None:
        client = _make_mock_client(
            list_evidence=[],
            create_evidence={"id": "ev-new", "name": "New Evidence", "linked": True, "mapping_id": "map-1"},
            link_evidence_to_control={"linked": True},
        )
        result = _run_tool(
            "pretorin_create_evidence",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "name": "New Evidence",
                "description": "- Test",
            },
            client,
        )
        data = _parse_result(result)
        assert data["evidence_id"] == "ev-new"
        assert data["created"] is True
        assert data["linked"] is False
        client.link_evidence_to_control.assert_not_called()

    def test_create_evidence_reuses_duplicate(self) -> None:
        from pretorin.client.models import EvidenceItemResponse

        client = _make_mock_client(
            list_evidence=[
                EvidenceItemResponse(
                    id="ev-existing",
                    name="New Evidence",
                    description="- Test",
                    evidence_type="policy_document",
                    collected_at="2026-01-01T00:00:00+00:00",
                )
            ],
            link_evidence_to_control={"linked": True},
        )
        result = _run_tool(
            "pretorin_create_evidence",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "name": "New Evidence",
                "description": "- Test",
                "control_id": "ac-2",
            },
            client,
        )
        data = _parse_result(result)
        assert data["evidence_id"] == "ev-existing"
        assert data["created"] is False
        assert data["linked"] is True
        assert data["match_basis"] == "exact_name_desc_type_control_framework"

    def test_create_evidence_missing_scope(self) -> None:
        client = _make_mock_client()
        with patch(
            "pretorin.mcp.helpers.resolve_execution_context",
            new=AsyncMock(side_effect=PretorianClientError("No system/framework context set")),
        ):
            result = _run_tool(
                "pretorin_create_evidence",
                {"name": "New Evidence", "description": "- Test"},
                client,
            )
        assert result.isError is True
        assert any("No system/framework context set" in c.text for c in result.content)

    def test_create_evidence_batch(self) -> None:
        client = _make_mock_client(
            create_evidence_batch={
                "framework_id": "fedramp-moderate",
                "total": 1,
                "results": [{"index": 0, "status": "created", "evidence_id": "ev-1"}],
            }
        )
        result = _run_tool(
            "pretorin_create_evidence_batch",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "items": [
                    {
                        "name": "Batch Evidence",
                        "description": "- Batch test",
                        "control_id": "ac-2",
                    }
                ],
            },
            client,
        )
        data = _parse_result(result)
        assert data["total"] == 1
        client.create_evidence_batch.assert_awaited_once()

    def test_link_evidence(self) -> None:
        client = _make_mock_client(link_evidence_to_control={"linked": True})
        result = _run_tool(
            "pretorin_link_evidence",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "evidence_id": "ev-1",
                "control_id": "ac-2",
            },
            client,
        )
        data = _parse_result(result)
        assert data["linked"] is True
        client.link_evidence_to_control.assert_awaited_once_with(
            evidence_id="ev-1",
            control_id="ac-02",
            system_id="sys-1",
            framework_id="fedramp-moderate",
        )

    def test_link_evidence_missing_scope(self) -> None:
        client = _make_mock_client()
        with patch(
            "pretorin.mcp.helpers.resolve_execution_context",
            new=AsyncMock(side_effect=PretorianClientError("No system/framework context set")),
        ):
            result = _run_tool(
                "pretorin_link_evidence",
                {"evidence_id": "ev-1", "control_id": "ac-2"},
                client,
            )
        assert result.isError is True
        assert any("No system/framework context set" in c.text for c in result.content)


class TestNarrativeTools:
    """Test narrative-related MCP tools."""

    def test_get_narrative(self) -> None:
        from pretorin.client.models import NarrativeResponse

        narrative = NarrativeResponse(
            control_id="ac-2",
            framework_id="fedramp-moderate",
            narrative="Existing narrative",
            ai_confidence_score=0.9,
            status="approved",
        )
        client = _make_mock_client(get_narrative=narrative)
        result = _run_tool(
            "pretorin_get_narrative",
            {
                "system_id": "sys-1",
                "control_id": "ac-2",
                "framework_id": "fedramp-moderate",
            },
            client,
        )
        data = _parse_result(result)
        assert data["narrative"] == "Existing narrative"
        client.get_narrative.assert_awaited_once_with(
            system_id="sys-1",
            control_id="ac-02",
            framework_id="fedramp-moderate",
        )

    def test_get_narrative_missing_framework_id(self) -> None:
        client = _make_mock_client()
        result = _run_tool("pretorin_get_narrative", {"system_id": "sys-1", "control_id": "ac-2"}, client)
        assert result.isError is True
        assert any("Missing required" in c.text for c in result.content)

    def test_get_narrative_resolves_system_name(self) -> None:
        from pretorin.client.models import NarrativeResponse

        narrative = NarrativeResponse(
            control_id="ac-2",
            framework_id="fedramp-moderate",
            narrative="Existing narrative",
            ai_confidence_score=0.9,
            status="approved",
        )
        client = _make_mock_client(get_narrative=narrative)
        _run_tool(
            "pretorin_get_narrative",
            {
                "system_id": "test",
                "control_id": "ac-2",
                "framework_id": "fedramp-moderate",
            },
            client,
        )
        client.get_narrative.assert_awaited_once_with(
            system_id="sys-1",
            control_id="ac-02",
            framework_id="fedramp-moderate",
        )

    def test_generate_control_artifacts(self) -> None:
        client = _make_mock_client()
        with patch(
            "pretorin.mcp.handlers.compliance.draft_control_artifacts",
            new=AsyncMock(
                return_value={
                    "system_id": "sys-1",
                    "system_name": "Test System",
                    "framework_id": "fedramp-moderate",
                    "control_id": "ac-02",
                    "parse_status": "json",
                    "narrative_draft": "- Draft narrative",
                    "evidence_gap_assessment": "| Gap | Detail |",
                    "recommended_notes": ["Gap: Missing review"],
                    "evidence_recommendations": [{"name": "IAM Export", "evidence_type": "configuration"}],
                    "raw_response": "{}",
                }
            ),
        ) as mock_generate:
            result = _run_tool(
                "pretorin_generate_control_artifacts",
                {
                    "system_id": "test",
                    "control_id": "ac-2",
                    "framework_id": "fedramp-moderate",
                },
                client,
            )

        data = _parse_result(result)
        assert data["control_id"] == "ac-02"
        assert data["parse_status"] == "json"
        assert data["narrative_draft"] == "- Draft narrative"
        mock_generate.assert_awaited_once()

    def test_get_control_notes(self) -> None:
        client = _make_mock_client(
            list_control_notes=[{"content": "Manual SSO evidence upload required"}],
        )
        result = _run_tool(
            "pretorin_get_control_notes",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
            },
            client,
        )
        data = _parse_result(result)
        assert data["total"] == 1
        assert data["notes"][0]["content"] == "Manual SSO evidence upload required"
        client.list_control_notes.assert_awaited_once_with(
            system_id="sys-1",
            control_id="ac-02",
            framework_id="fedramp-moderate",
        )


class TestMonitoringTools:
    """Test monitoring-related MCP tools."""

    def test_push_monitoring_event(self) -> None:
        client = _make_mock_client(
            create_monitoring_event={
                "id": "evt-1",
                "title": "Scan Complete",
                "severity": "high",
            }
        )
        result = _run_tool(
            "pretorin_push_monitoring_event",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "title": "Scan Complete",
                "severity": "high",
            },
            client,
        )
        data = _parse_result(result)
        assert data["id"] == "evt-1"


class TestQuestionnaireTools:
    """Test scope and policy questionnaire MCP tools."""

    def test_patch_scope_qa(self) -> None:
        from pretorin.client.models import ScopeResponse

        scope = ScopeResponse(
            scope_status="in_progress",
            scope_qa_responses={"sd-1": {"answer": "Handles CUI in production"}},
        )
        client = _make_mock_client(patch_scope_qa=scope)
        result = _run_tool(
            "pretorin_patch_scope_qa",
            {
                "system_id": "test",
                "framework_id": "fedramp-moderate",
                "updates": [{"question_id": "sd-1", "answer": "Handles CUI in production"}],
            },
            client,
        )
        data = _parse_result(result)
        assert data["scope_status"] == "in_progress"
        client.patch_scope_qa.assert_awaited_once_with(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            updates=[{"question_id": "sd-1", "answer": "Handles CUI in production"}],
        )

    def test_patch_scope_qa_rejects_empty_updates(self) -> None:
        client = _make_mock_client()
        result = _run_tool(
            "pretorin_patch_scope_qa",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "updates": [],
            },
            client,
        )
        assert result.isError is True
        assert any("updates must be a non-empty list" in c.text for c in result.content)
        client.patch_scope_qa.assert_not_called()

    def test_list_org_policies(self) -> None:
        from pretorin.client.models import OrgPolicyListResponse, OrgPolicySummary

        listing = OrgPolicyListResponse(
            policies=[
                OrgPolicySummary(
                    id="pol-1",
                    name="Access Control Policy",
                    policy_template_id="tpl-1",
                    status="draft",
                    policy_qa_status="in_progress",
                )
            ],
            total=1,
        )
        client = _make_mock_client(list_org_policies=listing)
        result = _run_tool("pretorin_list_org_policies", {}, client)
        data = _parse_result(result)
        assert data["total"] == 1
        assert data["policies"][0]["name"] == "Access Control Policy"
        client.list_org_policies.assert_awaited_once_with()

    def test_get_org_policy_questionnaire(self) -> None:
        from pretorin.client.models import OrgPolicyQuestionnaireResponse

        questionnaire = OrgPolicyQuestionnaireResponse(
            policy_id="pol-1",
            name="Access Control Policy",
            policy_template_id="tpl-1",
            policy_qa_status="in_progress",
            policy_qa_responses={"ac-1": {"answer": "MFA is required for admins"}},
        )
        client = _make_mock_client(get_org_policy_questionnaire=questionnaire)
        result = _run_tool(
            "pretorin_get_org_policy_questionnaire",
            {"policy_id": "pol-1"},
            client,
        )
        data = _parse_result(result)
        assert data["policy_id"] == "pol-1"
        assert data["policy_qa_status"] == "in_progress"
        client.get_org_policy_questionnaire.assert_awaited_once_with("pol-1")

    def test_patch_org_policy_qa(self) -> None:
        from pretorin.client.models import OrgPolicyQuestionnaireResponse

        questionnaire = OrgPolicyQuestionnaireResponse(
            policy_id="pol-1",
            name="Access Control Policy",
            policy_template_id="tpl-1",
            policy_qa_status="complete",
            policy_qa_responses={"ac-1": {"answer": "MFA is required for all users"}},
        )
        client = _make_mock_client(patch_org_policy_qa=questionnaire)
        result = _run_tool(
            "pretorin_patch_org_policy_qa",
            {
                "policy_id": "pol-1",
                "updates": [{"question_id": "ac-1", "answer": "MFA is required for all users"}],
            },
            client,
        )
        data = _parse_result(result)
        assert data["policy_qa_status"] == "complete"
        client.patch_org_policy_qa.assert_awaited_once_with(
            policy_id="pol-1",
            updates=[{"question_id": "ac-1", "answer": "MFA is required for all users"}],
        )

    def test_patch_org_policy_qa_rejects_empty_updates(self) -> None:
        client = _make_mock_client()
        result = _run_tool(
            "pretorin_patch_org_policy_qa",
            {"policy_id": "pol-1", "updates": []},
            client,
        )
        assert result.isError is True
        assert any("updates must be a non-empty list" in c.text for c in result.content)
        client.patch_org_policy_qa.assert_not_called()


class TestControlImplementationTools:
    """Test control implementation tools."""

    def test_update_control_status(self) -> None:
        client = _make_mock_client(
            update_control_status={
                "control_id": "ac-2",
                "status": "implemented",
            }
        )
        result = _run_tool(
            "pretorin_update_control_status",
            {
                "system_id": "sys-1",
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
                "status": "implemented",
            },
            client,
        )
        data = _parse_result(result)
        assert data["status"] == "implemented"
        client.update_control_status.assert_awaited_once_with(
            system_id="sys-1",
            control_id="ac-02",
            status="implemented",
            framework_id="fedramp-moderate",
        )

    def test_get_control_implementation(self) -> None:
        from pretorin.client.models import ControlImplementationResponse

        impl = ControlImplementationResponse(
            control_id="ac-2",
            status="partially_implemented",
            implementation_narrative="In progress",
            evidence_count=3,
            notes=[{"content": "Working on it"}],
        )
        client = _make_mock_client(get_control_implementation=impl)
        result = _run_tool(
            "pretorin_get_control_implementation",
            {
                "system_id": "sys-1",
                "control_id": "ac-2",
                "framework_id": "fedramp-moderate",
            },
            client,
        )
        data = _parse_result(result)
        assert data["control_id"] == "ac-2"
        assert data["evidence_count"] == 3
        client.get_control_implementation.assert_awaited_once_with(
            system_id="sys-1",
            control_id="ac-02",
            framework_id="fedramp-moderate",
        )

    def test_get_control_implementation_missing_framework_id(self) -> None:
        client = _make_mock_client()
        result = _run_tool(
            "pretorin_get_control_implementation",
            {"system_id": "sys-1", "control_id": "ac-2"},
            client,
        )
        assert result.isError is True
        assert any("Missing required" in c.text for c in result.content)


class TestErrorHandling:
    """Test error handling in tool dispatch."""

    def test_unknown_tool_returns_error(self) -> None:
        client = _make_mock_client()
        result = _run_tool("pretorin_nonexistent_tool", {}, client)
        assert result.isError is True
        text = result.content[0].text
        assert "Error" in text
        assert "Unknown tool" in text

    def test_not_configured_returns_error(self) -> None:
        client = AsyncMock()
        client.is_configured = False
        result = _run_tool("pretorin_list_systems", {}, client)
        assert result.isError is True
        text = result.content[0].text
        assert "Error" in text
        assert "Not authenticated" in text

    def test_not_found_returns_error(self) -> None:
        client = _make_mock_client()
        client.get_system = AsyncMock(side_effect=NotFoundError("System not found", 404))
        result = _run_tool("pretorin_get_system", {"system_id": "bad-id"}, client)
        assert result.isError is True
        text = result.content[0].text
        assert "Error" in text
        assert "System not found: bad-id" in text

    def test_api_error_returns_error(self) -> None:
        client = _make_mock_client()
        client.list_systems = AsyncMock(side_effect=PretorianClientError("Server error", 500))
        result = _run_tool("pretorin_list_systems", {}, client)
        assert result.isError is True
        text = result.content[0].text
        assert "Error" in text
        assert "Server error" in text
