"""Tests for shared compliance workflow helpers."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pretorin.client.models import EvidenceItemResponse
from pretorin.workflows.compliance_updates import (
    MATCH_BASIS_EXACT,
    MATCH_BASIS_NONE,
    build_gap_note,
    build_narrative_todo_block,
    upsert_evidence,
)


def test_build_narrative_todo_block_format() -> None:
    block = build_narrative_todo_block(
        missing_item="SSO provider metadata",
        required_manual_action="Upload IdP configuration screenshots",
        suggested_evidence_type="configuration",
    )
    assert "[[PRETORIN_TODO]]" in block
    assert "missing_item: SSO provider metadata" in block
    assert "suggested_evidence_type: configuration" in block
    assert "[[/PRETORIN_TODO]]" in block


def test_build_gap_note_format() -> None:
    note = build_gap_note(
        gap="Missing SSO integration evidence",
        observed="App references SAML middleware",
        missing="IdP policy exports",
        why_missing="IdP not connected to MCP",
        manual_next_step="Upload policy export and map to AC-02",
    )
    assert "Gap: Missing SSO integration evidence" in note
    assert "Observed: App references SAML middleware" in note
    assert "Manual next step: Upload policy export and map to AC-02" in note


@pytest.mark.asyncio
async def test_upsert_evidence_creates_when_no_match() -> None:
    client = AsyncMock()
    client.list_evidence = AsyncMock(return_value=[])
    client.create_evidence = AsyncMock(return_value={"id": "ev-new"})
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
