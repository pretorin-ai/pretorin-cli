"""Tests for the rewritten `_apply_control_item` pipeline (issue #77 fix).

The tests cover the classify/notes/evidence/completion-note pipeline without
hitting the platform. We stub the PretorianClient's `update_narrative`,
`create_evidence_batch`, and `add_control_note` coroutines.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.client.models import EvidenceBatchItemResult, EvidenceBatchResponse
from pretorin.workflows.campaign import (
    CampaignItem,
    CampaignItemState,
    CampaignRunRequest,
    WorkflowContextSnapshot,
    _apply_control_item,
)


def _snapshot() -> WorkflowContextSnapshot:
    return WorkflowContextSnapshot(
        domain="controls",
        subject="sys-1",
        scope={"system_id": "sys-1", "framework_id": "fedramp-moderate"},
        platform_api_base_url="https://example.test/api",
    )


def _item() -> CampaignItem:
    return CampaignItem(item_id="ac-02", label="AC-02", kind="control")


def _request(artifacts: str = "both") -> CampaignRunRequest:
    from pathlib import Path

    return CampaignRunRequest(
        domain="controls",
        mode="initial",
        apply=True,
        output="json",
        concurrency=1,
        max_retries=1,
        checkpoint_path=Path("/tmp/cp.jsonl"),
        working_directory=Path.cwd(),
        system="sys-1",
        framework_id="fedramp-moderate",
        artifacts=artifacts,
    )


def _state(proposal: dict[str, Any] | None = None, receipts: dict[str, Any] | None = None) -> CampaignItemState:
    state = CampaignItemState(item={"item_id": "ac-02", "label": "AC-02", "kind": "control"})
    state.proposal = proposal or {}
    state.receipts = receipts or {}
    return state


def _mock_client(batch_results: list[EvidenceBatchItemResult] | None = None) -> MagicMock:
    client = MagicMock()
    client.update_narrative = AsyncMock(return_value=None)
    client.add_control_note = AsyncMock(side_effect=lambda **_kwargs: {"id": f"note-{id(_kwargs):x}"})
    client.create_evidence_batch = AsyncMock(
        return_value=EvidenceBatchResponse(
            framework_id="fedramp-moderate",
            total=len(batch_results or []),
            results=batch_results or [],
        )
    )
    return client


def _ok_result(index: int) -> EvidenceBatchItemResult:
    return EvidenceBatchItemResult(
        index=index,
        status="ok",
        evidence_id=f"ev-{index}",
        mapping_id=f"map-{index}",
        control_id="ac-02",
        framework_id="fedramp-moderate",
    )


async def test_recommended_notes_become_platform_notes() -> None:
    proposal = {
        "narrative_draft": None,
        "recommended_notes": [
            "Gap: A\nObserved: x\nMissing: y\nWhy missing: z\nManual next step: do",
            "Gap: B\nObserved: x\nMissing: y\nWhy missing: z\nManual next step: do",
        ],
        "evidence_recommendations": [],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[])

    changed = await _apply_control_item(client, _request(), _item(), state, _snapshot())

    # 2 gap notes + 1 completion note.
    assert client.add_control_note.await_count == 3
    assert changed is True
    assert [r["index"] for r in state.receipts["recommended_notes"]] == [0, 1]
    assert all(r["status"] == "ok" for r in state.receipts["recommended_notes"])
    assert "completion_note" in state.receipts


async def test_missing_evidence_type_falls_back_to_other() -> None:
    """Issue #79: missing evidence_type normalizes to 'other' via the normalizer.

    Previously the safety net defaulted to 'policy_document'; that polluted the
    platform's custom-policies page. The fallback is now 'other' so summary-
    shaped evidence does not land as a tagged policy document.
    """
    proposal = {
        "evidence_recommendations": [
            {"name": "SSO config", "description": "Some summary", "evidence_type": None},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert [item.name for item in batch_items] == ["SSO config"]
    assert batch_items[0].evidence_type == "other"
    # No synthesized gap note for the missing-type case; only the completion note.
    assert client.add_control_note.await_count == 1


async def test_whitespace_only_evidence_type_treated_as_missing() -> None:
    """Issue #79: `"   "` should count as missing (not unknown-drift).

    The normalizer treats it as fallback; the campaign pipeline must
    classify it under defaulted_missing_type (like None/"") and NOT
    emit a drift gap note for it — the AI effectively didn't provide a
    type, and the prompt already tells them it's required.
    """
    proposal = {
        "evidence_recommendations": [
            {"name": "SSO config", "description": "d", "evidence_type": "   "},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert batch_items[0].evidence_type == "other"
    # Only the completion note (no drift gap note) fires.
    assert client.add_control_note.await_count == 1


async def test_unknown_evidence_type_normalizes_and_emits_gap_note() -> None:
    """Issue #79: unknown non-empty strings normalize to 'other' AND emit a gap note.

    The evidence still lands (so reviewers see the artifact) but the gap note
    surfaces what the AI originally tried so drift is visible in the UI.
    """
    proposal = {
        "evidence_recommendations": [
            {"name": "rec", "description": "desc", "evidence_type": "not-a-real-type"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert batch_items[0].evidence_type == "other"
    # Gap note references the original drift string.
    synthesized_call = client.add_control_note.await_args_list[0]
    assert "not-a-real-type" in synthesized_call.kwargs["content"]


async def test_alias_evidence_type_normalizes_to_canonical() -> None:
    """Issue #79: AI-drift aliases like 'audit_log' map to canonical 'log_file'."""
    proposal = {
        "evidence_recommendations": [
            {"name": "app audit", "description": "d", "evidence_type": "audit_log"},
            {"name": "unit tests", "description": "d", "evidence_type": "test_results"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0), _ok_result(1)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert batch_items[0].evidence_type == "log_file"
    assert batch_items[1].evidence_type == "test_result"
    # Aliases don't emit gap notes (they're legitimate near-misses) — only completion note.
    assert client.add_control_note.await_count == 1


async def test_mixed_accept_reject_preserves_original_indexes() -> None:
    """Issue #79: with the normalizer, formerly-rejected types now reach batch as 'other'.

    Five recs: 0/3/4 canonical, 1 missing (fallback -> other), 2 unknown (fallback -> other
    with gap note). All five reach the batch; the unknown still emits a gap note so
    reviewers see the drift.
    """
    proposal = {
        "evidence_recommendations": [
            {"name": "n0", "description": "d", "evidence_type": "configuration"},
            {"name": "n1", "description": "d"},
            {"name": "n2", "description": "d", "evidence_type": "bogus_xyzzy"},
            {"name": "n3", "description": "d", "evidence_type": "configuration"},
            {"name": "n4", "description": "d", "evidence_type": "code_snippet"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(i) for i in range(5)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_call = client.create_evidence_batch.await_args
    batch_items = batch_call.args[2]
    assert [item.name for item in batch_items] == ["n0", "n1", "n2", "n3", "n4"]
    assert batch_items[1].evidence_type == "other"  # missing -> fallback
    assert batch_items[2].evidence_type == "other"  # unknown -> fallback

    # Receipts keep original indexes 0..4.
    receipt_indexes = sorted(r["index"] for r in state.receipts["evidence_batch"])
    assert receipt_indexes == [0, 1, 2, 3, 4]

    # One synthesized gap note (only for the unknown-string index 2) + one completion note.
    assert client.add_control_note.await_count == 2


async def test_resume_skips_already_applied_notes() -> None:
    proposal = {
        "recommended_notes": ["one", "two"],
        "evidence_recommendations": [],
    }
    receipts = {
        "recommended_notes": [
            {"index": 0, "applied_at": "t", "status": "ok", "note_id": "note-a"},
        ],
    }
    state = _state(proposal, receipts)
    client = _mock_client(batch_results=[])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    # Only index 1 (+ the completion note) should be written.
    assert client.add_control_note.await_count == 2
    assert {r["index"] for r in state.receipts["recommended_notes"]} == {0, 1}


async def test_evidence_batch_length_mismatch_raises() -> None:
    proposal = {
        "evidence_recommendations": [
            {"name": "n0", "description": "d", "evidence_type": "configuration"},
            {"name": "n1", "description": "d", "evidence_type": "configuration"},
        ],
    }
    state = _state(proposal)
    # Server returns 1 result for 2 items — must raise.
    client = _mock_client(batch_results=[_ok_result(0)])

    with pytest.raises(PretorianClientError, match="length mismatch"):
        await _apply_control_item(client, _request(), _item(), state, _snapshot())


async def test_empty_proposal_writes_nothing() -> None:
    state = _state({"evidence_recommendations": [], "recommended_notes": [], "narrative_draft": None})
    client = _mock_client(batch_results=[])

    changed = await _apply_control_item(client, _request(), _item(), state, _snapshot())

    assert changed is False
    assert client.create_evidence_batch.await_count == 0
    assert client.add_control_note.await_count == 0
    assert "completion_note" not in state.receipts


async def test_malformed_recommendation_becomes_synthesized_note_not_crash() -> None:
    # AI returned one good rec, one non-dict entry, one dict missing `name`, one missing
    # `description`. Only the good rec should reach the batch; the others become notes.
    proposal = {
        "evidence_recommendations": [
            {"name": "good", "description": "d", "evidence_type": "configuration"},
            "not even a dict",
            {"description": "no name here", "evidence_type": "configuration"},
            {"name": "no desc", "evidence_type": "configuration"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert [item.name for item in batch_items] == ["good"]
    # 3 synthesized notes for the three malformed entries + 1 completion note.
    assert client.add_control_note.await_count == 4
    assert "completion_note" in state.receipts


async def test_completion_note_fires_even_with_malformed_entries() -> None:
    # Previously `evidence_done` relied on `total - rejected_typed` which undercounted
    # malformed entries and could keep `all_work_done` False forever.
    proposal = {
        "evidence_recommendations": [
            {"name": "a", "description": "d", "evidence_type": "configuration"},
            "malformed",
            {"name": "b", "description": "d", "evidence_type": "configuration"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0), _ok_result(1)])

    await _apply_control_item(client, _request(), _item(), state, _snapshot())

    assert "completion_note" in state.receipts


async def test_narrative_only_artifacts_skips_evidence_but_writes_notes() -> None:
    proposal = {
        "narrative_draft": "- narrative\n- more",
        "recommended_notes": ["a note"],
        "evidence_recommendations": [
            {"name": "should-be-skipped", "description": "d", "evidence_type": "configuration"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[])

    await _apply_control_item(client, _request("narratives"), _item(), state, _snapshot())

    client.create_evidence_batch.assert_not_called()
    client.update_narrative.assert_awaited_once()
    # 1 recommended_note + 1 completion note.
    assert client.add_control_note.await_count == 2
