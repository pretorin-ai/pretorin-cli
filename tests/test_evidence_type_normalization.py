"""Tests for the evidence_type normalizer (issue #79).

The normalizer lives at pretorin.evidence.types.normalize_evidence_type.
It maps possibly-AI-generated evidence_type strings onto the 13-value
canonical enum using (in order) exact canonical match, a static alias
map, then difflib fuzzy matching, then fallback to "other".
"""

from __future__ import annotations

import logging

import pytest

from pretorin.evidence.types import (
    EVIDENCE_TYPE_ALIASES,
    FUZZY_MATCH_CUTOFF,
    VALID_EVIDENCE_TYPES,
    normalize_evidence_type,
)

# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------


def test_canonical_set_has_thirteen_values() -> None:
    assert len(VALID_EVIDENCE_TYPES) == 13


def test_alias_keys_disjoint_from_canonical() -> None:
    """Alias keys must not shadow a canonical value (future-proofing)."""
    assert set(EVIDENCE_TYPE_ALIASES).isdisjoint(VALID_EVIDENCE_TYPES)


def test_alias_values_are_canonical() -> None:
    """Every alias must target a canonical value."""
    assert set(EVIDENCE_TYPE_ALIASES.values()).issubset(VALID_EVIDENCE_TYPES)


def test_fuzzy_cutoff_pinned() -> None:
    """Pin the cutoff so future edits can't silently widen/narrow matching."""
    assert FUZZY_MATCH_CUTOFF == 0.80


# ---------------------------------------------------------------------------
# Canonical roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("canonical", sorted(VALID_EVIDENCE_TYPES))
def test_canonical_roundtrip(canonical: str) -> None:
    result = normalize_evidence_type(canonical)
    assert result.value == canonical
    assert result.was_mapped is False
    assert result.was_fallback is False
    assert result.strategy == "canonical"


def test_canonical_is_case_and_whitespace_insensitive() -> None:
    for raw in ("POLICY_DOCUMENT", " screenshot  ", "\tLog_File\n", "Other"):
        result = normalize_evidence_type(raw)
        assert result.value in VALID_EVIDENCE_TYPES
        assert result.strategy == "canonical"
        assert result.was_fallback is False


# ---------------------------------------------------------------------------
# Alias map
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("alias,expected", sorted(EVIDENCE_TYPE_ALIASES.items()))
def test_each_alias_maps_to_canonical(alias: str, expected: str) -> None:
    result = normalize_evidence_type(alias)
    assert result.value == expected
    assert result.was_mapped is True
    assert result.was_fallback is False
    assert result.strategy == "alias"


def test_alias_case_insensitive() -> None:
    result = normalize_evidence_type("AUDIT_LOG")
    assert result.value == "log_file"
    assert result.strategy == "alias"


# ---------------------------------------------------------------------------
# Fuzzy matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "drift,expected",
    [
        ("policy_doc", "policy_document"),
        ("policy_documents", "policy_document"),
        ("screenshoot", "screenshot"),
        ("testresult", "test_result"),
        ("attestations", "attestation"),
        ("certificates", "certificate"),
    ],
)
def test_fuzzy_match_catches_typos(drift: str, expected: str) -> None:
    result = normalize_evidence_type(drift)
    assert result.value == expected
    assert result.was_mapped is True
    assert result.was_fallback is False
    assert result.strategy == "fuzzy"


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("empty", [None, "", "   ", "\t"])
def test_empty_inputs_fall_back_to_other(empty: str | None) -> None:
    result = normalize_evidence_type(empty)
    assert result.value == "other"
    assert result.was_fallback is True
    assert result.strategy == "fallback"


@pytest.mark.parametrize(
    "garbage",
    ["totally_made_up_zzz", "xyzzy", "frobnicate", "lorem_ipsum_dolor"],
)
def test_unrelated_strings_fall_back_to_other(garbage: str) -> None:
    result = normalize_evidence_type(garbage)
    assert result.value == "other"
    assert result.was_fallback is True
    assert result.strategy == "fallback"


def test_non_string_input_falls_back() -> None:
    # The normalizer is defensive: a caller that passes the wrong type
    # gets "other" rather than a TypeError.
    result = normalize_evidence_type(42)  # type: ignore[arg-type]
    assert result.value == "other"
    assert result.strategy == "fallback"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def test_canonical_emits_no_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG, logger="pretorin.evidence.types")
    normalize_evidence_type("screenshot")
    records = [r for r in caplog.records if r.name == "pretorin.evidence.types"]
    assert records == []


def test_alias_emits_info_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="pretorin.evidence.types")
    normalize_evidence_type("audit_log")
    records = [
        r for r in caplog.records if r.name == "pretorin.evidence.types" and r.message == "evidence_type.normalized"
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert getattr(records[0], "strategy", None) == "alias"
    assert getattr(records[0], "mapped_to", None) == "log_file"


def test_fuzzy_emits_info_log_with_ratio(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO, logger="pretorin.evidence.types")
    normalize_evidence_type("screenshoot")
    records = [
        r for r in caplog.records if r.name == "pretorin.evidence.types" and r.message == "evidence_type.normalized"
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.INFO
    assert getattr(records[0], "strategy", None) == "fuzzy"
    assert getattr(records[0], "mapped_to", None) == "screenshot"
    assert isinstance(getattr(records[0], "ratio", None), float)


def test_fallback_emits_warning_log(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="pretorin.evidence.types")
    normalize_evidence_type("totally_made_up_zzz")
    records = [
        r for r in caplog.records if r.name == "pretorin.evidence.types" and r.message == "evidence_type.normalized"
    ]
    assert len(records) == 1
    assert records[0].levelno == logging.WARNING
    assert getattr(records[0], "strategy", None) == "fallback"
    assert getattr(records[0], "mapped_to", None) == "other"
