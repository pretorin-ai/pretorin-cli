"""Coverage tests for src/pretorin/evidence/sync.py.

Covers line 29 (SyncResult.total), line 41 (ValueError when no active system),
lines 67-69 (skip already-synced), lines 72-73 (dry-run mode),
lines 100-104 (sync error handling), line 119 (_update_frontmatter no frontmatter).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.evidence.sync import EvidenceSync, SyncResult
from pretorin.evidence.writer import EvidenceWriter, LocalEvidence


class _DummyConfigNoSystem:
    active_system_id = ""


class _DummyConfigWithSystem:
    active_system_id = "sys-1"


class TestSyncResultTotal:
    """Tests for SyncResult.total property."""

    def test_total_counts_all_categories(self):
        """Line 29: total property sums all categories."""
        result = SyncResult(
            created=["a", "b"],
            reused=["c"],
            skipped=["d", "e", "f"],
            errors=["g"],
        )
        assert result.total == 7

    def test_total_zero_when_empty(self):
        result = SyncResult()
        assert result.total == 0


class TestEvidenceSyncInit:
    """Tests for EvidenceSync.__init__."""

    def test_raises_value_error_when_no_active_system(self, monkeypatch):
        """Line 41: raises ValueError when no active system set."""
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigNoSystem)
        with pytest.raises(ValueError, match="No active system set"):
            EvidenceSync()


class TestPushSkipAlreadySynced:
    """Tests for push() skipping already-synced evidence."""

    @pytest.mark.asyncio
    async def test_skip_already_synced_evidence(self, monkeypatch, tmp_path):
        """Lines 67-69: evidence with platform_id is skipped."""
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)

        sync = EvidenceSync(evidence_dir=tmp_path)
        # Mock list_local to return evidence with platform_id
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test Evidence",
            description="Already synced",
            evidence_type="policy_document",
            platform_id="plat-123",
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [ev]

        client = AsyncMock()
        result = await sync.push(client)

        assert len(result.skipped) == 1
        assert "fedramp-moderate/ac-02/Test Evidence" in result.skipped[0]
        assert len(result.created) == 0


class TestPushDryRun:
    """Tests for push() dry-run mode."""

    @pytest.mark.asyncio
    async def test_dry_run_does_not_create(self, monkeypatch, tmp_path):
        """Lines 72-73: dry-run records but doesn't actually create."""
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)

        sync = EvidenceSync(evidence_dir=tmp_path)
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="New Evidence",
            description="Should not be created",
            evidence_type="policy_document",
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [ev]

        client = AsyncMock()
        result = await sync.push(client, dry_run=True)

        assert len(result.created) == 1
        assert "[dry-run]" in result.created[0]
        client.create_evidence.assert_not_called()


class TestPushErrorHandling:
    """Tests for push() error handling."""

    @pytest.mark.asyncio
    async def test_sync_error_captured_in_errors(self, monkeypatch, tmp_path):
        """Lines 100-104: exceptions during sync are captured in errors list."""
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)

        sync = EvidenceSync(evidence_dir=tmp_path)
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Failing Evidence",
            description="Will fail",
            evidence_type="policy_document",
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [ev]

        with patch(
            "pretorin.evidence.sync.upsert_evidence",
            new=AsyncMock(side_effect=RuntimeError("API down")),
        ):
            client = AsyncMock()
            result = await sync.push(client)

        assert len(result.errors) == 1
        assert "API down" in result.errors[0]


class TestUpdateFrontmatter:
    """Tests for _update_frontmatter."""

    def test_update_frontmatter_no_frontmatter_delimiters(self, tmp_path):
        """Line 119: file doesn't start with --- so no update occurs."""
        file_path = tmp_path / "evidence.md"
        file_path.write_text("No frontmatter here\n\n# Evidence\n\nContent")

        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test",
            description="Desc",
            evidence_type="policy_document",
            platform_id="plat-1",
            path=file_path,
        )
        EvidenceSync._update_frontmatter(ev)

        # File should remain unchanged
        assert file_path.read_text() == "No frontmatter here\n\n# Evidence\n\nContent"

    def test_update_frontmatter_with_valid_frontmatter(self, tmp_path):
        """Updates frontmatter when file has valid --- delimiters."""
        file_path = tmp_path / "evidence.md"
        file_path.write_text(
            "---\ncontrol_id: ac-02\nframework_id: fedramp-moderate\n"
            "evidence_type: configuration\nstatus: draft\n"
            "collected_at: 2026-01-01T00:00:00\n---\n\n# Test\n\nBody"
        )

        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test",
            description="Desc",
            evidence_type="configuration",
            platform_id="plat-new",
            path=file_path,
        )
        EvidenceSync._update_frontmatter(ev)

        updated_content = file_path.read_text()
        assert "platform_id: plat-new" in updated_content

    def test_update_frontmatter_file_not_exists(self, tmp_path):
        """No-op when path doesn't exist."""
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test",
            description="Desc",
            evidence_type="policy_document",
            platform_id="plat-1",
            path=tmp_path / "nonexistent.md",
        )
        # Should not raise
        EvidenceSync._update_frontmatter(ev)

    def test_update_frontmatter_no_path(self):
        """No-op when path is None."""
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test",
            description="Desc",
            evidence_type="policy_document",
            platform_id="plat-1",
            path=None,
        )
        EvidenceSync._update_frontmatter(ev)
