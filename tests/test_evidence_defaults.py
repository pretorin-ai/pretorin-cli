"""Tests that pin `evidence_type` as required on evidence write models.

Issue #77 tightened EvidenceBatchItemCreate. Issue #79 extends that to
EvidenceCreate and adds enum validation on both models so non-canonical
values fail loud instead of reaching the API as HTTP 400s.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from pretorin.client.models import EvidenceBatchItemCreate, EvidenceCreate


def test_evidence_batch_item_requires_evidence_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceBatchItemCreate(name="n", description="d", control_id="ac-02")


def test_evidence_batch_item_accepts_explicit_type() -> None:
    instance = EvidenceBatchItemCreate(name="n", description="d", control_id="ac-02", evidence_type="configuration")
    assert instance.evidence_type == "configuration"


def test_evidence_batch_item_rejects_non_canonical_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceBatchItemCreate(name="n", description="d", control_id="ac-02", evidence_type="audit_log")


def test_evidence_create_requires_evidence_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceCreate(name="n", description="d")


def test_evidence_create_accepts_canonical_type() -> None:
    instance = EvidenceCreate(name="n", description="d", evidence_type="screenshot")
    assert instance.evidence_type == "screenshot"


def test_evidence_create_rejects_non_canonical_type() -> None:
    # "policy" is an alias in the normalizer but must be rejected at the model
    # layer — callers are expected to run normalize_evidence_type() first.
    with pytest.raises(ValidationError):
        EvidenceCreate(name="n", description="d", evidence_type="policy")
