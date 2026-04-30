"""Coverage tests for src/pretorin/mcp/handlers/systems.py.

Covers: list_systems (no systems note), get_system/get_compliance_status
(system_id None), get_source_manifest (all branches), get_cli_status.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.mcp.handlers.systems import (
    handle_get_cli_status,
    handle_get_compliance_status,
    handle_get_source_manifest,
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
        client = _make_client(list_systems=[{"id": "sys-1", "name": "My System", "description": "Test"}])
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


# =============================================================================
# handle_get_source_manifest
# =============================================================================


class TestHandleGetSourceManifest:
    """Tests for handle_get_source_manifest."""

    @pytest.mark.asyncio
    async def test_no_system_id_raises(self):
        """Raises PretorianClientError when no system_id and no active context."""
        with patch("pretorin.client.config.Config") as mock_config_cls:
            mock_config_cls.return_value.active_system_id = None
            with pytest.raises(PretorianClientError, match="No system_id"):
                await handle_get_source_manifest(None, {})

    @pytest.mark.asyncio
    async def test_no_manifest_found(self):
        """Returns helpful message when no manifest file exists."""
        with (
            patch("pretorin.client.config.Config") as mock_config_cls,
            patch("pretorin.attestation.load_manifest", return_value=None),
        ):
            mock_config_cls.return_value.active_system_id = "sys-1"
            result = await handle_get_source_manifest(None, {})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["manifest"] is None
        assert "No source manifest found" in parsed["message"]

    @pytest.mark.asyncio
    async def test_manifest_without_framework(self):
        """Returns manifest data without evaluation when no active framework."""
        mock_manifest = MagicMock()
        mock_manifest.version = "1.0"
        mock_manifest.system_sources = []
        mock_manifest.family_sources = {}

        with (
            patch("pretorin.client.config.Config") as mock_config_cls,
            patch(
                "pretorin.attestation.load_manifest",
                return_value=mock_manifest,
            ),
        ):
            mock_config_cls.return_value.active_system_id = "sys-1"
            mock_config_cls.return_value.active_framework_id = None
            result = await handle_get_source_manifest(None, {})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["version"] == "1.0"
        assert "evaluation" not in parsed

    @pytest.mark.asyncio
    async def test_manifest_with_evaluation(self):
        """Returns manifest data with evaluation when snapshot exists."""
        mock_manifest = MagicMock()
        mock_manifest.version = "1.0"
        mock_manifest.system_sources = []
        mock_manifest.family_sources = {}

        mock_snap = MagicMock()
        mock_snap.sources = []

        mock_eval = MagicMock()
        mock_eval.status.value = "verified"
        mock_eval.satisfied = []
        mock_eval.missing_required = []
        mock_eval.missing_recommended = []

        with (
            patch("pretorin.client.config.Config") as mock_config_cls,
            patch(
                "pretorin.attestation.load_manifest",
                return_value=mock_manifest,
            ),
            patch(
                "pretorin.attestation.load_snapshot",
                return_value=mock_snap,
            ),
            patch(
                "pretorin.attestation.evaluate_manifest",
                return_value=mock_eval,
            ),
        ):
            mock_config_cls.return_value.active_system_id = "sys-1"
            mock_config_cls.return_value.active_framework_id = "fedramp-moderate"
            result = await handle_get_source_manifest(None, {})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["evaluation"]["status"] == "verified"

    @pytest.mark.asyncio
    async def test_manifest_no_snapshot(self):
        """Returns no_snapshot evaluation when snapshot file doesn't exist."""
        mock_manifest = MagicMock()
        mock_manifest.version = "1.0"
        mock_manifest.system_sources = []
        mock_manifest.family_sources = {}

        with (
            patch("pretorin.client.config.Config") as mock_config_cls,
            patch(
                "pretorin.attestation.load_manifest",
                return_value=mock_manifest,
            ),
            patch(
                "pretorin.attestation.load_snapshot",
                return_value=None,
            ),
        ):
            mock_config_cls.return_value.active_system_id = "sys-1"
            mock_config_cls.return_value.active_framework_id = "fedramp-moderate"
            result = await handle_get_source_manifest(None, {})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["evaluation"]["status"] == "no_snapshot"

    @pytest.mark.asyncio
    async def test_system_id_from_arguments(self):
        """Uses system_id from arguments when provided."""
        with (
            patch("pretorin.client.config.Config") as mock_config_cls,
            patch("pretorin.attestation.load_manifest", return_value=None),
        ):
            mock_config_cls.return_value.active_system_id = "default-sys"
            result = await handle_get_source_manifest(None, {"system_id": "explicit-sys"})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["system_id"] == "explicit-sys"


# =============================================================================
# handle_get_cli_status
# =============================================================================


class TestHandleGetCliStatus:
    """Tests for handle_get_cli_status."""

    @pytest.mark.asyncio
    async def test_returns_status(self):
        """Returns CLI update status as JSON."""
        mock_status = {"current_version": "1.0.0", "update_available": False}
        with patch(
            "pretorin.mcp.handlers.systems.get_update_status",
            return_value=mock_status,
        ):
            result = await handle_get_cli_status(None, {})

        text = result[0].text
        parsed = json.loads(text)
        assert parsed["current_version"] == "1.0.0"

    @pytest.mark.asyncio
    async def test_force_flag(self):
        """Passes force flag from arguments."""
        mock_status = {"current_version": "1.0.0"}
        with patch(
            "pretorin.mcp.handlers.systems.get_update_status",
            return_value=mock_status,
        ) as mock_get:
            await handle_get_cli_status(None, {"force": True})
            mock_get.assert_called_once_with(force=True)
