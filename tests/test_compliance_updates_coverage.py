"""Coverage tests for src/pretorin/workflows/compliance_updates.py.

Covers lines 94-96 (_sort_key_collected_at ValueError), line 119 (to_dict link_error),
line 130 (resolve_system no systems), lines 139-150 (resolve_system variants),
lines 236-237 (link_evidence exception in upsert_evidence), line 255 (link_error log).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.client.models import EvidenceItemResponse
from pretorin.workflows.compliance_updates import (
    EvidenceUpsertResult,
    _sort_key_collected_at,
    resolve_system,
    upsert_evidence,
)


class TestSortKeyCollectedAt:
    """Tests for _sort_key_collected_at."""

    def test_valid_timestamp(self):
        item = EvidenceItemResponse(
            id="ev-1",
            name="Test",
            description="Desc",
            evidence_type="configuration",
            collected_at="2026-01-15T10:00:00+00:00",
        )
        priority, value = _sort_key_collected_at(item)
        assert priority == 1

    def test_invalid_timestamp_falls_back(self):
        """Lines 94-96: ValueError path when collected_at is unparseable."""
        item = EvidenceItemResponse(
            id="ev-1",
            name="Test",
            description="Desc",
            evidence_type="configuration",
            collected_at="not-a-date",
        )
        priority, value = _sort_key_collected_at(item)
        assert priority == 0
        assert value == "ev-1"

    def test_no_collected_at(self):
        item = EvidenceItemResponse(
            id="ev-2",
            name="Test",
            description="Desc",
            evidence_type="configuration",
            collected_at=None,
        )
        priority, value = _sort_key_collected_at(item)
        assert priority == 0
        assert value == "ev-2"


class TestEvidenceUpsertResultToDict:
    """Tests for EvidenceUpsertResult.to_dict."""

    def test_to_dict_without_link_error(self):
        result = EvidenceUpsertResult(
            evidence_id="ev-1",
            created=True,
            linked=True,
            match_basis="none",
        )
        d = result.to_dict()
        assert d["evidence_id"] == "ev-1"
        assert "link_error" not in d

    def test_to_dict_with_link_error(self):
        """Line 119: to_dict includes link_error when present."""
        result = EvidenceUpsertResult(
            evidence_id="ev-1",
            created=True,
            linked=False,
            match_basis="none",
            link_error="Failed to link",
        )
        d = result.to_dict()
        assert d["link_error"] == "Failed to link"


class TestResolveSystem:
    """Tests for resolve_system."""

    @pytest.mark.asyncio
    async def test_no_systems_raises(self):
        """Line 130: no systems found raises PretorianClientError."""
        client = AsyncMock()
        client.list_systems = AsyncMock(return_value=[])
        with pytest.raises(PretorianClientError, match="No systems found"):
            await resolve_system(client)

    @pytest.mark.asyncio
    async def test_system_hint_matches_by_id(self):
        """resolve_system with matching system ID."""
        client = AsyncMock()
        client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "My System"}])
        sys_id, sys_name = await resolve_system(client, "sys-1")
        assert sys_id == "sys-1"
        assert sys_name == "My System"

    @pytest.mark.asyncio
    async def test_system_hint_matches_by_name_prefix(self):
        """resolve_system with matching system name prefix."""
        client = AsyncMock()
        client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Production System"}])
        sys_id, sys_name = await resolve_system(client, "production")
        assert sys_id == "sys-1"

    @pytest.mark.asyncio
    async def test_system_hint_not_found(self):
        """resolve_system with hint that matches nothing."""
        client = AsyncMock()
        client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Prod"}])
        with pytest.raises(PretorianClientError, match="System not found"):
            await resolve_system(client, "staging")

    @pytest.mark.asyncio
    async def test_active_system_from_config(self):
        """Lines 139-144: active system from Config."""
        client = AsyncMock()
        client.list_systems = AsyncMock(
            return_value=[
                {"id": "sys-1", "name": "System One"},
                {"id": "sys-2", "name": "System Two"},
            ]
        )
        mock_config = MagicMock()
        mock_config.get.return_value = "sys-2"
        with patch("pretorin.workflows.compliance_updates.Config", return_value=mock_config):
            sys_id, sys_name = await resolve_system(client)
        assert sys_id == "sys-2"
        assert sys_name == "System Two"

    @pytest.mark.asyncio
    async def test_single_system_auto_resolves(self):
        """Lines 146-148: single system auto-resolves."""
        client = AsyncMock()
        client.list_systems = AsyncMock(return_value=[{"id": "sys-only", "name": "Only System"}])
        mock_config = MagicMock()
        mock_config.get.return_value = None
        with patch("pretorin.workflows.compliance_updates.Config", return_value=mock_config):
            sys_id, sys_name = await resolve_system(client)
        assert sys_id == "sys-only"

    @pytest.mark.asyncio
    async def test_multiple_systems_no_active_raises(self):
        """Lines 150-152: multiple systems without active system raises."""
        client = AsyncMock()
        client.list_systems = AsyncMock(
            return_value=[
                {"id": "sys-1", "name": "System One"},
                {"id": "sys-2", "name": "System Two"},
            ]
        )
        mock_config = MagicMock()
        mock_config.get.return_value = None
        with patch("pretorin.workflows.compliance_updates.Config", return_value=mock_config):
            with pytest.raises(PretorianClientError, match="Multiple systems"):
                await resolve_system(client)


class TestUpsertEvidenceLinkError:
    """Tests for link_evidence exception path in upsert_evidence."""

    @pytest.mark.asyncio
    async def test_link_evidence_exception_captured(self):
        """Lines 236-237, 255: exception during link_evidence is captured as link_error."""
        client = AsyncMock()
        client.list_evidence = AsyncMock(
            return_value=[
                EvidenceItemResponse(
                    id="ev-existing",
                    name="RBAC Config",
                    description="- Role mapping policy",
                    evidence_type="configuration",
                    collected_at="2026-01-01T00:00:00+00:00",
                )
            ]
        )
        client.link_evidence_to_control = AsyncMock(side_effect=RuntimeError("Link API error"))

        result = await upsert_evidence(
            client,
            system_id="sys-1",
            name="RBAC Config",
            description="- Role mapping policy",
            evidence_type="configuration",
            control_id="ac-2",
            framework_id="fedramp-moderate",
            dedupe=True,
        )

        assert result.created is False
        assert result.linked is False
        assert result.link_error == "Link API error"
