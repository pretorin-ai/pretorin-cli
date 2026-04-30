"""Entities the calling agent extracts and passes to pretorin_start_task.

The calling agent's LLM does the prompt parsing; this module declares the
shape pretorin expects back. Validation here is structural only — the
cross-check layer (``cross_check.py``) verifies entities against actual
platform state.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

IntentVerb = Literal[
    "work_on",
    "collect_evidence",
    "draft_narrative",
    "answer",
    "campaign",
    "inspect_status",
]
"""What the user wants to do at a high level. The calling agent picks one
based on the prompt's verb pattern. The router uses this as the primary
discriminator before falling through to entity-shape rules.

- ``work_on`` — generic "do something with this control/system"
- ``collect_evidence`` — explicit evidence-gathering ask
- ``draft_narrative`` — explicit narrative-writing ask
- ``answer`` — questionnaire work (scope or policy)
- ``campaign`` — bulk control work (a family, a framework, a filter)
- ``inspect_status`` — read-only "what's the state" ask; no workflow runs
"""


class EngagementEntities(BaseModel):
    """Structured entities extracted from the user prompt.

    Every list field defaults to empty rather than None so the rule
    cascade can use ``len(...)`` without None-checks. ``raw_prompt`` is
    audit-only — pretorin does not parse it.
    """

    system_id: str | None = Field(
        default=None,
        description="System name or id the user named. None when the user didn't say.",
    )
    framework_id: str | None = Field(
        default=None,
        description="Framework id the user named (e.g., 'nist-800-53-r5').",
    )
    control_ids: list[str] = Field(
        default_factory=list,
        description="Explicit control ids the user mentioned, normalized lowercase.",
    )
    scope_question_ids: list[str] = Field(
        default_factory=list,
        description="Specific scope question ids the user named.",
    )
    policy_question_ids: list[str] = Field(
        default_factory=list,
        description="Specific policy question ids the user named.",
    )
    intent_verb: IntentVerb = Field(
        ...,
        description="High-level intent the calling agent inferred from the prompt.",
    )
    raw_prompt: str = Field(
        ...,
        min_length=1,
        description="Original user prompt text. Audit only — pretorin doesn't parse it.",
    )


__all__ = ["EngagementEntities", "IntentVerb"]
