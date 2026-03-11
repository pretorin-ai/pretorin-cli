"""Additional coverage tests for src/pretorin/mcp/handlers/compliance.py.

Covers line 144 (add_control_note system_id None), line 194 (update_narrative
system_id None), line 248 (get_control_implementation system_id None).
"""

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
    """Tests for handle_add_control_note when system_id is None."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Line 144: system_id resolves to None raises PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_system_id",
            new=AsyncMock(return_value=None),
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
    """Tests for handle_update_narrative when system_id is None."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Line 194: system_id resolves to None raises PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_system_id",
            new=AsyncMock(return_value=None),
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
    """Tests for handle_get_control_implementation when system_id is None."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Line 248: system_id resolves to None raises PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.compliance.resolve_system_id",
            new=AsyncMock(return_value=None),
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
