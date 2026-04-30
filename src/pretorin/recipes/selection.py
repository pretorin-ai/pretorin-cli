"""Recipe selection — the per-item routing decision inside a workflow.

Workflows iterate items (one control, one questionnaire question, one
campaign batch). At each item the calling agent (or pretorin's
CodexAgent for server-side iteration) needs to decide *which* recipe
to run. ``RecipeSelection`` captures that decision.

Per the design WS5 §"Shared mechanism": every workflow's per-item step
emits a ``RecipeSelection`` record. The record persists on the
resulting evidence (or narrative) record's audit_metadata so an auditor
can trace which recipe drove which artifact, with the alternatives the
agent considered and the reason for the pick.

For v1, the selector is a deterministic hint-match over recipes'
``attests`` entries. When no recipe matches, the workflow falls through
to freelance generation. Smarter selection (LLM-assisted scoring,
``required_inputs_present`` checking, etc.) lands in v1.5.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from pretorin.recipes.registry import RecipeRegistry


class RecipeSelection(BaseModel):
    """One per-item recipe decision recorded for audit.

    Stored as ``EvidenceAuditMetadata.recipe_selection`` (or the narrative
    equivalent). Auditors can query by this field to trace which recipes
    drove which artifacts across a campaign.
    """

    selected_recipe: str | None = Field(
        default=None,
        description="Recipe id chosen for this item. None means freelance fallback.",
    )
    selected_recipe_version: str | None = Field(
        default=None,
        description="Version of the selected recipe at decision time. None when no recipe was picked.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        default="low",
        description=(
            "How confident the selector is. v1 hint-match → 'high' on attests "
            "exact match, 'low' otherwise. Drives nothing in v1 — audit signal."
        ),
    )
    reason: str = Field(
        default="",
        description="Plain-English explanation of why this recipe (or freelance) was picked.",
    )
    alternatives_considered: list[str] = Field(
        default_factory=list,
        description="Other recipe ids the selector saw but did not pick.",
    )
    required_inputs_present: bool = Field(
        default=True,
        description=(
            "v1 always True (selector doesn't validate inputs). v1.5 will "
            "verify the picked recipe's required params are available before "
            "committing to it."
        ),
    )
    fallback_to_freelance: bool = Field(
        default=False,
        description=(
            "True when no recipe matched and the workflow used freelance "
            "generation instead. The audit trail captures this so spotty "
            "recipe coverage is visible."
        ),
    )


def select_recipe_for_drafting(
    *,
    framework_id: str,
    control_id: str,
    registry: RecipeRegistry | None = None,
) -> RecipeSelection:
    """Pick a recipe for narrative-and-evidence drafting on one control.

    Hint-match: surveys every loaded recipe's ``attests`` entries for a
    matching ``(control, framework)`` pair. The first match wins. When
    nothing matches, returns a ``RecipeSelection`` with
    ``fallback_to_freelance=True``.

    The function reads the registry at call time so newly-loaded
    community recipes show up automatically without server restart.

    Returns a record the caller attaches to the resulting artifact's
    audit_metadata.recipe_selection.
    """
    reg = registry or RecipeRegistry()

    matches: list[str] = []
    selected: str | None = None
    selected_version: str | None = None
    selected_reason = ""

    normalized_control = control_id.strip().lower()
    normalized_framework = framework_id.strip()

    for entry in reg.entries():
        manifest = entry.active.manifest
        for attests in manifest.attests:
            attested_control = str(attests.get("control", "")).strip().lower()
            attested_framework = str(attests.get("framework", "")).strip()
            if attested_control != normalized_control:
                continue
            if attested_framework and attested_framework != normalized_framework:
                continue
            matches.append(manifest.id)
            if selected is None:
                selected = manifest.id
                selected_version = manifest.version
                selected_reason = (
                    f"Recipe {manifest.id!r} attests control={attested_control!r} "
                    f"framework={attested_framework!r}; matched on hint."
                )

    if selected is None:
        return RecipeSelection(
            selected_recipe=None,
            selected_recipe_version=None,
            confidence="low",
            reason=(
                f"No recipe in the registry attests control={normalized_control!r} "
                f"framework={normalized_framework!r}; falling back to freelance "
                "drafting via CodexAgent."
            ),
            alternatives_considered=[],
            required_inputs_present=True,
            fallback_to_freelance=True,
        )

    alternatives = [m for m in matches if m != selected]
    return RecipeSelection(
        selected_recipe=selected,
        selected_recipe_version=selected_version,
        confidence="high",
        reason=selected_reason,
        alternatives_considered=alternatives,
        required_inputs_present=True,
        fallback_to_freelance=False,
    )


def to_audit_dict(selection: RecipeSelection) -> dict[str, Any]:
    """Serialize a RecipeSelection for ``EvidenceAuditMetadata.recipe_selection``.

    The audit-metadata field is typed as ``dict[str, Any]`` for forward
    compatibility; this helper is the single conversion site so the
    on-the-wire shape stays consistent.
    """
    return selection.model_dump(mode="json")


__all__ = [
    "RecipeSelection",
    "select_recipe_for_drafting",
    "to_audit_dict",
]
