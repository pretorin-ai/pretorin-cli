"""Shared exception hierarchy for the recipe system.

Per Section 2 finding C3 of the plan-eng-review: every recipe-system component
raises errors from one type tree so callers (CLI, MCP, internal tools) can
distinguish failure modes consistently.

Tree:
- ``RecipeError`` (base; never raised directly)
  - ``RecipeManifestError`` — malformed ``recipe.md`` (missing frontmatter,
    invalid YAML, schema validation failure, broken script reference, etc.)
  - ``RecipeContextError`` — recipe execution context lifecycle issues
    - ``RecipeContextAlreadyActiveError`` — caller tried to start a recipe while
      another is already active in the same session (nesting forbidden v1)
    - ``RecipeContextExpiredError`` — context_id has passed the 1-hour expiry
      window or never existed
    - ``RecipeContextSessionMismatchError`` — context_id was created in a
      different MCP session than the caller
  - ``RecipeExecutionError`` — runtime failure inside a recipe's scripts
    (subprocess failure, timeout, exception bubble-up)
  - ``RecipeExtractionError`` — engagement-layer entity extraction surfaced
    invalid or incoherent entities (cross-check rejection)
"""

from __future__ import annotations


class RecipeError(Exception):
    """Base for every recipe-system exception."""


class RecipeManifestError(RecipeError):
    """``recipe.md`` is malformed or violates the manifest schema.

    Raised by the loader at load-time for the recipe being inspected; per the
    per-recipe validation isolation rule, one bad recipe does not break the
    registry — the malformed recipe is simply unavailable.
    """


class RecipeContextError(RecipeError):
    """Base for recipe-execution-context lifecycle errors."""


class RecipeContextAlreadyActiveError(RecipeContextError):
    """A recipe context is already active in this session.

    v1 forbids nesting: one recipe per logical task. Future v2 may allow
    composition (``depends_on`` / ``extends``) but for now nesting indicates
    the calling agent forgot to close a prior context.
    """


class RecipeContextExpiredError(RecipeContextError):
    """The supplied ``context_id`` is unknown or past its expiry window.

    Auto-expiry after 1 hour with no activity. Callers receiving this error
    should call ``pretorin_start_recipe`` again to obtain a fresh context.
    """


class RecipeContextSessionMismatchError(RecipeContextError):
    """The supplied ``context_id`` was created in a different session.

    Recipe contexts are scoped to MCP session id to prevent the orphan-context-
    from-prior-session class of bugs.
    """


class RecipeExecutionError(RecipeError):
    """Runtime failure inside a recipe's scripts."""


class RecipeExtractionError(RecipeError):
    """Engagement-layer entity extraction surfaced invalid entities.

    Raised when the calling agent's claimed system_id / framework_id /
    control_ids fail the coherence cross-check (e.g., control id doesn't
    exist in the claimed framework, framework_id doesn't match the system's
    active framework).
    """
