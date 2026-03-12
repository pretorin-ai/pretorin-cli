"""Tests for src/pretorin/narrative/sync.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.narrative.sync import NarrativeSync, SyncResult
from pretorin.narrative.writer import LocalNarrative


class _DummyConfigNoSystem:
    active_system_id = ""


class _DummyConfigWithSystem:
    active_system_id = "sys-1"


class TestSyncResult:
    def test_total(self):
        result = SyncResult(pushed=["a"], skipped=["b", "c"], errors=["d"])
        assert result.total == 4

    def test_empty_total(self):
        assert SyncResult().total == 0


class TestNarrativeSyncInit:
    def test_raises_without_active_system(self, monkeypatch):
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigNoSystem)
        with pytest.raises(ValueError, match="No active system set"):
            NarrativeSync()


class TestPushSkipSynced:
    @pytest.mark.asyncio
    async def test_skip_already_synced(self, monkeypatch, tmp_path):
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)
        sync = NarrativeSync(narrative_dir=tmp_path)
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="test",
            content="content",
            platform_synced=True,
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [narr]

        client = AsyncMock()
        result = await sync.push(client)

        assert len(result.skipped) == 1
        assert len(result.pushed) == 0


class TestPushDryRun:
    @pytest.mark.asyncio
    async def test_dry_run_does_not_push(self, monkeypatch, tmp_path):
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)
        sync = NarrativeSync(narrative_dir=tmp_path)
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="new-narrative",
            content="content",
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [narr]

        client = AsyncMock()
        result = await sync.push(client, dry_run=True)

        assert len(result.pushed) == 1
        assert "[dry-run]" in result.pushed[0]
        client.update_narrative.assert_not_called()


class TestPushErrorHandling:
    @pytest.mark.asyncio
    async def test_error_captured(self, monkeypatch, tmp_path):
        monkeypatch.setattr("pretorin.client.config.Config", _DummyConfigWithSystem)
        sync = NarrativeSync(narrative_dir=tmp_path)
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="failing",
            content="content",
        )
        sync.writer = MagicMock()
        sync.writer.list_local.return_value = [narr]

        client = AsyncMock()
        client.update_narrative = AsyncMock(side_effect=RuntimeError("API down"))
        result = await sync.push(client)

        assert len(result.errors) == 1
        assert "API down" in result.errors[0]


class TestUpdateFrontmatter:
    def test_updates_frontmatter(self, tmp_path):
        file_path = tmp_path / "narrative.md"
        file_path.write_text(
            "---\ncontrol_id: ac-02\nframework_id: fedramp-moderate\n"
            "status: draft\nis_ai_generated: false\nplatform_synced: false\n"
            "created_at: 2026-01-01T00:00:00\n---\n\nContent here"
        )

        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="test",
            content="Content here",
            platform_synced=True,
            path=file_path,
        )
        NarrativeSync._update_frontmatter(narr)
        assert "platform_synced: true" in file_path.read_text()

    def test_no_op_when_no_path(self):
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="test",
            content="c",
            path=None,
        )
        NarrativeSync._update_frontmatter(narr)

    def test_no_op_when_file_missing(self, tmp_path):
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="test",
            content="c",
            path=tmp_path / "nonexistent.md",
        )
        NarrativeSync._update_frontmatter(narr)
