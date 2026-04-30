"""Output of the engagement layer — the routing decision."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from pretorin.engagement.entities import EngagementEntities

SelectedWorkflow = Literal[
    "single-control",
    "scope-question",
    "policy-question",
    "campaign",
]


class EngagementSelection(BaseModel):
    """The router's decision plus the inspect snapshot that informed it.

    Three success modes:

    1. **Routed** — ``selected_workflow`` is set, ``ambiguous`` is False.
       The calling agent reads the workflow body and follows it.
    2. **Inspect-only** — ``intent_verb=="inspect_status"``;
       ``selected_workflow`` is None, ``ambiguous`` is False, the calling
       agent just renders the inspect summary to the user.
    3. **Ambiguous** — ``ambiguous=True`` with a reason. The calling
       agent shows the user the ambiguity and asks for explicit
       confirmation before retrying with disambiguated entities.

    Hard-error cases (hallucinated entities) are MCP errors, not
    EngagementSelection responses — they fail fast before workflow
    selection runs.
    """

    entities: EngagementEntities
    inspect_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Read-side platform state pretorin loaded server-side: "
        "workflow_state, compliance_status, pending_families, pending_scope, pending_policy.",
    )
    selected_workflow: SelectedWorkflow | None = Field(
        default=None,
        description="The workflow the calling agent should run next. None for inspect_status or ambiguous.",
    )
    workflow_params: dict[str, Any] = Field(
        default_factory=dict,
        description="Params to pass when invoking the workflow (e.g., {'control_filter': [...]} for campaign).",
    )
    rule_matched: str = Field(
        default="",
        description="Which rule fired in the cascade, e.g. 'len(control_ids) == 1'. Empty when ambiguous.",
    )
    ambiguous: bool = Field(
        default=False,
        description="True when the rules couldn't pick or cross-check found a coherence problem.",
    )
    ambiguity_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of why the request couldn't be routed.",
    )


__all__ = ["EngagementSelection", "SelectedWorkflow"]
