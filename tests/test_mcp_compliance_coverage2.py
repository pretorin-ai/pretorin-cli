"""Additional coverage tests for src/pretorin/mcp/handlers/compliance.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.compliance import (
    handle_add_control_note,
    handle_get_control_implementation,
    handle_update_narrative,
)


def _make_client(**overrides) -> AsyncMock:
    """Build a mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


class TestAddControlNoteSystemIdNone:
    """Tests for handle_add_control_note when scope resolution fails."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Scope resolution failure should surface as a client error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(side_effect=PretorianClientError("system_id is required")),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_add_control_note(
                    client,
                    {
                        "system_id": "sys-1",
                        "control_id": "ac-02",
                        "framework_id": "fedramp-moderate",
                        "content": "Test note",
                    },
                )


class TestUpdateNarrativeSystemIdNone:
    """Tests for handle_update_narrative when scope resolution fails."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Scope resolution failure should surface as a client error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(side_effect=PretorianClientError("system_id is required")),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_update_narrative(
                    client,
                    {
                        "system_id": "sys-1",
                        "control_id": "ac-02",
                        "framework_id": "fedramp-moderate",
                        "narrative": "The system implements RBAC.",
                    },
                )


class TestGetControlImplementationSystemIdNone:
    """Tests for handle_get_control_implementation when scope resolution fails."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Scope resolution failure should surface as a client error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_execution_scope",
            new=AsyncMock(side_effect=PretorianClientError("system_id is required")),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_get_control_implementation(
                    client,
                    {
                        "system_id": "sys-1",
                        "control_id": "ac-02",
                        "framework_id": "fedramp-moderate",
                    },
                )
