"""Coverage tests for src/pretorin/mcp/handlers/evidence.py.

Covers line 74 (format_error missing name/description), line 79 (invalid evidence_type),
lines 95-96 (ValueError during upsert_evidence), line 110 (missing items),
line 119 (invalid evidence_type in batch), line 142 (missing evidence_id/control_id),
line 170 (PretorianClientError in get_narrative).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from mcp.types import CallToolResult

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.evidence import (
    handle_create_evidence,
    handle_create_evidence_batch,
    handle_delete_evidence,
    handle_get_narrative,
    handle_link_evidence,
)


def _make_client(**overrides) -> AsyncMock:
    """Build a mock PretorianClient."""
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _is_error(result) -> bool:
    return isinstance(result, CallToolResult) and result.isError is True


def _error_text(result) -> str:
    assert isinstance(result, CallToolResult)
    return " ".join(c.text for c in result.content)


class TestHandleCreateEvidence:
    """Tests for handle_create_evidence."""

    @pytest.mark.asyncio
    async def test_missing_name_returns_error(self):
        """Line 74: missing name/description returns format_error."""
        client = _make_client()
        result = await handle_create_evidence(client, {"description": "test"})
        assert _is_error(result)
        assert "name" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_description_returns_error(self):
        """Line 74: missing description returns format_error."""
        client = _make_client()
        result = await handle_create_evidence(client, {"name": "test"})
        assert _is_error(result)
        assert "description" in _error_text(result)

    @pytest.mark.asyncio
    async def test_invalid_evidence_type_returns_error(self):
        """Line 79: invalid evidence_type returns format_error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ):
            result = await handle_create_evidence(
                client,
                {
                    "name": "Test",
                    "description": "Desc",
                    "evidence_type": "INVALID_TYPE",
                },
            )
        assert _is_error(result)
        assert "evidence_type" in _error_text(result)

    @pytest.mark.asyncio
    async def test_value_error_during_upsert(self):
        """Lines 95-96: ValueError from upsert_evidence returns format_error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", "ac-02")),
        ), patch(
            "pretorin.mcp.handlers.evidence.upsert_evidence",
            new=AsyncMock(side_effect=ValueError("framework_id is required")),
        ):
            result = await handle_create_evidence(
                client,
                {
                    "name": "Test",
                    "description": "Desc",
                    "evidence_type": "policy_document",
                },
            )
        assert _is_error(result)
        assert "framework_id is required" in _error_text(result)


class TestHandleCreateEvidenceBatch:
    """Tests for handle_create_evidence_batch."""

    @pytest.mark.asyncio
    async def test_missing_items_returns_error(self):
        """Line 110: missing items returns format_error."""
        client = _make_client()
        result = await handle_create_evidence_batch(client, {})
        assert _is_error(result)
        assert "items" in _error_text(result)

    @pytest.mark.asyncio
    async def test_invalid_evidence_type_in_batch(self):
        """Line 119: invalid evidence_type in batch item returns format_error."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", None)),
        ):
            result = await handle_create_evidence_batch(
                client,
                {
                    "items": [
                        {
                            "name": "Test",
                            "description": "Desc",
                            "control_id": "ac-02",
                            "evidence_type": "BAD_TYPE",
                        }
                    ],
                },
            )
        assert _is_error(result)
        assert "evidence_type" in _error_text(result)


class TestHandleLinkEvidence:
    """Tests for handle_link_evidence."""

    @pytest.mark.asyncio
    async def test_missing_evidence_id_returns_error(self):
        """Line 142: missing evidence_id/control_id returns format_error."""
        client = _make_client()
        result = await handle_link_evidence(client, {"control_id": "ac-02"})
        assert _is_error(result)
        assert "evidence_id" in _error_text(result)

    @pytest.mark.asyncio
    async def test_missing_control_id_returns_error(self):
        """Line 142: missing control_id returns format_error."""
        client = _make_client()
        result = await handle_link_evidence(client, {"evidence_id": "ev-1"})
        assert _is_error(result)
        assert "control_id" in _error_text(result)


class TestHandleDeleteEvidence:
    """Tests for handle_delete_evidence."""

    @pytest.mark.asyncio
    async def test_missing_evidence_id_returns_error(self):
        """Missing evidence_id returns format_error."""
        client = _make_client()
        result = await handle_delete_evidence(client, {})
        assert _is_error(result)
        assert "evidence_id" in _error_text(result)

    @pytest.mark.asyncio
    async def test_success_returns_deleted_payload(self):
        """Successful delete returns evidence_id and deleted flag."""
        client = _make_client()
        client.delete_evidence = AsyncMock(return_value=None)
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", None)),
        ):
            result = await handle_delete_evidence(
                client, {"evidence_id": "ev-abc123"}
            )
        assert not isinstance(result, CallToolResult)
        import json

        text = result[0].text
        payload = json.loads(text)
        assert payload["evidence_id"] == "ev-abc123"
        assert payload["deleted"] is True

    @pytest.mark.asyncio
    async def test_client_error_bubbles_up(self):
        """PretorianClientError from delete should propagate."""
        client = _make_client()
        client.delete_evidence = AsyncMock(
            side_effect=PretorianClientError("Not found")
        )
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(return_value=("sys-1", "fedramp-moderate", None)),
        ):
            with pytest.raises(PretorianClientError, match="Not found"):
                await handle_delete_evidence(
                    client, {"evidence_id": "ev-abc123"}
                )


class TestHandleGetNarrative:
    """Tests for handle_get_narrative."""

    @pytest.mark.asyncio
    async def test_client_error_in_get_narrative(self):
        """Scope resolution failures should bubble up as PretorianClientError."""
        client = _make_client()
        with patch(
            "pretorin.mcp.handlers.evidence.resolve_execution_scope",
            new=AsyncMock(side_effect=PretorianClientError("system_id is required")),
        ):
            with pytest.raises(PretorianClientError, match="system_id is required"):
                await handle_get_narrative(
                    client,
                    {
                        "system_id": "sys-1",
                        "control_id": "ac-02",
                        "framework_id": "fedramp-moderate",
                    },
                )

    @pytest.mark.asyncio
    async def test_missing_required_returns_error(self):
        """Missing required params returns format_error."""
        client = _make_client()
        result = await handle_get_narrative(client, {})
        assert _is_error(result)
        assert "Missing required" in _error_text(result)
