"""Pydantic models for ``recipe.md`` frontmatter.

The manifest is the **public contract** between recipe authors and the pretorin
runtime. Frozen per ``contract_version``. Fields added later without breaking
existing recipes do not bump the version; removals or shape changes do.

Per RFC 0001 §"Frontmatter schema (v1)" with v1 amendments documented in the
design doc at WS2 §1 ("RFC 0001 v0.5 supersedes the original RFC...").

Tier signaling, schema versioning, and per-script param declarations are core
to v1 because:

- ``tier`` (set by the loader from source path) is what lets the agent prefer
  official over community recipes when scoring.
- ``recipe_schema_version`` and ``min_pretorin_version`` solve the
  "stable-API-for-markdown" trap codex flagged.
- Per-script ``ScriptDecl.params`` lets the MCP renderer emit a real
  ``inputSchema`` for each script tool the agent can call.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RecipeParam(BaseModel):
    """One input parameter for a recipe (or per-script tool).

    Mirrors RFC 0001's ``params`` schema. Used both at the recipe level (as
    inputs the calling agent supplies via ``pretorin_start_recipe``) and at
    the per-script level (as inputs to a specific script tool).
    """

    type: Literal["string", "array", "boolean", "integer", "number"]
    items: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema for array items; required when type='array'",
    )
    description: str = Field(..., min_length=1)
    default: Any | None = None
    required: bool = False


class RecipeRequires(BaseModel):
    """Environment requirements declared by a recipe.

    v1 captures the requirements but does not run probes — ``pretorin recipe
    check`` is deferred to v1.5. ``run`` does not block on missing requires;
    failures surface as runtime errors when scripts try to invoke missing
    tools. Recipe authors can still document requirements clearly.

    ``mcp`` (third-party MCP server requirements) is deferred to v1.5
    alongside MCP auto-exposure of recipes.
    """

    cli: list[dict[str, str]] = Field(
        default_factory=list,
        description="CLI binaries the recipe needs at runtime, e.g. [{name: 'inspec', probe: 'inspec --version'}]",
    )
    env: list[str] = Field(
        default_factory=list,
        description="Environment variable names the recipe reads",
    )


class ScriptDecl(BaseModel):
    """One script the recipe exposes as a callable tool.

    The MCP renderer emits one tool per ScriptDecl as
    ``pretorin_recipe_<recipe_id>_<tool_name>`` with ``inputSchema`` derived
    from ``params``. Per-script params are distinct from recipe-level params
    because individual scripts in a recipe routinely take different shapes
    of input (e.g., ``redact_secrets(text)`` vs ``compose_snippet(redacted_text,
    file_path, line_numbers)``).
    """

    path: str = Field(
        ...,
        description="Relative path to the .py file under the recipe directory",
    )
    description: str = Field(
        ...,
        min_length=1,
        description="One-liner describing what this tool does, surfaced to the agent",
    )
    params: dict[str, RecipeParam] = Field(default_factory=dict)
    timeout_seconds: int = Field(
        default=300,
        ge=1,
        description="Per-script wall-clock; total recipe wall-clock can override",
    )
    writes_evidence: bool = Field(
        default=False,
        description="Declared intent — used by the trust gate for community recipes",
    )


class RecipeManifest(BaseModel):
    """Frontmatter block parsed from ``recipe.md``.

    All required fields must be present or the loader raises ``RecipeManifestError``
    for that recipe (per per-recipe validation isolation, this does not break
    the registry).

    The loader sets ``tier`` from the recipe's source path **after** parsing
    the frontmatter; any author-declared tier in the manifest is overridden if
    the source path implies a different tier (per design WS2 §1: "Manifest-
    declared tier is at most a hint; loader path is authoritative.").
    """

    id: str = Field(..., min_length=1, pattern=r"^[a-z][a-z0-9-]*$")
    version: str = Field(..., min_length=1, description="SemVer-ish version string")
    name: str = Field(..., min_length=1, description="Display name")
    description: str = Field(
        ...,
        min_length=1,
        description="Self-contained description used by agents to pick this recipe",
    )
    use_when: str = Field(
        ...,
        min_length=1,
        description="Explicit guidance for the agent on when to pick this recipe",
    )
    produces: Literal["evidence", "narrative", "both", "answers"]
    tier: Literal["official", "partner", "community"] = Field(
        default="community",
        description="Trust signal; overridden by loader from source path",
    )
    author: str = Field(
        ...,
        min_length=1,
        description="Attribution; shown in list/show and stamped in evidence provenance",
    )
    license: str = Field(
        default="Apache-2.0",
        description="SPDX identifier; required when shared publicly",
    )
    params: dict[str, RecipeParam] = Field(default_factory=dict)
    requires: RecipeRequires = Field(default_factory=RecipeRequires)
    attests: list[dict[str, str]] = Field(
        default_factory=list,
        description=(
            "[{control, framework}] entries — hint/filter only, never a binding. "
            "Agent reasons over description, not over attests."
        ),
    )
    scripts: dict[str, ScriptDecl] = Field(
        default_factory=dict,
        description="tool_name → ScriptDecl mapping. tool_name appears as pretorin_recipe_<id>_<tool_name> via MCP.",
    )
    contract_version: int = Field(
        default=1,
        ge=1,
        description="Frozen v1 contract version. Bumps only on backwards-incompatible shape changes.",
    )
    recipe_schema_version: str = Field(
        default="1.0",
        description="Schema this recipe.md is written against; loader rejects newer-than-supported.",
    )
    min_pretorin_version: str | None = Field(
        default=None,
        description="SemVer; loader rejects if running pretorin is older",
    )

    @field_validator("id")
    @classmethod
    def _id_must_be_kebab_case(cls, value: str) -> str:
        """Recipe ids are lowercase-kebab — matches Python module name conventions
        and avoids filesystem-case-sensitivity issues across platforms."""
        if not value.islower() or "_" in value:
            raise ValueError(f"Recipe id {value!r} must be lowercase-kebab-case (e.g., 'code-evidence-capture')")
        return value
