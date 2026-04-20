"""Tests that pin `evidence_type` as required on the batch model.

Issue #77: the campaign batch write path used to silently default the evidence_type
to "policy_document". This tightens EvidenceBatchItemCreate so a missing type now
fails loud via pydantic validation instead of polluting the evidence locker.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pretorin.client.models import EvidenceBatchItemCreate


def test_evidence_batch_item_requires_evidence_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceBatchItemCreate(name="n", description="d", control_id="ac-02")


def test_evidence_batch_item_accepts_explicit_type() -> None:
    instance = EvidenceBatchItemCreate(
        name="n", description="d", control_id="ac-02", evidence_type="configuration"
    )
    assert instance.evidence_type == "configuration"
