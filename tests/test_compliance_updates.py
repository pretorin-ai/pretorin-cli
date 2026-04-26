"""Tests for shared compliance workflow helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pretorin.client.models import EvidenceItemResponse
from pretorin.workflows.compliance_updates import (
    MATCH_BASIS_EXACT,
    MATCH_BASIS_NONE,
    upsert_evidence,
)


@pytest.mark.asyncio
async def test_upsert_evidence_creates_when_no_match() -> None:
    client = AsyncMock()
    client.list_evidence = AsyncMock(return_value=[])
    client.create_evidence = AsyncMock(return_value={"id": "ev-new", "linked": True, "mapping_id": "map-1"})
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

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

    assert result.created is True
    assert result.evidence_id == "ev-new"
    assert result.linked is True
    assert result.match_basis == MATCH_BASIS_NONE
    client.link_evidence_to_control.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_evidence_reuses_newest_duplicate() -> None:
    client = AsyncMock()
    client.list_evidence = AsyncMock(
        return_value=[
            EvidenceItemResponse(
                id="ev-old",
                name="RBAC Config",
                description="- Role mapping policy",
                evidence_type="configuration",
                collected_at="2025-01-01T00:00:00+00:00",
            ),
            EvidenceItemResponse(
                id="ev-newest",
                name="RBAC Config",
                description="- Role mapping policy",
                evidence_type="configuration",
                collected_at="2026-01-01T00:00:00+00:00",
            ),
        ]
    )
    client.create_evidence = AsyncMock(return_value={"id": "should-not-create"})
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

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
    assert result.evidence_id == "ev-newest"
    assert result.match_basis == MATCH_BASIS_EXACT
    client.create_evidence.assert_not_called()


@pytest.mark.asyncio
async def test_upsert_evidence_requires_framework_for_scoped_control() -> None:
    client = AsyncMock()

    with pytest.raises(ValueError, match="framework_id is required"):
        await upsert_evidence(
            client,
            system_id="sys-1",
            name="RBAC Config",
            description="- Role mapping policy",
            evidence_type="configuration",
            control_id="ac-2",
            framework_id=None,
            dedupe=True,
        )
