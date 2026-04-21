"""Canonical evidence-type enum, AI-drift alias map, and client-side normalizer.

Issue #79: the platform's `evidence_type` enum has 13 values. AI drafting
(campaign flows) regularly invents near-misses ("report", "audit_log",
"test_results" plural, etc.) and the platform rejects the batch with HTTP 400.
This module is the one place the CLI enforces the enum and maps known drift
values onto canonical types before anything is sent upstream.

Lookup order (all lowercase+stripped):
    1. None / empty / non-string        -> "other"            (fallback)
    2. Canonical hit                    -> value              (canonical)
    3. Known alias                      -> alias target       (alias)
    4. difflib fuzzy match (>= cutoff)  -> closest canonical  (fuzzy)
    5. Otherwise                        -> "other"            (fallback)

CLI write paths do NOT call this normalizer; they hard-error when the user
omits `-t/--type`. All non-CLI write paths (MCP handlers, agent tools,
campaign apply) run this before payload construction so AI drift doesn't
turn into HTTP 400s during batch submission.
"""

from __future__ import annotations

import difflib
import logging
from typing import Final, NamedTuple

logger = logging.getLogger(__name__)

VALID_EVIDENCE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "attestation",
        "certificate",
        "code_snippet",
        "configuration",
        "interview_notes",
        "log_file",
        "other",
        "policy_document",
        "repository_link",
        "scan_result",
        "screen_recording",
        "screenshot",
        "test_result",
    }
)

# Known AI-drift aliases -> canonical types. Keys MUST be lowercase and
# stripped (normalize_evidence_type lowercases+strips before lookup).
# Kept deliberately small: fuzzy matching handles the long tail of novel
# typos and near-misses without needing a new entry per variant.
EVIDENCE_TYPE_ALIASES: Final[dict[str, str]] = {
    "log": "log_file",
    "logs": "log_file",
    "audit_log": "log_file",
    "audit_logs": "log_file",
    "test_results": "test_result",
    "tests": "test_result",
    "report": "other",
    "procedure": "policy_document",
    "policy": "policy_document",
    "contract": "attestation",
    "screenshots": "screenshot",
    "recording": "screen_recording",
    "screencast": "screen_recording",
    "scan": "scan_result",
    "cert": "certificate",
    "config": "configuration",
    "repo": "repository_link",
    "repository": "repository_link",
    "interview": "interview_notes",
    "code": "code_snippet",
}

# Minimum SequenceMatcher ratio for a fuzzy match to count. Tuned to catch
# obvious typos (`screenshoot` -> `screenshot`, 0.90; `policy_doc` ->
# `policy_document`, 0.86) while rejecting unrelated strings (`report`
# best-matches `repository_link` at ~0.52). Covered by boundary tests.
FUZZY_MATCH_CUTOFF: Final[float] = 0.80

_FALLBACK_TYPE: Final[str] = "other"


class NormalizedEvidenceType(NamedTuple):
    """Result of normalizing a possibly-AI-generated evidence_type string."""

    value: str
    was_mapped: bool
    was_fallback: bool
    strategy: str  # "canonical" | "alias" | "fuzzy" | "fallback"


def normalize_evidence_type(value: str | None) -> NormalizedEvidenceType:
    """Map a possibly-AI-generated evidence_type onto the canonical enum.

    Never raises; this is a client-side safety net. Pydantic validation
    at the boundary (`EvidenceCreate`, `EvidenceBatchItemCreate`) is the
    last line of defense and will reject a truly garbage value. The
    normalizer's job is to make common AI-drift cases cheap and
    deterministic.
    """
    if value is None or not isinstance(value, str):
        logger.warning(
            "evidence_type.normalized",
            extra={
                "original": value,
                "mapped_to": _FALLBACK_TYPE,
                "strategy": "fallback",
            },
        )
        return NormalizedEvidenceType(_FALLBACK_TYPE, False, True, "fallback")

    key = value.strip().lower()
    if not key:
        logger.warning(
            "evidence_type.normalized",
            extra={
                "original": value,
                "mapped_to": _FALLBACK_TYPE,
                "strategy": "fallback",
            },
        )
        return NormalizedEvidenceType(_FALLBACK_TYPE, False, True, "fallback")

    if key in VALID_EVIDENCE_TYPES:
        return NormalizedEvidenceType(key, False, False, "canonical")

    if key in EVIDENCE_TYPE_ALIASES:
        target = EVIDENCE_TYPE_ALIASES[key]
        logger.info(
            "evidence_type.normalized",
            extra={
                "original": value,
                "mapped_to": target,
                "strategy": "alias",
            },
        )
        return NormalizedEvidenceType(target, True, False, "alias")

    matches = difflib.get_close_matches(key, VALID_EVIDENCE_TYPES, n=1, cutoff=FUZZY_MATCH_CUTOFF)
    if matches:
        match = matches[0]
        ratio = difflib.SequenceMatcher(None, key, match).ratio()
        logger.info(
            "evidence_type.normalized",
            extra={
                "original": value,
                "mapped_to": match,
                "strategy": "fuzzy",
                "ratio": round(ratio, 3),
            },
        )
        return NormalizedEvidenceType(match, True, False, "fuzzy")

    logger.warning(
        "evidence_type.normalized",
        extra={
            "original": value,
            "mapped_to": _FALLBACK_TYPE,
            "strategy": "fallback",
        },
    )
    return NormalizedEvidenceType(_FALLBACK_TYPE, False, True, "fallback")
