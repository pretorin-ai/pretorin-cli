"""Audit-trail metadata helpers — single construction surface for every write path.

Every evidence/narrative write through this CLI produces an `EvidenceAuditMetadata`
instance via one of three helpers in this module:

- ``build_cli_metadata`` — manual CLI writes (`pretorin evidence create`, etc.).
  Stamps ``producer_kind="cli"`` and ``producer_id="cli"`` plus the running pretorin
  version.
- ``build_agent_metadata`` — agent-driven writes from `pretorin agent run` or from
  campaign-apply's freelance fallback. Stamps ``producer_kind="agent"``.
- ``build_recipe_metadata`` — writes made inside a recipe execution context
  (recipe-implementation WS2). Stamps ``producer_kind="recipe"`` plus recipe id
  and version.

The single-construction-surface pattern is the load-bearing DRY decision from the
plan-eng-review (Section 2 finding C1): no path stamps fields on its own, every
path goes through these helpers, and the platform sees one consistent shape.

Per the recipe-implementation WS1a/b/c sequencing, this module ships in WS1a as
the foundation that WS1b's caller migration uses and WS1c's strict-enforcement flip
relies on.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from pretorin import __version__ as _pretorin_version
from pretorin.client.models import (
    EvidenceAuditMetadata,
    RedactionSummary,
    SourceType,
)


def compute_content_hash(body: str | bytes) -> str:
    """Return the lowercase-hex sha256 digest of the canonical body.

    Strings are UTF-8 encoded before hashing so the digest is stable across
    platforms regardless of source string representation.

    Used by every ``build_*_metadata`` helper; exposed publicly so callers that
    already have a hash (e.g., file-upload checksums) can pass it directly without
    re-hashing.
    """
    if isinstance(body, str):
        body_bytes = body.encode("utf-8")
    else:
        body_bytes = body
    return hashlib.sha256(body_bytes).hexdigest()


def _now_utc() -> datetime:
    """RFC3339-compatible timezone-aware UTC datetime.

    Wrapped in a helper so tests can monkeypatch a fixed clock. Real callers
    rarely need to override; ``captured_at`` parameters on the build helpers
    handle the when-the-state-was-actually-true vs when-we-stamped distinction.
    """
    return datetime.now(timezone.utc)


def build_cli_metadata(
    *,
    body: str | bytes,
    source_uri: str,
    source_type: SourceType,
    captured_at: datetime | None = None,
    source_version: str | None = None,
    redaction_summary: RedactionSummary | None = None,
) -> EvidenceAuditMetadata:
    """Stamp metadata for a manual CLI write.

    ``captured_at`` defaults to now. Override when the underlying state was
    captured at a different time than the write — e.g., a screenshot taken
    yesterday but uploaded today.
    """
    return EvidenceAuditMetadata(
        producer_kind="cli",
        producer_id="cli",
        producer_version=_pretorin_version,
        captured_at=captured_at if captured_at is not None else _now_utc(),
        source_type=source_type,
        source_uri=source_uri,
        source_version=source_version,
        content_hash=compute_content_hash(body),
        redaction_summary=redaction_summary,
        recipe_selection=None,
    )


def build_agent_metadata(
    *,
    body: str | bytes,
    source_uri: str,
    source_type: SourceType,
    agent_id: str,
    agent_version: str | None = None,
    captured_at: datetime | None = None,
    source_version: str | None = None,
    redaction_summary: RedactionSummary | None = None,
) -> EvidenceAuditMetadata:
    """Stamp metadata for an agent-driven write.

    ``agent_id`` identifies which agent runtime did the work — for pretorin's
    own ``CodexAgent``, pass ``"codex-agent"``; for an external agent acting via
    MCP, pass the agent name the caller supplies. ``agent_version`` is the model
    id or runtime version when known.
    """
    return EvidenceAuditMetadata(
        producer_kind="agent",
        producer_id=agent_id,
        producer_version=agent_version,
        captured_at=captured_at if captured_at is not None else _now_utc(),
        source_type=source_type,
        source_uri=source_uri,
        source_version=source_version,
        content_hash=compute_content_hash(body),
        redaction_summary=redaction_summary,
        recipe_selection=None,
    )


def build_recipe_metadata(
    *,
    body: str | bytes,
    source_uri: str,
    source_type: SourceType,
    recipe_id: str,
    recipe_version: str,
    captured_at: datetime | None = None,
    source_version: str | None = None,
    redaction_summary: RedactionSummary | None = None,
) -> EvidenceAuditMetadata:
    """Stamp metadata for a write made inside a recipe execution context.

    Called by the recipe runtime (WS2) when a recipe's scripts emit evidence /
    narrative through the platform-API write tools. The recipe context's
    ``recipe_selection`` record is attached separately by the caller after the
    write tool returns; this helper does not embed it because the selection
    record is only known at the workflow layer (WS5), not at the recipe-script
    layer.
    """
    return EvidenceAuditMetadata(
        producer_kind="recipe",
        producer_id=recipe_id,
        producer_version=recipe_version,
        captured_at=captured_at if captured_at is not None else _now_utc(),
        source_type=source_type,
        source_uri=source_uri,
        source_version=source_version,
        content_hash=compute_content_hash(body),
        redaction_summary=redaction_summary,
        recipe_selection=None,
    )


__all__ = [
    "build_agent_metadata",
    "build_cli_metadata",
    "build_recipe_metadata",
    "compute_content_hash",
]
