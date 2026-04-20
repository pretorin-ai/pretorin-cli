"""Tests for write provenance injection in API client methods."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.client.api import PretorianClient
from pretorin.client.models import EvidenceBatchItemCreate, EvidenceCreate, MonitoringEventCreate

FAKE_PROVENANCE = {
    "cli_version": "0.14.0",
    "source": "pretorin-cli",
    "verification_status": "unverified",
}


@pytest.fixture
def mock_provenance():
    """Patch _build_provenance to return a known dict."""
    with patch("pretorin.client.api._build_provenance", return_value=FAKE_PROVENANCE) as m:
        yield m


@pytest.fixture
def client():
    """Create a PretorianClient with mocked _request.

    Default return value works for most methods (they return dict).
    create_evidence_batch needs framework_id and total for Pydantic.
    """
    c = PretorianClient.__new__(PretorianClient)
    c._request = AsyncMock(return_value={"framework_id": "fw-1", "total": 0, "results": []})
    c._config = MagicMock()
    c._config.platform_api_base_url = "https://example.com"
    return c


class TestProvenanceInjection:
    @pytest.mark.asyncio
    async def test_update_narrative(self, client, mock_provenance):
        with patch("pretorin.client.api.ensure_audit_markdown"):
            await client.update_narrative("sys-1", "ac-02", "narrative text", "fw-1")
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload
        assert payload["_provenance"]["verification_status"] == "unverified"

    @pytest.mark.asyncio
    async def test_add_control_note(self, client, mock_provenance):
        await client.add_control_note("sys-1", "ac-02", "note content", "fw-1")
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload

    @pytest.mark.asyncio
    async def test_update_control_status(self, client, mock_provenance):
        await client.update_control_status("sys-1", "ac-02", "implemented", "fw-1")
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload
        assert payload["status"] == "implemented"

    @pytest.mark.asyncio
    async def test_create_evidence(self, client, mock_provenance):
        evidence = EvidenceCreate(
            name="test evidence",
            description="desc",
            evidence_type="policy_document",
            framework_id="fw-1",
        )
        await client.create_evidence("sys-1", evidence)
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload

    @pytest.mark.asyncio
    async def test_create_evidence_batch(self, client, mock_provenance):
        items = [
            EvidenceBatchItemCreate(
                name="item1",
                description="desc1",
                control_id="ac-02",
                evidence_type="policy_document",
            )
        ]
        await client.create_evidence_batch("sys-1", "fw-1", items)
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload

    @pytest.mark.asyncio
    async def test_link_evidence_to_control(self, client, mock_provenance):
        await client.link_evidence_to_control("ev-1", "ac-02", "sys-1", "fw-1")
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        assert "_provenance" in payload

    @pytest.mark.asyncio
    async def test_create_monitoring_event(self, client, mock_provenance):
        event = MonitoringEventCreate(
            title="test event",
            event_type="security_scan",
            severity="medium",
            framework_id="fw-1",
            event_data={"source": "cli"},
        )
        await client.create_monitoring_event("sys-1", event)
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        # For monitoring events, provenance is nested in event_data
        assert "_provenance" in payload.get("event_data", {})


class TestProvenanceShape:
    @pytest.mark.asyncio
    async def test_provenance_has_required_keys(self, client, mock_provenance):
        await client.add_control_note("sys-1", "ac-02", "note", "fw-1")
        call_kwargs = client._request.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        prov = payload["_provenance"]
        assert "cli_version" in prov
        assert "source" in prov
        assert "verification_status" in prov


class TestManualSourceProvenance:
    def test_provenance_includes_attestation_type(self, tmp_path, monkeypatch):
        from datetime import datetime, timezone

        from pretorin.attestation import (
            SourceIdentity,
            VerificationStatus,
            VerifiedSnapshot,
            build_write_provenance,
            save_snapshot,
        )

        monkeypatch.setattr("pretorin.attestation.SNAPSHOT_DIR", tmp_path)

        manual_source = SourceIdentity(
            provider_type="hris",
            identity="workday.acme.com/tenant/prod",
            display_name="Workday HRIS",
            raw={"attestation_type": "manual"},
        )
        snap = VerifiedSnapshot(
            system_id="sys-1",
            framework_id="fedramp-moderate",
            api_base_url="https://example.com",
            sources=(manual_source,),
            verified_at=datetime.now(timezone.utc).isoformat(),
            status=VerificationStatus.VERIFIED,
        )
        save_snapshot(snap)

        mock_config = MagicMock()
        mock_config.platform_api_base_url = "https://example.com"
        with patch("pretorin.client.config.Config", return_value=mock_config):
            result = build_write_provenance("sys-1", "fedramp-moderate")

        assert result["verification_status"] == "verified"
        assert len(result["verified_sources"]) == 1
        src = result["verified_sources"][0]
        assert src["provider_type"] == "hris"
        assert src["attestation_type"] == "manual"
