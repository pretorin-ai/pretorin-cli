"""Tests for evidence sync workflow behavior."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from pretorin.evidence.sync import EvidenceSync
from pretorin.evidence.writer import EvidenceWriter, LocalEvidence


class _DummyConfig:
    active_system_id = "sys-1"


def _write_local_evidence(base_dir: Path) -> None:
    writer = EvidenceWriter(base_dir=base_dir)
    writer.write(
        LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="RBAC Config",
            description="- Role mapping policy",
            evidence_type="configuration",
        )
    )


@pytest.mark.asyncio
async def test_push_does_not_emit_notifications(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("pretorin.client.config.Config", _DummyConfig)
    _write_local_evidence(tmp_path)

    client = AsyncMock()
    client.list_evidence = AsyncMock(return_value=[])
    client.create_evidence = AsyncMock(return_value={"id": "ev-new"})
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})
    client.update_control_status = AsyncMock(return_value={"ok": True})
    client.create_monitoring_event = AsyncMock(return_value={"ok": True})

    sync = EvidenceSync(evidence_dir=tmp_path)
    result = await sync.push(client, dry_run=False)

    assert result.created
    assert result.events == []
    client.update_control_status.assert_not_called()
    client.create_monitoring_event.assert_not_called()


@pytest.mark.asyncio
async def test_push_reuses_existing_matching_evidence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from pretorin.client.models import EvidenceItemResponse

    monkeypatch.setattr("pretorin.client.config.Config", _DummyConfig)
    _write_local_evidence(tmp_path)

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
    client.create_evidence = AsyncMock(return_value={"id": "should-not-create"})
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    sync = EvidenceSync(evidence_dir=tmp_path)
    result = await sync.push(client, dry_run=False)

    assert result.reused
    client.create_evidence.assert_not_called()
