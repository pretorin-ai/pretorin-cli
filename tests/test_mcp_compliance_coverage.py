"""Coverage tests for src/pretorin/mcp/handlers/compliance.py.

Targets missing lines in: handle_generate_control_artifacts,
handle_push_monitoring_event, handle_get_control_context, handle_get_scope,
handle_add_control_note, handle_get_control_notes, handle_update_narrative,
handle_update_control_status, handle_get_control_implementation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import CallToolResult

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.compliance import (
    handle_add_control_note,
    handle_generate_control_artifacts,
    handle_get_control_context,
    handle_get_control_implementation,
    handle_get_scope,
    handle_push_monitoring_event,
    handle_update_control_status,
    handle_update_narrative,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**overrides) -> AsyncMock:
    """Build a mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _is_error(result) -> bool:
    """Return True if the result is an error CallToolResult."""
    return isinstance(result, CallToolResult) and result.isError is True


def _error_text(result) -> str:
    """Extract error text from a CallToolResult."""
    assert isinstance(result, CallToolResult)
    return " ".join(c.text for c in result.content)


def _result_text(result) -> str:
    """Extract text from a list[TextContent] result."""
    assert isinstance(result, list)
    return " ".join(c.text for c in result)


# ---------------------------------------------------------------------------
# handle_generate_control_artifacts
# ---------------------------------------------------------------------------


class TestHandleGenerateControlArtifacts:
    @pytest.mark.asyncio
    async def test_missing_required_args_returns_error(self):
        client = _make_client()
        result = await handle_generate_control_artifacts(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_control_id_returns_error(self):
        client = _make_client()
        result = await handle_generate_control_artifacts(
            client, {"system_id": "sys-1", "framework_id": "fedramp-moderate"}
        )
        assert _is_error(result)
        assert "control_id" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_returns_artifacts(self):
        client = _make_client()
        artifacts_response = {
            "system_id": "sys-1",
            "framework_id": "fedramp-moderate",
            "control_id": "ac-02",
            "narrative_draft": "System uses RBAC.",
            "parse_status": "json",
        }
        with patch(
            "pretorin.mcp.handlers.compliance.draft_control_artifacts",
            new=AsyncMock(return_value=artifacts_response),
        ):
            result = await handle_generate_control_artifacts(
                client,
                {
                    "system_id": "sys-1",
                    "framework_id": "fedramp-moderate",
                    "control_id": "ac-02",
                },
            )
        assert isinstance(result, list)
        assert "ac-02" in _result_text(result)

    @pytest.mark.asyncio
    async def test_success_with_working_directory(self):
        client = _make_client()
        artifacts_response = {"control_id": "sc-07", "narrative_draft": "Firewall controls."}
        with patch(
            "pretorin.mcp.handlers.compliance.draft_control_artifacts",
            new=AsyncMock(return_value=artifacts_response),
        ) as mock_draft:
            await handle_generate_control_artifacts(
                client,
                {
                    "system_id": "sys-1",
                    "framework_id": "fedramp-moderate",
                    "control_id": "sc-07",
                    "working_directory": "/tmp/artifacts",
                },
            )
        mock_draft.assert_awaited_once()
        call_kwargs = mock_draft.call_args.kwargs
        assert call_kwargs["working_directory"] is not None


# ---------------------------------------------------------------------------
# handle_push_monitoring_event
# ---------------------------------------------------------------------------


class TestHandlePushMonitoringEvent:
    @pytest.mark.asyncio
    async def test_missing_title_returns_error(self):
        client = _make_client()
        result = await handle_push_monitoring_event(client, {})
        assert _is_error(result)
        assert "title" in _error_text(result)

    @pytest.mark.asyncio
    async def test_invalid_event_type_returns_error(self):
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", None)),
        ):
            result = await handle_push_monitoring_event(
                client,
                {"title": "Test event", "event_type": "INVALID_TYPE"},
            )
        assert _is_error(result)
        assert "event_type" in _error_text(result)

    @pytest.mark.asyncio
    async def test_invalid_severity_returns_error(self):
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", None)),
        ):
            result = await handle_push_monitoring_event(
                client,
                {"title": "Test event", "severity": "CATASTROPHIC"},
            )
        assert _is_error(result)
        assert "severity" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_creates_event(self):
        client = _make_client(
            create_monitoring_event={"id": "evt-1", "title": "Scan Complete", "severity": "high"}
        )
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_push_monitoring_event(
                client,
                {
                    "title": "Scan Complete",
                    "severity": "high",
                    "event_type": "security_scan",
                    "system_id": "sys-1",
                    "framework_id": "fedramp-moderate",
                },
            )
        assert isinstance(result, list)
        assert "evt-1" in _result_text(result)


# ---------------------------------------------------------------------------
# handle_get_control_context
# ---------------------------------------------------------------------------


class TestHandleGetControlContext:
    @pytest.mark.asyncio
    async def test_success_returns_context(self):
        from pretorin.client.models import ControlContext

        ctx_data = ControlContext(control_id="ac-02", title="Access Control Policy")
        client = _make_client(get_control_context=ctx_data)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_get_control_context(
                client,
                {"system_id": "sys-1", "framework_id": "fedramp-moderate", "control_id": "ac-02"},
            )
        assert isinstance(result, list)
        assert "ac-02" in _result_text(result)

    @pytest.mark.asyncio
    async def test_control_context_calls_client_with_resolved_ids(self):
        from pretorin.client.models import ControlContext

        ctx_data = ControlContext(control_id="sc-07")
        client = _make_client(get_control_context=ctx_data)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "sc-07")),
        ):
            await handle_get_control_context(
                client,
                {"system_id": "sys-1", "framework_id": "fedramp-moderate", "control_id": "sc-07"},
            )
        client.get_control_context.assert_awaited_once_with(
            system_id="sys-1", control_id="sc-07", framework_id="fedramp-moderate"
        )


# ---------------------------------------------------------------------------
# handle_get_scope
# ---------------------------------------------------------------------------


class TestHandleGetScope:
    @pytest.mark.asyncio
    async def test_success_returns_scope(self):
        from pretorin.client.models import ScopeResponse

        scope = ScopeResponse(
            scope_status="complete",
            scope_narrative={"description": "In scope: all production systems."},
        )
        client = _make_client(get_scope=scope)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_system_id",
            new=AsyncMock(return_value="sys-1"),
        ):
            result = await handle_get_scope(client, {"system_id": "sys-1", "framework_id": "nist-800-53-r5"})
        assert isinstance(result, list)
        assert "complete" in _result_text(result)

    @pytest.mark.asyncio
    async def test_missing_framework_id_returns_error(self):
        client = _make_client()
        result = await handle_get_scope(client, {"system_id": "sys-1"})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_system_id_none_raises_client_error(self):
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_system_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_get_scope(client, {"system_id": "sys-1", "framework_id": "nist-800-53-r5"})


# ---------------------------------------------------------------------------
# handle_add_control_note
# ---------------------------------------------------------------------------


class TestHandleAddControlNote:
    @pytest.mark.asyncio
    async def test_missing_required_args_returns_error(self):
        client = _make_client()
        result = await handle_add_control_note(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_content_returns_error(self):
        client = _make_client()
        result = await handle_add_control_note(
            client,
            {"system_id": "sys-1", "control_id": "ac-02", "framework_id": "fedramp-moderate"},
        )
        assert _is_error(result)
        assert "content" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_adds_note(self):
        note_response = {"id": "note-1", "content": "Manual review complete", "source": "cli"}
        client = _make_client(add_control_note=note_response)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_add_control_note(
                client,
                {
                    "system_id": "sys-1",
                    "control_id": "ac-02",
                    "framework_id": "fedramp-moderate",
                    "content": "Manual review complete",
                },
            )
        assert isinstance(result, list)
        assert "note-1" in _result_text(result)


# ---------------------------------------------------------------------------
# handle_update_narrative
# ---------------------------------------------------------------------------


class TestHandleUpdateNarrative:
    @pytest.mark.asyncio
    async def test_missing_required_args_returns_error(self):
        client = _make_client()
        result = await handle_update_narrative(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_narrative_returns_error(self):
        client = _make_client()
        result = await handle_update_narrative(
            client,
            {"system_id": "sys-1", "control_id": "ac-02", "framework_id": "fedramp-moderate"},
        )
        assert _is_error(result)
        assert "narrative" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_updates_narrative(self):
        narrative_response = {"control_id": "ac-02", "narrative": "Access is controlled via RBAC."}
        client = _make_client(update_narrative=narrative_response)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_update_narrative(
                client,
                {
                    "system_id": "sys-1",
                    "control_id": "ac-02",
                    "framework_id": "fedramp-moderate",
                    "narrative": "Access is controlled via RBAC.",
                },
            )
        assert isinstance(result, list)
        assert "ac-02" in _result_text(result)

    @pytest.mark.asyncio
    async def test_value_error_returns_error(self):
        client = _make_client()
        client.update_narrative = AsyncMock(side_effect=ValueError("narrative too long"))
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_update_narrative(
                client,
                {
                    "system_id": "sys-1",
                    "control_id": "ac-02",
                    "framework_id": "fedramp-moderate",
                    "narrative": "x" * 10000,
                },
            )
        assert _is_error(result)
        assert "narrative too long" in _error_text(result)


# ---------------------------------------------------------------------------
# handle_update_control_status
# ---------------------------------------------------------------------------


class TestHandleUpdateControlStatus:
    @pytest.mark.asyncio
    async def test_missing_required_args_returns_error(self):
        client = _make_client()
        result = await handle_update_control_status(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_status_returns_error(self):
        client = _make_client()
        result = await handle_update_control_status(client, {"control_id": "ac-02"})
        assert _is_error(result)
        assert "status" in _error_text(result)

    @pytest.mark.asyncio
    async def test_invalid_status_returns_error(self):
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_update_control_status(
                client,
                {"control_id": "ac-02", "status": "fully_compliant"},
            )
        assert _is_error(result)
        assert "status" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_updates_status(self):
        status_response = {"control_id": "ac-02", "status": "implemented"}
        client = _make_client(update_control_status=status_response)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_update_control_status(
                client,
                {
                    "system_id": "sys-1",
                    "framework_id": "fedramp-moderate",
                    "control_id": "ac-02",
                    "status": "implemented",
                },
            )
        assert isinstance(result, list)
        assert "implemented" in _result_text(result)


# ---------------------------------------------------------------------------
# handle_get_control_implementation
# ---------------------------------------------------------------------------


class TestHandleGetControlImplementation:
    @pytest.mark.asyncio
    async def test_missing_required_args_returns_error(self):
        client = _make_client()
        result = await handle_get_control_implementation(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)

    @pytest.mark.asyncio
    async def test_uses_active_scope_when_explicit_scope_omitted(self):
        from pretorin.client.models import ControlImplementationResponse

        client = _make_client(
            get_control_implementation=ControlImplementationResponse(
                control_id="ac-02",
                status="partially_implemented",
                implementation_narrative="In progress.",
                evidence_count=2,
                notes=[{"content": "Reviewing access logs"}],
            )
        )
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_get_control_implementation(client, {"control_id": "ac-02"})
        assert isinstance(result, list)
        assert "ac-02" in _result_text(result)

    @pytest.mark.asyncio
    async def test_success_returns_implementation(self):
        from pretorin.client.models import ControlImplementationResponse

        impl = ControlImplementationResponse(
            control_id="ac-02",
            status="partially_implemented",
            implementation_narrative="In progress.",
            evidence_count=2,
            notes=[{"content": "Reviewing access logs"}],
        )
        client = _make_client(get_control_implementation=impl)
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_get_control_implementation(
                client,
                {
                    "system_id": "sys-1",
                    "control_id": "ac-02",
                    "framework_id": "fedramp-moderate",
                },
            )
        assert isinstance(result, list)
        text = _result_text(result)
        assert "ac-02" in text
        assert "partially_implemented" in text
        assert "2" in text
