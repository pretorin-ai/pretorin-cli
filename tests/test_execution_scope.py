"""Tests for run-local ExecutionScope threading."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from pretorin.scope import ExecutionScope

# ---------------------------------------------------------------------------
# ExecutionScope basics
# ---------------------------------------------------------------------------


def test_execution_scope_is_frozen() -> None:
    scope = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    with pytest.raises(AttributeError):
        scope.system_id = "sys-2"  # type: ignore[misc]


def test_execution_scope_equality() -> None:
    a = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    b = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    assert a == b


def test_execution_scope_hashable() -> None:
    scope = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    assert hash(scope) == hash(ExecutionScope(system_id="sys-1", framework_id="fw-1"))


# ---------------------------------------------------------------------------
# resolve_execution_context — scope bypass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_execution_context_uses_scope_directly() -> None:
    """When scope is provided, resolve_execution_context returns it without API calls."""
    from pretorin.cli.context import resolve_execution_context

    client = AsyncMock()
    scope = ExecutionScope(system_id="sys-1", framework_id="fedramp-moderate")

    system_id, framework_id = await resolve_execution_context(client, scope=scope)

    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"
    # No API calls should be made when scope is provided
    client.list_systems.assert_not_called()
    client.get_system_compliance_status.assert_not_called()


@pytest.mark.asyncio
async def test_resolve_execution_context_explicit_flags_override_scope() -> None:
    """Explicit system/framework flags take priority over scope."""
    from pretorin.cli.context import resolve_execution_context

    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-2", "name": "Other System"}])
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "nist-800-53-r5"}]})
    scope = ExecutionScope(system_id="sys-1", framework_id="fedramp-moderate")

    system_id, framework_id = await resolve_execution_context(
        client,
        system="sys-2",
        framework="nist-800-53-r5",
        scope=scope,
    )

    assert system_id == "sys-2"
    assert framework_id == "nist-800-53-r5"


# ---------------------------------------------------------------------------
# _resolve_context_values — scope bypass
# ---------------------------------------------------------------------------


def test_resolve_context_values_uses_scope() -> None:
    from pretorin.cli.context import _resolve_context_values

    scope = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    system_id, framework_id = _resolve_context_values(scope=scope)

    assert system_id == "sys-1"
    assert framework_id == "fw-1"


def test_resolve_context_values_flags_override_scope() -> None:
    from pretorin.cli.context import _resolve_context_values

    scope = ExecutionScope(system_id="sys-1", framework_id="fw-1")
    # When explicit flags are provided, scope is not used
    system_id, framework_id = _resolve_context_values(system="sys-2", framework="fw-2", scope=scope)

    assert system_id == "sys-2"
    assert framework_id == "fw-2"


# ---------------------------------------------------------------------------
# Sync classes — explicit system_id
# ---------------------------------------------------------------------------


class _DummyConfig:
    active_system_id = "config-sys"


def test_evidence_sync_accepts_explicit_system_id(tmp_path: Path) -> None:
    from pretorin.evidence.sync import EvidenceSync

    sync = EvidenceSync(evidence_dir=tmp_path, system_id="explicit-sys")
    assert sync._system_id == "explicit-sys"


def test_narrative_sync_accepts_explicit_system_id(tmp_path: Path) -> None:
    from pretorin.narrative.sync import NarrativeSync

    sync = NarrativeSync(narrative_dir=tmp_path, system_id="explicit-sys")
    assert sync._system_id == "explicit-sys"


def test_notes_sync_accepts_explicit_system_id(tmp_path: Path) -> None:
    from pretorin.notes.sync import NotesSync

    sync = NotesSync(notes_dir=tmp_path, system_id="explicit-sys")
    assert sync._system_id == "explicit-sys"


def test_evidence_sync_falls_back_to_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pretorin.client.config.Config", _DummyConfig)

    from pretorin.evidence.sync import EvidenceSync

    sync = EvidenceSync(evidence_dir=tmp_path)
    assert sync._system_id == "config-sys"


def test_evidence_sync_raises_when_no_system(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _NoSystemConfig:
        active_system_id = None

    monkeypatch.setattr("pretorin.client.config.Config", _NoSystemConfig)

    from pretorin.evidence.sync import EvidenceSync

    with pytest.raises(ValueError, match="No active system set"):
        EvidenceSync(evidence_dir=tmp_path)


# ---------------------------------------------------------------------------
# resolve_system — scope bypass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_system_uses_scope_over_config() -> None:
    from pretorin.workflows.compliance_updates import resolve_system

    client = AsyncMock()
    client.list_systems = AsyncMock(
        return_value=[
            {"id": "sys-scope", "name": "Scope System"},
            {"id": "sys-config", "name": "Config System"},
        ]
    )
    scope = ExecutionScope(system_id="sys-scope", framework_id="fw-1")

    system_id, system_name = await resolve_system(client, scope=scope)

    assert system_id == "sys-scope"
    assert system_name == "Scope System"


@pytest.mark.asyncio
async def test_resolve_system_explicit_arg_takes_priority_over_scope() -> None:
    from pretorin.workflows.compliance_updates import resolve_system

    client = AsyncMock()
    client.list_systems = AsyncMock(
        return_value=[
            {"id": "sys-scope", "name": "Scope System"},
            {"id": "sys-explicit", "name": "Explicit System"},
        ]
    )
    scope = ExecutionScope(system_id="sys-scope", framework_id="fw-1")

    system_id, system_name = await resolve_system(client, system="sys-explicit", scope=scope)

    assert system_id == "sys-explicit"
    assert system_name == "Explicit System"


# ---------------------------------------------------------------------------
# MCP resolve_execution_scope — scope threading
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_resolve_execution_scope_threads_scope() -> None:
    from pretorin.mcp.helpers import resolve_execution_scope

    client = AsyncMock()
    scope = ExecutionScope(system_id="sys-1", framework_id="fedramp-moderate")

    system_id, framework_id, control_id = await resolve_execution_scope(client, {}, scope=scope)

    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"
    assert control_id is None
    client.list_systems.assert_not_called()


# ---------------------------------------------------------------------------
# Agent tools — scope threading
# ---------------------------------------------------------------------------


def test_create_platform_tools_accepts_scope() -> None:
    from pretorin.agent.tools import create_platform_tools

    client = AsyncMock()
    scope = ExecutionScope(system_id="sys-1", framework_id="fw-1")

    tools = create_platform_tools(client, scope=scope)
    assert len(tools) > 0
    # Verify tool names are present
    tool_names = {t.name for t in tools}
    assert "search_evidence" in tool_names
    assert "create_evidence" in tool_names
