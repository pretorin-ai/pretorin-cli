"""Canonical gap-note format for unresolved compliance gaps.

The format is the single source of truth used by both AI skill prompts
(agent/skills.py) and the campaign apply pipeline (workflows/campaign.py)
when it synthesizes a gap note for a rejected evidence recommendation.
"""

from __future__ import annotations

from typing import Any

GAP_NOTE_TEMPLATE = (
    "Gap: {title}\nObserved: {observed}\nMissing: {missing}\nWhy missing: {why}\nManual next step: {next_step}"
)


def synthesize_gap_note(rec: dict[str, Any], reason: str) -> str:
    """Build a canonical gap note for an evidence recommendation we rejected.

    `rec` is an AI-drafted evidence recommendation that failed validation
    (missing/invalid evidence_type, or any future content gate). `reason`
    describes why it was rejected. The note follows GAP_NOTE_TEMPLATE so
    platform reviewers see one consistent shape whether the note came from
    the AI or from the apply pipeline.

    Falls back to safe defaults when `rec` is malformed so a single bad
    recommendation never crashes the whole control.
    """
    title = _safe_str(rec, "name", default="AI-drafted evidence (rejected)")
    description = _safe_str(rec, "description", default="(no description provided)")
    proposed_type = _safe_str(rec, "evidence_type", default="(none)")

    return GAP_NOTE_TEMPLATE.format(
        title=title,
        observed=f"AI proposed evidence_type={proposed_type}: {description}",
        missing="Workspace-verified evidence artifact for this control.",
        why=reason,
        next_step=(
            "Either upload the matching artifact on the platform, or refine the "
            "control narrative to reflect how this requirement is actually met."
        ),
    )


def _safe_str(rec: dict[str, Any], key: str, *, default: str) -> str:
    value = rec.get(key) if isinstance(rec, dict) else None
    if value is None:
        return default
    text = str(value).strip()
    return text or default
