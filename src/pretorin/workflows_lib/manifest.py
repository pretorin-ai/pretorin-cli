"""Pydantic model for ``workflow.md`` frontmatter.

Workflows are simpler than recipes — no scripts, no audit-metadata
stamping, no per-script param schemas. The frontmatter just describes
*what* the workflow is and *when* the calling agent should pick it.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WorkflowManifest(BaseModel):
    """Frontmatter block parsed from ``workflow.md``.

    Per the design WS5 §"Shared mechanism": workflows are the layer that
    iterates items (controls, scope questions, campaign batches) and tells
    the agent how to pick a recipe per item. The body of ``workflow.md``
    is the playbook prose the agent reads.
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(..., min_length=1, description="SemVer-ish")
    name: str = Field(..., min_length=1, description="Display name")
    description: str = Field(
        ...,
        min_length=1,
        description="Self-contained description used by the engagement layer to pick this workflow.",
    )
    use_when: str = Field(
        ...,
        min_length=1,
        description="Explicit guidance for when this workflow fits.",
    )
    produces: Literal["evidence", "narrative", "answers", "mixed"]
    iterates_over: Literal[
        "single_control",
        "scope_questions",
        "policy_questions",
        "campaign_items",
    ] = Field(
        ...,
        description="What the workflow's item iteration loop walks. Drives engagement-layer selection.",
    )
    recipes_commonly_used: list[str] = Field(
        default_factory=list,
        description=(
            "Recipe ids the calling agent often picks while running this workflow. "
            "Hint, not binding — the agent reads pretorin_list_recipes at runtime "
            "and picks per-item using the recipe's description."
        ),
    )
    contract_version: int = Field(
        default=1,
        ge=1,
        description="Frontmatter shape version. Bumps only on breaking changes.",
    )


__all__ = ["WorkflowManifest"]
