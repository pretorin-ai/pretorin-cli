"""Shared workflow primitives for narratives, evidence, and notes."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pretorin.client.api import PretorianClient, PretorianClientError
from pretorin.client.config import Config
from pretorin.client.models import EvidenceCreate, EvidenceItemResponse
from pretorin.scope import ExecutionScope
from pretorin.utils import normalize_control_id
from pretorin.workflows.markdown_quality import ensure_audit_markdown

logger = logging.getLogger(__name__)

MATCH_BASIS_EXACT = "exact_name_desc_type_control_framework"
MATCH_BASIS_NONE = "none"


def _normalize_text(value: str | None) -> str:
    """Normalize free-form text for stable matching."""
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip().lower()


def _safe_value(value: str) -> str:
    """Collapse line breaks in template values to keep them one-line."""
    return re.sub(r"\s+", " ", value).strip()


def build_narrative_todo_block(
    missing_item: str,
    required_manual_action: str,
    suggested_evidence_type: str,
) -> str:
    """Create the canonical narrative TODO placeholder block.

    Issue #79: `suggested_evidence_type` is required. The authoring call
    site knows best what artifact the reviewer should produce, so there's
    no safe default.
    """
    return (
        "[[PRETORIN_TODO]]\n"
        f"missing_item: {_safe_value(missing_item)}\n"
        "reason: Not observable from current workspace and connected MCP systems\n"
        f"required_manual_action: {_safe_value(required_manual_action)}\n"
        f"suggested_evidence_type: {_safe_value(suggested_evidence_type)}\n"
        "[[/PRETORIN_TODO]]"
    )


def build_gap_note(
    gap: str,
    observed: str,
    missing: str,
    why_missing: str,
    manual_next_step: str,
) -> str:
    """Create the canonical control gap note format."""
    return (
        f"Gap: {_safe_value(gap)}\n"
        f"Observed: {_safe_value(observed)}\n"
        f"Missing: {_safe_value(missing)}\n"
        f"Why missing: {_safe_value(why_missing)}\n"
        f"Manual next step: {_safe_value(manual_next_step)}"
    )


def _evidence_key(
    name: str,
    description: str | None,
    evidence_type: str | None,
    control_id: str | None,
    framework_id: str | None,
) -> str:
    normalized_control_id = normalize_control_id(control_id) if control_id else ""
    return "|".join(
        [
            _normalize_text(name),
            _normalize_text(description),
            _normalize_text(evidence_type or ""),
            _normalize_text(normalized_control_id),
            _normalize_text(framework_id or ""),
        ]
    )


def _sort_key_collected_at(item: EvidenceItemResponse) -> tuple[int, str]:
    """Sort evidence by collected_at descending, falling back to id."""
    if item.collected_at:
        try:
            normalized = item.collected_at.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
            return (1, dt.isoformat())
        except ValueError:
            pass
    return (0, item.id)


@dataclass
class EvidenceUpsertResult:
    """Outcome of evidence upsert."""

    evidence_id: str
    created: bool
    linked: bool
    match_basis: str = MATCH_BASIS_NONE
    platform_response: dict[str, Any] = field(default_factory=dict)
    link_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON and MCP responses."""
        payload = {
            "evidence_id": self.evidence_id,
            "created": self.created,
            "linked": self.linked,
            "match_basis": self.match_basis,
        }
        if self.link_error:
            payload["link_error"] = self.link_error
        return payload


async def resolve_system(
    client: PretorianClient,
    system: str | None = None,
    scope: ExecutionScope | None = None,
) -> tuple[str, str]:
    """Resolve a system hint/name/ID to concrete (system_id, system_name).

    When *scope* is provided and *system* is None, uses the scope's system_id
    instead of falling back to shared config.
    """
    systems = await client.list_systems()
    if not systems:
        raise PretorianClientError("No systems found. Create a system first.")

    if system:
        system_lower = system.lower()
        for candidate in systems:
            if candidate.get("id") == system or candidate.get("name", "").lower().startswith(system_lower):
                return candidate["id"], candidate.get("name", candidate["id"])
        raise PretorianClientError(f"System not found: {system}")

    # Prefer run-local scope over ambient config
    active_system_id: str | None = None
    if scope is not None:
        active_system_id = scope.system_id
    else:
        config = Config()
        active_system_id = config.get("active_system_id")

    if active_system_id:
        for candidate in systems:
            if candidate.get("id") == active_system_id:
                return candidate["id"], candidate.get("name", candidate["id"])

    if len(systems) == 1:
        candidate = systems[0]
        return candidate["id"], candidate.get("name", candidate["id"])

    raise PretorianClientError(
        "Multiple systems found. Use --system to specify one, or set context with 'pretorin context set'."
    )


async def upsert_evidence(
    client: PretorianClient,
    *,
    system_id: str,
    name: str,
    description: str,
    evidence_type: str,
    control_id: str | None = None,
    framework_id: str | None = None,
    source: str = "cli",
    dedupe: bool = True,
    search_limit: int = 200,
    code_context: dict[str, Any] | None = None,
) -> EvidenceUpsertResult:
    """Find-or-create scoped evidence and ensure system/control link.

    Issue #79: `evidence_type` is a required keyword argument. Callers that
    receive a possibly-AI-generated value should run
    `pretorin.evidence.types.normalize_evidence_type()` first; the CLI
    entry points hard-error when the user omits `-t/--type`.
    """
    ensure_audit_markdown(description, artifact_type="evidence_description")

    normalized_control_id = normalize_control_id(control_id) if control_id else None
    if not framework_id:
        raise ValueError("framework_id is required for scoped evidence updates")

    candidate_id: str | None = None

    if dedupe:
        key = _evidence_key(name, description, evidence_type, normalized_control_id, framework_id)
        existing = await client.list_evidence(
            system_id=system_id,
            framework_id=framework_id or "",
            control_id=normalized_control_id,
            limit=search_limit,
        )
        matches = [
            item
            for item in existing
            if _evidence_key(
                item.name,
                item.description,
                item.evidence_type,
                normalized_control_id,
                framework_id,
            )
            == key
        ]
        if matches:
            newest = sorted(matches, key=_sort_key_collected_at, reverse=True)[0]
            # If we have new code provenance fields, create enriched evidence rather
            # than reusing a record that lacks provenance. The platform's idempotency
            # key includes code_* fields, so the enriched record is distinct.
            if code_context:
                candidate_id = None
            else:
                candidate_id = newest.id

    created = False
    match_basis = MATCH_BASIS_NONE
    platform_response: dict[str, Any] = {}
    evidence_id = ""

    if candidate_id:
        evidence_id = candidate_id
        match_basis = MATCH_BASIS_EXACT
    else:
        created = True
        payload = EvidenceCreate(
            name=name,
            description=description,
            evidence_type=evidence_type,
            source=source,
            control_id=normalized_control_id,
            framework_id=framework_id,
            **(code_context or {}),
        )
        platform_response = await client.create_evidence(system_id, payload)
        evidence_id = str(platform_response.get("id", ""))

    linked = False
    link_error: str | None = None
    if evidence_id and normalized_control_id:
        if created:
            linked = bool(platform_response.get("linked")) or bool(platform_response.get("mapping_id"))
        else:
            try:
                await client.link_evidence_to_control(
                    evidence_id=evidence_id,
                    control_id=normalized_control_id,
                    system_id=system_id,
                    framework_id=framework_id or "",
                )
                linked = True
            except Exception as exc:  # noqa: BLE001
                link_error = str(exc)

    result = EvidenceUpsertResult(
        evidence_id=evidence_id,
        created=created,
        linked=linked,
        match_basis=match_basis,
        platform_response=platform_response,
        link_error=link_error,
    )
    logger.debug(
        "Evidence upsert result: id=%s created=%s linked=%s match_basis=%s",
        result.evidence_id,
        result.created,
        result.linked,
        result.match_basis,
    )
    if link_error:
        logger.warning("Evidence link error for %s: %s", evidence_id, link_error)
    return result
