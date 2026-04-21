"""Tests for pretorin.agent.tools — targets 100 % coverage of tools.py."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.agent.tools import ToolDefinition, create_platform_tools, to_function_tool

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_tool(tools: list[ToolDefinition], name: str) -> ToolDefinition:
    """Look up a tool by name or fail the test."""
    for tool in tools:
        if tool.name == name:
            return tool
    raise AssertionError(f"Tool '{name}' not found in {[t.name for t in tools]}")


class _ModelStub:
    """Lightweight stand-in for any Pydantic model returned by the client."""

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

    def model_dump(self) -> dict[str, Any]:
        return self._data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_RESOLVE_CTX = "pretorin.agent.tools.resolve_execution_context"
_UPSERT = "pretorin.agent.tools.upsert_evidence"


@pytest.fixture()
def mock_client() -> AsyncMock:
    """Return an AsyncMock pretending to be PretorianClient."""
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "System 1"}])
    client.get_system = AsyncMock(return_value=_ModelStub({"id": "sys-1", "name": "System 1"}))
    client.get_system_compliance_status = AsyncMock(
        return_value={"status": "partial", "frameworks": [{"framework_id": "fw-1"}]}
    )
    client.list_frameworks = AsyncMock(return_value=_ModelStub({"frameworks": []}))
    client.get_control = AsyncMock(return_value=_ModelStub({"id": "ac-02", "title": "Account Mgmt"}))
    client.get_controls_batch = AsyncMock(return_value=_ModelStub({"controls": [], "total": 0}))
    client.list_evidence = AsyncMock(return_value=[])
    client.create_evidence = AsyncMock(return_value={"id": "ev-1"})
    client.create_evidence_batch = AsyncMock(return_value=_ModelStub({"results": [], "total": 0}))
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})
    client.get_narrative = AsyncMock(
        return_value=_ModelStub({"control_id": "ac-02", "narrative": "text"})
    )
    client.add_control_note = AsyncMock(return_value={"id": "note-1"})
    client.list_control_notes = AsyncMock(return_value=[])
    client.create_monitoring_event = AsyncMock(return_value={"id": "event-1"})
    client.update_control_status = AsyncMock(return_value={"status": "implemented"})
    client.get_control_implementation = AsyncMock(
        return_value=_ModelStub({"control_id": "ac-02", "status": "implemented"})
    )
    client.get_control_context = AsyncMock(
        return_value=_ModelStub({"control_id": "ac-02", "title": "Account Mgmt"})
    )
    client.get_scope = AsyncMock(
        return_value=_ModelStub({"scope_status": "completed", "excluded_controls": []})
    )
    client.update_narrative = AsyncMock(return_value={"ok": True})
    return client


@pytest.fixture(autouse=True)
def _blank_active_context() -> None:
    """Keep agent tool tests independent from the developer's local config."""
    config = MagicMock()
    config.check_context_environment.return_value = None
    config.active_system_id = None
    config.active_framework_id = None
    config.active_system_name = None
    config.get.side_effect = lambda _key, default=None: default
    with patch("pretorin.client.config.Config", return_value=config):
        yield


def _build_tools_patched(mock_client: AsyncMock) -> tuple[list[ToolDefinition], AsyncMock]:
    """Build tools with resolve_execution_context patched; returns tools and the mock."""
    patcher = patch(_RESOLVE_CTX, new_callable=AsyncMock)
    mock_ctx = patcher.start()
    mock_ctx.return_value = ("sys-1", "fw-1")
    tools = create_platform_tools(mock_client)
    # Caller must stop the patcher when done — or just leave it running for the test.
    return tools, mock_ctx


# ---------------------------------------------------------------------------
# to_function_tool
# ---------------------------------------------------------------------------


class TestToFunctionTool:
    """Cover to_function_tool (lines 36-50)."""

    def test_success_when_agents_importable(self) -> None:
        """When 'agents' package is available, return a FunctionTool."""
        tool_def = ToolDefinition(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
            handler=AsyncMock(return_value="ok"),
        )

        mock_function_tool_cls = MagicMock()
        mock_function_tool_cls.return_value = "fake-function-tool"

        with patch.dict("sys.modules", {"agents": MagicMock(FunctionTool=mock_function_tool_cls)}):
            result = to_function_tool(tool_def)

        assert result == "fake-function-tool"
        mock_function_tool_cls.assert_called_once()
        call_kwargs = mock_function_tool_cls.call_args
        assert call_kwargs.kwargs["name"] == "test_tool"

    def test_raises_import_error_when_agents_missing(self) -> None:
        """When 'agents' package is NOT installed, raise ImportError."""
        tool_def = ToolDefinition(
            name="test_tool",
            description="desc",
            parameters={},
            handler=AsyncMock(),
        )

        with patch.dict("sys.modules", {"agents": None}):
            with pytest.raises(ImportError, match="Agent features are not installed"):
                to_function_tool(tool_def)

    async def test_wrapper_invokes_handler(self) -> None:
        """The wrapper built inside to_function_tool correctly parses args and calls handler."""
        handler = AsyncMock(return_value="result-value")
        tool_def = ToolDefinition(
            name="t",
            description="d",
            parameters={},
            handler=handler,
        )

        mock_function_tool_cls = MagicMock()
        captured_wrapper = None

        def capture_ft(**kwargs: Any) -> MagicMock:
            nonlocal captured_wrapper
            captured_wrapper = kwargs["on_invoke_tool"]
            return MagicMock()

        mock_function_tool_cls.side_effect = capture_ft

        with patch.dict("sys.modules", {"agents": MagicMock(FunctionTool=mock_function_tool_cls)}):
            to_function_tool(tool_def)

        assert captured_wrapper is not None
        # Call wrapper with JSON args
        result = await captured_wrapper(None, json.dumps({"key": "val"}))
        handler.assert_awaited_once_with(key="val")
        assert result == "result-value"

    async def test_wrapper_handles_empty_args(self) -> None:
        handler = AsyncMock(return_value="empty")
        tool_def = ToolDefinition(name="t", description="d", parameters={}, handler=handler)

        mock_function_tool_cls = MagicMock()
        captured_wrapper = None

        def capture_ft(**kwargs: Any) -> MagicMock:
            nonlocal captured_wrapper
            captured_wrapper = kwargs["on_invoke_tool"]
            return MagicMock()

        mock_function_tool_cls.side_effect = capture_ft

        with patch.dict("sys.modules", {"agents": MagicMock(FunctionTool=mock_function_tool_cls)}):
            to_function_tool(tool_def)

        result = await captured_wrapper(None, "")
        handler.assert_awaited_once_with()
        assert result == "empty"


# ---------------------------------------------------------------------------
# Tool handler tests — simple tools (no _resolve_scope needed at call time)
# ---------------------------------------------------------------------------


class TestListSystems:
    """Cover list_systems handler (lines 92-93)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "list_systems")
        result = await tool.handler()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        mock_client.list_systems.assert_awaited_once()


class TestGetSystem:
    """Cover get_system handler (lines 105-106)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_system")
        result = await tool.handler(system_id="sys-1")
        parsed = json.loads(result)
        assert parsed["id"] == "sys-1"
        mock_client.get_system.assert_awaited_once_with("sys-1")


class TestGetComplianceStatus:
    """Cover get_compliance_status handler (lines 122-123)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_compliance_status")
        result = await tool.handler(system_id="sys-1")
        parsed = json.loads(result)
        assert parsed["status"] == "partial"
        mock_client.get_system_compliance_status.assert_awaited_once_with("sys-1")


class TestListFrameworks:
    """Cover list_frameworks handler (lines 141-142)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "list_frameworks")
        result = await tool.handler()
        parsed = json.loads(result)
        assert "frameworks" in parsed
        mock_client.list_frameworks.assert_awaited_once()


class TestGetControl:
    """Cover get_control handler (lines 154-155)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_control")
        result = await tool.handler(framework_id="fw-1", control_id="ac-2")
        parsed = json.loads(result)
        assert parsed["id"] == "ac-02"
        mock_client.get_control.assert_awaited()


class TestGetControlsBatch:
    """Cover get_controls_batch handler (lines 158-160)."""

    async def test_with_control_ids(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_controls_batch")
        result = await tool.handler(framework_id="fw-1", control_ids=["ac-2", "sc-7"])
        parsed = json.loads(result)
        assert "controls" in parsed
        mock_client.get_controls_batch.assert_awaited_once()

    async def test_without_control_ids(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_controls_batch")
        result = await tool.handler(framework_id="fw-1")
        parsed = json.loads(result)
        assert "controls" in parsed
        mock_client.get_controls_batch.assert_awaited()


# ---------------------------------------------------------------------------
# Tools that call _resolve_scope at runtime
# ---------------------------------------------------------------------------


class TestSearchEvidence:
    """Cover search_evidence handler (lines 205-215)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "search_evidence")
            result = await tool.handler(control_id="ac-2")

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        mock_client.list_evidence.assert_awaited_once()

    async def test_no_control_id(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "search_evidence")
            result = await tool.handler()

        parsed = json.loads(result)
        assert isinstance(parsed, list)


class TestCreateEvidence:
    """Cover create_evidence handler (lines 244-264)."""

    async def test_happy_path(self, mock_client: AsyncMock) -> None:
        """Create evidence with a control_id to exercise the validation branch."""
        from pretorin.workflows.compliance_updates import EvidenceUpsertResult

        upsert_result = EvidenceUpsertResult(
            evidence_id="ev-42",
            created=True,
            linked=True,
            match_basis="none",
        )

        with (
            patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx,
            patch(_UPSERT, new_callable=AsyncMock) as mock_upsert,
        ):
            mock_ctx.return_value = ("sys-1", "fw-1")
            mock_upsert.return_value = upsert_result
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "create_evidence")
            result = await tool.handler(
                name="Test Evidence",
                description="A description",
                control_id="ac-2",
                evidence_type="policy_document",
            )

        parsed = json.loads(result)
        assert parsed["id"] == "ev-42"
        assert parsed["evidence_id"] == "ev-42"

    async def test_value_error_path(self, mock_client: AsyncMock) -> None:
        """ValueError during create_evidence returns a JSON error."""
        with (
            patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx,
            patch(_UPSERT, new_callable=AsyncMock) as mock_upsert,
        ):
            mock_ctx.return_value = ("sys-1", "fw-1")
            mock_upsert.side_effect = ValueError("bad input")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "create_evidence")
            result = await tool.handler(
                name="Bad", description="Nope", evidence_type="policy_document"
            )

        parsed = json.loads(result)
        assert parsed["error"] == "bad input"


class TestCreateEvidenceBatch:
    """Cover create_evidence_batch handler (lines 298-316)."""

    async def test_happy_path(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "create_evidence_batch")
            items = [
                {
                    "name": "Ev 1",
                    "description": "Desc 1",
                    "control_id": "ac-2",
                    "evidence_type": "policy_document",
                    "relevance_notes": "relevant",
                },
                {
                    "name": "Ev 2",
                    "description": "Desc 2",
                    "control_id": "sc-7",
                },
            ]
            result = await tool.handler(items=items)

        parsed = json.loads(result)
        assert "results" in parsed
        mock_client.create_evidence_batch.assert_awaited_once()
        assert mock_client.get_control.await_count >= 2


class TestLinkEvidence:
    """Cover link_evidence handler (lines 354-365) and _resolve_scoped_control (lines 84-87)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "link_evidence")
            result = await tool.handler(evidence_id="ev-1", control_id="ac-2")

        parsed = json.loads(result)
        assert parsed["linked"] is True
        mock_client.link_evidence_to_control.assert_awaited_once()


class TestGetNarrative:
    """Cover get_narrative handler (lines 392-393)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_narrative")
        result = await tool.handler(system_id="sys-1", control_id="ac-2", framework_id="fw-1")
        parsed = json.loads(result)
        assert parsed["control_id"] == "ac-02"
        mock_client.get_narrative.assert_awaited_once()


class TestAddControlNote:
    """Cover add_control_note handler (lines 418-425)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "add_control_note")
        result = await tool.handler(
            system_id="sys-1",
            control_id="ac-2",
            framework_id="fw-1",
            content="Test note",
        )
        parsed = json.loads(result)
        assert parsed["id"] == "note-1"
        mock_client.add_control_note.assert_awaited_once()


class TestGetControlNotes:
    """Cover get_control_notes handler (lines 450-466) and _resolve_scoped_control."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "get_control_notes")
            result = await tool.handler(control_id="ac-2")

        parsed = json.loads(result)
        assert parsed["control_id"] == "ac-02"
        assert parsed["framework_id"] == "fw-1"
        assert parsed["total"] == 0
        assert parsed["notes"] == []
        mock_client.list_control_notes.assert_awaited_once()


class TestPushMonitoringEvent:
    """Cover push_monitoring_event handler (lines 496-512)."""

    async def test_happy_path_no_control(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "push_monitoring_event")
            result = await tool.handler(title="Scan Complete")

        parsed = json.loads(result)
        assert parsed["id"] == "event-1"
        mock_client.create_monitoring_event.assert_awaited_once()

    async def test_happy_path_with_control(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "push_monitoring_event")
            result = await tool.handler(
                title="Scan Complete",
                control_id="ac-2",
                severity="high",
                event_type="vulnerability_scan",
                description="Found issues",
            )

        parsed = json.loads(result)
        assert parsed["id"] == "event-1"
        mock_client.get_control.assert_awaited()


class TestUpdateControlStatus:
    """Cover update_control_status handler (lines 543-554)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
            tool = _find_tool(tools, "update_control_status")
            result = await tool.handler(control_id="ac-2", status="implemented")

        parsed = json.loads(result)
        assert parsed["status"] == "implemented"
        mock_client.update_control_status.assert_awaited_once()


class TestGetControlImplementation:
    """Cover get_control_implementation handler (lines 579-584)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_control_implementation")
        result = await tool.handler(
            system_id="sys-1", control_id="ac-2", framework_id="fw-1"
        )
        parsed = json.loads(result)
        assert parsed["control_id"] == "ac-02"
        mock_client.get_control_implementation.assert_awaited_once()


class TestGetControlContext:
    """Cover get_control_context handler (lines 610-611)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_control_context")
        result = await tool.handler(system_id="sys-1", control_id="ac-2", framework_id="fw-1")
        parsed = json.loads(result)
        assert parsed["control_id"] == "ac-02"
        mock_client.get_control_context.assert_awaited_once()


class TestGetScope:
    """Cover get_scope handler (lines 633-634)."""

    async def test_returns_json(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_scope")
        result = await tool.handler(system_id="sys-1", framework_id="fw-1")
        parsed = json.loads(result)
        assert parsed["scope_status"] == "completed"
        mock_client.get_scope.assert_awaited_once_with("sys-1", "fw-1")


class TestUpdateNarrative:
    """Cover update_narrative handler (lines 671-681)."""

    async def test_happy_path(self, mock_client: AsyncMock) -> None:
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "update_narrative")
        result = await tool.handler(
            system_id="sys-1",
            control_id="ac-2",
            framework_id="fw-1",
            narrative="Updated text",
            is_ai_generated=True,
        )
        parsed = json.loads(result)
        assert parsed["ok"] is True
        mock_client.update_narrative.assert_awaited_once()

    async def test_value_error_path(self, mock_client: AsyncMock) -> None:
        """ValueError during update_narrative returns a JSON error."""
        mock_client.update_narrative.side_effect = ValueError("invalid narrative")
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "update_narrative")
        result = await tool.handler(
            system_id="sys-1",
            control_id="ac-2",
            framework_id="fw-1",
            narrative="Bad text",
        )
        parsed = json.loads(result)
        assert parsed["error"] == "invalid narrative"


# ---------------------------------------------------------------------------
# _normalize helper (line 66 — None branch)
# ---------------------------------------------------------------------------


class TestNormalizeBranch:
    """Cover the None-return branch in _normalize (line 66)."""

    async def test_normalize_none_via_get_controls_batch(
        self, mock_client: AsyncMock,
    ) -> None:
        """get_controls_batch with control_ids=None exercises _normalize(None) -> None path."""
        with patch(_RESOLVE_CTX, new_callable=AsyncMock) as mock_ctx:
            mock_ctx.return_value = ("sys-1", "fw-1")
            tools = create_platform_tools(mock_client)
        tool = _find_tool(tools, "get_controls_batch")
        result = await tool.handler(framework_id="fw-1", control_ids=None)
        parsed = json.loads(result)
        assert "controls" in parsed
        mock_client.get_controls_batch.assert_awaited_once_with("fw-1", None)
