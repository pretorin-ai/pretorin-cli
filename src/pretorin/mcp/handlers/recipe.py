"""MCP handlers for recipe execution context lifecycle.

``pretorin_start_recipe`` opens a server-side context; ``pretorin_end_recipe``
closes it and returns the ``RecipeResult`` summary.

Per the design's WS2 §5, the calling agent passes the returned ``context_id``
on subsequent platform-API write tool calls (``pretorin_create_evidence``,
``pretorin_create_evidence_batch``, etc.) which look up the context and stamp
``producer_kind="recipe"`` automatically. Stamping wiring lives in
``mcp/handlers/evidence.py`` (Phase B integration); these two handlers expose
the lifecycle.
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
)
from pretorin.recipes.registry import RecipeRegistry

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
