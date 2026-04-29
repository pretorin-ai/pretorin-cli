"""MCP handlers for recipe lifecycle, discovery, and per-script execution.

WS2 Phase B handlers (lifecycle):
- ``pretorin_start_recipe`` opens a server-side context.
- ``pretorin_end_recipe`` closes it and returns the ``RecipeResult`` summary.

WS2 Phase C handlers (discovery + script execution):
- ``pretorin_list_recipes`` enumerates all loaded recipes (optionally filtered
  by tier) so external agents can find recipes without hardcoded ids.
- ``pretorin_get_recipe`` returns one recipe's full manifest and body — the
  playbook the calling agent reads.
- ``handle_run_recipe_script`` is the catch-all dispatcher for the dynamic
  per-script MCP tools (``pretorin_recipe_<id>_<tool>``), looking up the
  script via the registry and running its ``async run(ctx, **params)``
  callable in pretorin's process. Pretorin still does not run a recipe-level
  LLM — script execution is deterministic Python, not agent reasoning.
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import format_error, format_json, require, safe_args
from pretorin.recipes.context import get_default_store
from pretorin.recipes.errors import (
    RecipeContextAlreadyActiveError,
    RecipeContextError,
    RecipeError,
    RecipeExecutionError,
    RecipeManifestError,
)
from pretorin.recipes.registry import RecipeRegistry
from pretorin.recipes.runner import RecipeScriptContext, run_script

logger = logging.getLogger(__name__)


async def handle_start_recipe(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Open a recipe execution context.

    Inputs:
    - ``recipe_id`` (required): id of the recipe to start. Must be loadable
      from the registry; explicit-path invocations go through a different
      path.
    - ``recipe_version`` (required): the version the calling agent intends to
      run. Cross-checked against the loaded recipe; mismatch is an error.
    - ``params`` (optional): inputs the calling agent supplies, validated
      lightly here (full schema validation happens when scripts are invoked).
    - ``selection`` (optional): the structured ``RecipeSelection`` record from
      the engagement layer. Stored on the context for later use in audit
      metadata and the RecipeResult.

    Returns ``{context_id, recipe_id, recipe_version, body, expires_at}`` on
    success — body is the recipe.md content the calling agent reads as a
    playbook. ``expires_at`` is informational; callers who pass it back later
    aren't required to honor it (the server enforces).
    """
    logger.debug("handle_start_recipe called with %s", safe_args(arguments))
    err = require(arguments, "recipe_id", "recipe_version")
    if err:
        return format_error(err)

    recipe_id = str(arguments["recipe_id"])
    recipe_version = str(arguments["recipe_version"])
    params = arguments.get("params") or {}
    selection = arguments.get("selection")

    if not isinstance(params, dict):
        return format_error("params must be a JSON object/dict")
    if selection is not None and not isinstance(selection, dict):
        return format_error("selection must be a JSON object/dict")

    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    if entry is None:
        return format_error(f"No recipe found with id {recipe_id!r}")

    loaded = entry.active
    if loaded.manifest.version != recipe_version:
        return format_error(
            f"Recipe {recipe_id!r} is at version {loaded.manifest.version!r}, "
            f"but caller requested {recipe_version!r}. Re-fetch the recipe via "
            "pretorin_get_recipe to confirm the current version."
        )

    store = get_default_store()
    try:
        ctx = store.start_recipe(
            recipe_id=recipe_id,
            recipe_version=recipe_version,
            params=params,
            selection=selection,
        )
    except RecipeContextAlreadyActiveError as exc:
        return format_error(str(exc))

    return format_json(
        {
            "context_id": ctx.context_id,
            "recipe_id": ctx.recipe_id,
            "recipe_version": ctx.recipe_version,
            "body": loaded.body,
            "tier": loaded.manifest.tier,
            "started_at": ctx.started_at.isoformat(),
        }
    )


async def handle_end_recipe(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Close a recipe execution context and return its summary.

    Inputs:
    - ``context_id`` (required): the id returned by ``pretorin_start_recipe``.
    - ``status`` (optional): "pass" | "fail" | "needs_input". Defaults to "pass".

    Returns the ``RecipeResult`` shape: status, recipe_id/version, evidence and
    narrative counts, errors accumulated during execution, the selection
    record, and the elapsed wall-clock time.

    Calling ``end`` with an unknown/expired/cross-session ``context_id``
    raises ``RecipeContextExpiredError`` or ``RecipeContextSessionMismatchError``
    surfaced as MCP errors so the caller sees the failure mode clearly.
    """
    logger.debug("handle_end_recipe called with %s", safe_args(arguments))
    err = require(arguments, "context_id")
    if err:
        return format_error(err)

    context_id = str(arguments["context_id"])
    status = str(arguments.get("status", "pass"))
    if status not in {"pass", "fail", "needs_input"}:
        return format_error(f"status must be one of 'pass', 'fail', 'needs_input'; got {status!r}")

    store = get_default_store()
    try:
        result = store.end_recipe(context_id, status=status)
    except RecipeContextError as exc:
        return format_error(str(exc))

    return format_json(asdict(result))


# =============================================================================
# Phase C: discovery handlers
# =============================================================================


async def handle_list_recipes(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Enumerate loaded recipes for the calling agent.

    Optional filters: ``tier`` (one of "official", "partner", "community") and
    ``produces`` (one of "evidence", "narrative", "both"). Returns a list of
    summary dicts the agent can scan to pick a recipe — id, name, tier,
    description, use_when, produces, version, author, source.

    Body is intentionally NOT included — use ``pretorin_get_recipe`` for the
    full body once the agent has narrowed down the candidate.
    """
    logger.debug("handle_list_recipes called with %s", safe_args(arguments))

    tier_filter = arguments.get("tier")
    produces_filter = arguments.get("produces")

    registry = RecipeRegistry()
    entries = registry.entries()

    if tier_filter:
        entries = [e for e in entries if e.active.manifest.tier == tier_filter]
    if produces_filter:
        entries = [e for e in entries if e.active.manifest.produces == produces_filter]

    return format_json(
        {
            "total": len(entries),
            "recipes": [
                {
                    "id": e.active.manifest.id,
                    "name": e.active.manifest.name,
                    "tier": e.active.manifest.tier,
                    "version": e.active.manifest.version,
                    "author": e.active.manifest.author,
                    "description": e.active.manifest.description,
                    "use_when": e.active.manifest.use_when,
                    "produces": e.active.manifest.produces,
                    "source": e.active.source,
                    "shadowed": len(e.shadowed) > 0,
                }
                for e in entries
            ],
        }
    )


async def handle_get_recipe(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Return one recipe's full manifest and body.

    The body is the markdown playbook the calling agent reads to understand
    the procedure. The manifest carries the params/scripts/requires schemas
    the agent needs to invoke the recipe correctly.
    """
    logger.debug("handle_get_recipe called with %s", safe_args(arguments))
    err = require(arguments, "recipe_id")
    if err:
        return format_error(err)

    recipe_id = str(arguments["recipe_id"])
    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    if entry is None:
        return format_error(f"No recipe found with id {recipe_id!r}")

    return format_json(
        {
            "id": entry.active.manifest.id,
            "manifest": entry.active.manifest.model_dump(),
            "body": entry.active.body,
            "source": entry.active.source,
            "shadowed_count": len(entry.shadowed),
        }
    )


# =============================================================================
# Phase C: per-recipe-script tool dispatcher
# =============================================================================


async def handle_run_recipe_script(
    client: PretorianClient,
    arguments: dict[str, Any],
    *,
    tool_name: str,
) -> list[TextContent] | CallToolResult:
    """Dispatch a ``pretorin_recipe_<id>__<tool>`` MCP call to the script runtime.

    The catch-all called by ``mcp/server.py`` when a tool name matches the
    per-recipe-script pattern. Looks up the (recipe, script) pair via the
    registry's tool-name map, validates the active recipe context, then runs
    the script's ``async run(ctx, **params)`` callable via ``run_script``.

    Phase C invariants:
    - An active recipe execution context is REQUIRED. Calling a script tool
      outside ``pretorin_start_recipe`` / ``pretorin_end_recipe`` is an error.
    - The active context's recipe id must match the script's recipe id.
      Calling ``pretorin_recipe_code_evidence_capture__redact_secrets`` while
      a different recipe's context is active is rejected.
    - For ``community``-tier recipes, the calling agent has already chosen
      to load the recipe (via ``pretorin_start_recipe``) — no second trust
      gate at the per-script level.
    """
    logger.debug("handle_run_recipe_script(%s) called with %s", tool_name, safe_args(arguments))

    registry = RecipeRegistry()
    tool_map = registry.get_script_tool_map()
    if tool_name not in tool_map:
        return format_error(f"No recipe script tool registered as {tool_name!r}")
    recipe_id, script_name = tool_map[tool_name]

    entry = registry.get(recipe_id)
    if entry is None:
        # Race condition: tool was in the map but recipe gone now.
        return format_error(f"Recipe {recipe_id!r} no longer available")

    # Active context required + must match the script's recipe.
    store = get_default_store()
    active_contexts = [
        ctx for ctx in store._contexts.values() if not ctx.is_expired() and ctx.session_id == store.session_id
    ]
    if not active_contexts:
        return format_error(
            f"Recipe script {tool_name!r} requires an active recipe execution "
            "context. Call pretorin_start_recipe first."
        )
    active = active_contexts[0]
    if active.recipe_id != recipe_id:
        return format_error(
            f"Active recipe context is for {active.recipe_id!r}; cannot dispatch "
            f"to {recipe_id!r}'s script. End the current context first."
        )

    # Build the ctx the script's run() receives. Subset of platform context
    # plus the recipe metadata for stamping any further writes the script makes.
    ctx = RecipeScriptContext(
        system_id=getattr(client, "active_system_id", None),
        framework_id=getattr(client, "active_framework_id", None),
        api_client=client,
        logger=logger.getChild(f"recipe.{recipe_id}.{script_name}"),
        recipe_id=recipe_id,
        recipe_version=active.recipe_version,
        recipe_context_id=active.context_id,
    )

    # Strip framework arg pollution: anything from MCP routing isn't the
    # script's params. Future v1.5 adds per-script params validation here.
    script_params = {k: v for k, v in arguments.items() if k != "_meta"}

    try:
        result = await run_script(
            recipe=entry.active,
            script_name=script_name,
            ctx=ctx,
            params=script_params,
        )
    except RecipeManifestError as exc:
        return format_error(f"Recipe manifest error: {exc}")
    except RecipeExecutionError as exc:
        store.record_error(active.context_id, str(exc))
        return format_error(f"Recipe script execution failed: {exc}")
    except RecipeError as exc:
        return format_error(str(exc))

    return format_json(result)
