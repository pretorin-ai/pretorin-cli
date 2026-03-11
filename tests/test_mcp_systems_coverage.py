"""Coverage tests for src/pretorin/mcp/handlers/systems.py.

Covers line 42 (list_systems no systems note), line 60 (get_system system_id None),
line 81 (get_compliance_status system_id None).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.systems import (
    handle_get_compliance_status,
    handle_get_system,
    handle_list_systems,
)


def _make_client(**overrides) -> AsyncMock:
    """Build a mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


class TestHandleListSystems:
    """Tests for handle_list_systems."""

    @pytest.mark.asyncio
    async def test_no_systems_adds_note(self):
        """Line 42: when no systems, result contains 'note' key."""
        client = _make_client(list_systems=[])
        result = await handle_list_systems(client, {})
        text = result[0].text
        assert '"note"' in text
        assert "No systems found" in text
        assert "beta code" in text

    @pytest.mark.asyncio
    async def test_with_systems_no_note(self):
        """When systems exist, no note is added."""
        client = _make_client(
            list_systems=[{"id": "sys-1", "name": "My System", "description": "Test"}]
        )
        result = await handle_list_systems(client, {})
        text = result[0].text
        assert "sys-1" in text
        assert '"note"' not in text


class TestHandleGetSystem:
    """Tests for handle_get_system."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Line 60: system_id resolves to None raises PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.systems.resolve_system_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_get_system(client, {"system_id": "test"})


class TestHandleGetComplianceStatus:
    """Tests for handle_get_compliance_status."""

    @pytest.mark.asyncio
    async def test_system_id_none_raises(self):
        """Line 81: system_id resolves to None raises PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.systems.resolve_system_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_get_compliance_status(client, {"system_id": "test"})
