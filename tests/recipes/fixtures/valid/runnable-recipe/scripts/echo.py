"""Echo script for the runnable-recipe test fixture."""

from __future__ import annotations

from typing import Any


async def run(ctx: Any, **params: Any) -> dict[str, Any]:
    return {
        "greeting": "hello from runnable-recipe",
        "params": params,
        "recipe_context_id": ctx.recipe_context_id,
        "recipe_id": ctx.recipe_id,
        "recipe_version": ctx.recipe_version,
    }
