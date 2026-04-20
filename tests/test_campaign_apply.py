"""Tests for the rewritten `_apply_control_item` pipeline (issue #77 fix).

The tests cover the classify/notes/evidence/completion-note pipeline without
hitting the platform. We stub the PretorianClient's `update_narrative`,
`create_evidence_batch`, and `add_control_note` coroutines.
"""

from __future__ import annotations

import asyncio
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
    client.add_control_note = AsyncMock(
        side_effect=lambda **_kwargs: {"id": f"note-{id(_kwargs):x}"}
    )
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


def test_recommended_notes_become_platform_notes() -> None:
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

    changed = asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    # 2 gap notes + 1 completion note.
    assert client.add_control_note.await_count == 3
    assert changed is True
    assert [r["index"] for r in state.receipts["recommended_notes"]] == [0, 1]
    assert all(r["status"] == "ok" for r in state.receipts["recommended_notes"])
    assert "completion_note" in state.receipts


def test_missing_evidence_type_becomes_synthesized_gap_note() -> None:
    proposal = {
        "evidence_recommendations": [
            {"name": "SSO config", "description": "Some summary", "evidence_type": None},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[])

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    client.create_evidence_batch.assert_not_called()
    # 1 synthesized gap note + 1 completion note.
    assert client.add_control_note.await_count == 2
    assert state.receipts["recommended_notes"][0]["status"] == "ok"


def test_invalid_evidence_type_becomes_synthesized_gap_note() -> None:
    proposal = {
        "evidence_recommendations": [
            {"name": "rec", "description": "desc", "evidence_type": "not-a-real-type"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[])

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    client.create_evidence_batch.assert_not_called()
    # The synthesized note references the rejected type.
    synthesized_call = client.add_control_note.await_args_list[0]
    assert "not-a-real-type" in synthesized_call.kwargs["content"]


def test_mixed_accept_reject_preserves_original_indexes() -> None:
    # Five recs: indexes 0/3 valid, 1 missing type, 2 invalid type, 4 valid.
    proposal = {
        "evidence_recommendations": [
            {"name": "n0", "description": "d", "evidence_type": "configuration"},
            {"name": "n1", "description": "d"},
            {"name": "n2", "description": "d", "evidence_type": "bogus"},
            {"name": "n3", "description": "d", "evidence_type": "configuration"},
            {"name": "n4", "description": "d", "evidence_type": "code_snippet"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[_ok_result(0), _ok_result(1), _ok_result(2)])

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    # Batch received exactly the 3 accepted items, in order 0, 3, 4.
    batch_call = client.create_evidence_batch.await_args
    batch_items = batch_call.args[2]
    assert [item.name for item in batch_items] == ["n0", "n3", "n4"]

    # Receipts remap offsets back to original indexes.
    receipt_indexes = sorted(r["index"] for r in state.receipts["evidence_batch"])
    assert receipt_indexes == [0, 3, 4]

    # Two synthesized gap notes were written (for indexes 1 and 2).
    # Plus a completion note at the end → 3 add_control_note calls total.
    assert client.add_control_note.await_count == 3


def test_resume_skips_already_applied_notes() -> None:
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

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    # Only index 1 (+ the completion note) should be written.
    assert client.add_control_note.await_count == 2
    assert {r["index"] for r in state.receipts["recommended_notes"]} == {0, 1}


def test_evidence_batch_length_mismatch_raises() -> None:
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
        asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))


def test_empty_proposal_writes_nothing() -> None:
    state = _state(
        {"evidence_recommendations": [], "recommended_notes": [], "narrative_draft": None}
    )
    client = _mock_client(batch_results=[])

    changed = asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    assert changed is False
    assert client.create_evidence_batch.await_count == 0
    assert client.add_control_note.await_count == 0
    assert "completion_note" not in state.receipts


def test_malformed_recommendation_becomes_synthesized_note_not_crash() -> None:
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

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    batch_items = client.create_evidence_batch.await_args.args[2]
    assert [item.name for item in batch_items] == ["good"]
    # 3 synthesized notes for the three malformed entries + 1 completion note.
    assert client.add_control_note.await_count == 4
    assert "completion_note" in state.receipts


def test_completion_note_fires_even_with_malformed_entries() -> None:
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

    asyncio.run(_apply_control_item(client, _request(), _item(), state, _snapshot()))

    assert "completion_note" in state.receipts


def test_narrative_only_artifacts_skips_evidence_but_writes_notes() -> None:
    proposal = {
        "narrative_draft": "- narrative\n- more",
        "recommended_notes": ["a note"],
        "evidence_recommendations": [
            {"name": "should-be-skipped", "description": "d", "evidence_type": "configuration"},
        ],
    }
    state = _state(proposal)
    client = _mock_client(batch_results=[])

    asyncio.run(_apply_control_item(client, _request("narratives"), _item(), state, _snapshot()))

    client.create_evidence_batch.assert_not_called()
    client.update_narrative.assert_awaited_once()
    # 1 recommended_note + 1 completion note.
    assert client.add_control_note.await_count == 2
