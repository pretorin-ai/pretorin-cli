"""Tests for evidence audit-trail metadata models + helpers.

Covers WS1a of the recipe-implementation design:
- ``EvidenceAuditMetadata`` model validation (required + optional fields, enum
  enforcement, content_hash format).
- ``RedactionSummary`` model defaults and constraints.
- ``build_cli_metadata`` / ``build_agent_metadata`` / ``build_recipe_metadata``
  helpers in ``pretorin.evidence.audit_metadata``.
- Optional ``audit_metadata`` field on ``EvidenceCreate`` and
  ``EvidenceBatchItemCreate`` (the migration-window shape; WS1c flips required).
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from pretorin import __version__ as pretorin_version
from pretorin.client.models import (
    EvidenceAuditMetadata,
    EvidenceBatchItemCreate,
    EvidenceCreate,
    RedactionSummary,
)
from pretorin.evidence.audit_metadata import (
    build_agent_metadata,
    build_cli_metadata,
    build_recipe_metadata,
    compute_content_hash,
)

# A valid sha256 hex digest used as a constant in tests that need a content_hash
# but aren't testing the hash itself.
_VALID_HASH = "a" * 64
_NOW = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)


# =============================================================================
# RedactionSummary
# =============================================================================


def test_redaction_summary_defaults() -> None:
    summary = RedactionSummary()
    assert summary.secrets == 0
    assert summary.pii == 0
    assert summary.custom == 0
    assert summary.details is None


def test_redaction_summary_accepts_explicit_counts() -> None:
    summary = RedactionSummary(secrets=2, pii=1, custom=0)
    assert summary.secrets == 2
    assert summary.pii == 1


def test_redaction_summary_accepts_details_dict() -> None:
    summary = RedactionSummary(secrets=3, details={"aws_keys": 2, "github_pats": 1})
    assert summary.details == {"aws_keys": 2, "github_pats": 1}


def test_redaction_summary_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        RedactionSummary(secrets=-1)


# =============================================================================
# EvidenceAuditMetadata — required minimum
# =============================================================================


def _valid_metadata_kwargs(**overrides: object) -> dict[str, object]:
    """Reusable dict of valid kwargs; overrides let tests focus on one field."""
    base: dict[str, object] = {
        "producer_kind": "cli",
        "producer_id": "cli",
        "captured_at": _NOW,
        "source_type": "code_snippet",
        "source_uri": "file:///path/to/source.py",
        "content_hash": _VALID_HASH,
    }
    base.update(overrides)
    return base


def test_metadata_required_minimum_constructs() -> None:
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs())  # type: ignore[arg-type]
    assert meta.producer_kind == "cli"
    assert meta.producer_id == "cli"
    assert meta.captured_at == _NOW
    assert meta.source_type == "code_snippet"
    assert meta.source_uri == "file:///path/to/source.py"
    assert meta.content_hash == _VALID_HASH
    assert meta.producer_version is None
    assert meta.source_version is None
    assert meta.redaction_summary is None
    assert meta.recipe_selection is None


@pytest.mark.parametrize(
    "missing_field",
    [
        "producer_kind",
        "producer_id",
        "captured_at",
        "source_type",
        "source_uri",
        "content_hash",
    ],
)
def test_metadata_rejects_missing_required_field(missing_field: str) -> None:
    kwargs = _valid_metadata_kwargs()
    del kwargs[missing_field]
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**kwargs)  # type: ignore[arg-type]


# =============================================================================
# EvidenceAuditMetadata — enum and constraint validation
# =============================================================================


@pytest.mark.parametrize(
    "value",
    ["cli", "recipe", "agent", "manual_upload", "api"],
)
def test_metadata_accepts_all_producer_kinds(value: str) -> None:
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(producer_kind=value))  # type: ignore[arg-type]
    assert meta.producer_kind == value


def test_metadata_rejects_unknown_producer_kind() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(producer_kind="bogus"))  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "value",
    [
        "code_snippet",
        "log_excerpt",
        "configuration",
        "screenshot",
        "document",
        "attestation",
        "scan_result",
    ],
)
def test_metadata_accepts_all_source_types(value: str) -> None:
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(source_type=value))  # type: ignore[arg-type]
    assert meta.source_type == value


def test_metadata_rejects_unknown_source_type() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(source_type="not-a-type"))  # type: ignore[arg-type]


def test_metadata_rejects_empty_producer_id() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(producer_id=""))  # type: ignore[arg-type]


def test_metadata_rejects_empty_source_uri() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(source_uri=""))  # type: ignore[arg-type]


# =============================================================================
# EvidenceAuditMetadata — content_hash validation
# =============================================================================


def test_metadata_rejects_short_content_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(content_hash="a" * 63))  # type: ignore[arg-type]


def test_metadata_rejects_long_content_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(content_hash="a" * 65))  # type: ignore[arg-type]


def test_metadata_rejects_uppercase_content_hash() -> None:
    """Convention is lowercase hex; uppercase indicates a different stamping path."""
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(content_hash="A" * 64))  # type: ignore[arg-type]


def test_metadata_rejects_non_hex_content_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceAuditMetadata(**_valid_metadata_kwargs(content_hash="g" * 64))  # type: ignore[arg-type]


def test_metadata_accepts_real_sha256_digest() -> None:
    real_digest = hashlib.sha256(b"hello").hexdigest()
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(content_hash=real_digest))  # type: ignore[arg-type]
    assert meta.content_hash == real_digest


# =============================================================================
# EvidenceAuditMetadata — optional fields
# =============================================================================


def test_metadata_accepts_optional_producer_version() -> None:
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(producer_version="0.16.3"))  # type: ignore[arg-type]
    assert meta.producer_version == "0.16.3"


def test_metadata_accepts_optional_source_version() -> None:
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(source_version="abc1234"))  # type: ignore[arg-type]
    assert meta.source_version == "abc1234"


def test_metadata_accepts_optional_redaction_summary() -> None:
    summary = RedactionSummary(secrets=2)
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(redaction_summary=summary))  # type: ignore[arg-type]
    assert meta.redaction_summary is not None
    assert meta.redaction_summary.secrets == 2


def test_metadata_accepts_optional_recipe_selection_dict() -> None:
    selection = {"selected_recipe": "code-evidence-capture", "confidence": "high"}
    meta = EvidenceAuditMetadata(**_valid_metadata_kwargs(recipe_selection=selection))  # type: ignore[arg-type]
    assert meta.recipe_selection == selection


# =============================================================================
# compute_content_hash
# =============================================================================


def test_compute_hash_str_matches_sha256() -> None:
    assert compute_content_hash("hello") == hashlib.sha256(b"hello").hexdigest()


def test_compute_hash_bytes_matches_sha256() -> None:
    assert compute_content_hash(b"hello") == hashlib.sha256(b"hello").hexdigest()


def test_compute_hash_str_and_bytes_agree() -> None:
    """UTF-8 encoding makes str and bytes inputs produce identical hashes."""
    assert compute_content_hash("hello") == compute_content_hash(b"hello")


def test_compute_hash_deterministic() -> None:
    """Same input → same hash. Twice."""
    assert compute_content_hash("payload") == compute_content_hash("payload")


def test_compute_hash_empty() -> None:
    """sha256 of empty string is a known constant."""
    expected = hashlib.sha256(b"").hexdigest()
    assert compute_content_hash("") == expected
    assert compute_content_hash(b"") == expected


def test_compute_hash_unicode() -> None:
    """Non-ASCII strings hash via their UTF-8 encoding."""
    body = "héllo wörld"
    assert compute_content_hash(body) == hashlib.sha256(body.encode("utf-8")).hexdigest()


# =============================================================================
# build_cli_metadata
# =============================================================================


def test_build_cli_basic() -> None:
    meta = build_cli_metadata(
        body="payload",
        source_uri="file:///x.py",
        source_type="code_snippet",
    )
    assert meta.producer_kind == "cli"
    assert meta.producer_id == "cli"
    assert meta.producer_version == pretorin_version
    assert meta.source_type == "code_snippet"
    assert meta.source_uri == "file:///x.py"
    assert meta.content_hash == compute_content_hash("payload")
    assert meta.redaction_summary is None
    assert meta.recipe_selection is None


def test_build_cli_captured_at_defaults_to_now_utc() -> None:
    meta = build_cli_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
    )
    # Auto-stamped captured_at should be timezone-aware UTC.
    assert meta.captured_at.tzinfo is timezone.utc


def test_build_cli_captured_at_override_respected() -> None:
    custom = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    meta = build_cli_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        captured_at=custom,
    )
    assert meta.captured_at == custom


def test_build_cli_passes_through_optional_fields() -> None:
    summary = RedactionSummary(secrets=1)
    meta = build_cli_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        source_version="abc1234",
        redaction_summary=summary,
    )
    assert meta.source_version == "abc1234"
    assert meta.redaction_summary is summary


def test_build_cli_accepts_bytes_body() -> None:
    meta = build_cli_metadata(
        body=b"\x00\x01raw",
        source_uri="file:///x.bin",
        source_type="document",
    )
    assert meta.content_hash == compute_content_hash(b"\x00\x01raw")


# =============================================================================
# build_agent_metadata
# =============================================================================


def test_build_agent_basic() -> None:
    meta = build_agent_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        agent_id="codex-agent",
    )
    assert meta.producer_kind == "agent"
    assert meta.producer_id == "codex-agent"
    assert meta.producer_version is None  # not provided


def test_build_agent_version_passed_through() -> None:
    meta = build_agent_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        agent_id="claude-code",
        agent_version="claude-opus-4-7",
    )
    assert meta.producer_version == "claude-opus-4-7"


# =============================================================================
# build_recipe_metadata
# =============================================================================


def test_build_recipe_basic() -> None:
    meta = build_recipe_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        recipe_id="code-evidence-capture",
        recipe_version="0.1.0",
    )
    assert meta.producer_kind == "recipe"
    assert meta.producer_id == "code-evidence-capture"
    assert meta.producer_version == "0.1.0"
    assert meta.recipe_selection is None  # set by workflow layer (WS5), not here


def test_build_recipe_for_scanner_recipe() -> None:
    """Scanner recipes use source_type='scan_result'."""
    meta = build_recipe_metadata(
        body="scan output...",
        source_uri="inspec://disa-stig-rhel-9",
        source_type="scan_result",
        recipe_id="inspec-baseline",
        recipe_version="0.1.0",
    )
    assert meta.source_type == "scan_result"
    assert meta.producer_id == "inspec-baseline"


# =============================================================================
# EvidenceCreate / EvidenceBatchItemCreate integration
# =============================================================================


def test_evidence_create_accepts_no_audit_metadata() -> None:
    """During the WS1a/b migration window, audit_metadata is optional."""
    ev = EvidenceCreate(
        name="x",
        description="y",
        evidence_type="code_snippet",
    )
    assert ev.audit_metadata is None


def test_evidence_create_accepts_audit_metadata_instance() -> None:
    meta = build_cli_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
    )
    ev = EvidenceCreate(
        name="x",
        description="y",
        evidence_type="code_snippet",
        audit_metadata=meta,
    )
    assert ev.audit_metadata is meta


def test_evidence_create_accepts_audit_metadata_dict() -> None:
    """Pydantic auto-coerces a dict into the nested model."""
    meta_dict = {
        "producer_kind": "cli",
        "producer_id": "cli",
        "captured_at": _NOW,
        "source_type": "code_snippet",
        "source_uri": "file:///x.py",
        "content_hash": _VALID_HASH,
    }
    ev = EvidenceCreate(
        name="x",
        description="y",
        evidence_type="code_snippet",
        audit_metadata=meta_dict,  # type: ignore[arg-type]
    )
    assert ev.audit_metadata is not None
    assert ev.audit_metadata.producer_kind == "cli"


def test_evidence_create_serialization_round_trip_preserves_metadata() -> None:
    meta = build_recipe_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        recipe_id="code-evidence-capture",
        recipe_version="0.1.0",
    )
    ev = EvidenceCreate(
        name="x",
        description="y",
        evidence_type="code_snippet",
        audit_metadata=meta,
    )
    payload = ev.model_dump(mode="json")
    assert "audit_metadata" in payload
    assert payload["audit_metadata"]["producer_kind"] == "recipe"
    # Round trip.
    rehydrated = EvidenceCreate.model_validate(payload)
    assert rehydrated.audit_metadata is not None
    assert rehydrated.audit_metadata.producer_id == "code-evidence-capture"


def test_evidence_batch_item_accepts_audit_metadata() -> None:
    meta = build_agent_metadata(
        body="x",
        source_uri="file:///x.py",
        source_type="code_snippet",
        agent_id="codex-agent",
    )
    item = EvidenceBatchItemCreate(
        name="x",
        description="y",
        control_id="AC-2",
        evidence_type="code_snippet",
        audit_metadata=meta,
    )
    assert item.audit_metadata is not None
    assert item.audit_metadata.producer_kind == "agent"


def test_evidence_batch_item_audit_metadata_optional() -> None:
    item = EvidenceBatchItemCreate(
        name="x",
        description="y",
        control_id="AC-2",
        evidence_type="code_snippet",
    )
    assert item.audit_metadata is None
