"""Recipe script execution helper.

Per the design's WS2 §3 ("Recipe script contract"): each script in a recipe
is a Python file with one ``async run(ctx, **params) -> dict`` callable.
Loaded by direct ``importlib.import_module``, not subprocess. The recipe's
``scripts/`` directory is added to ``sys.path`` for the duration of the
import.

This module is the only place pretorin actually executes recipe-author code.
It's still NOT a recipe-level LLM — scripts are deterministic Python — but
it IS server-side code execution, which means trust gating matters. The MCP
handler that dispatches to ``run_script`` checks the active recipe context
and the recipe's tier before allowing execution.
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pretorin.recipes.errors import RecipeExecutionError, RecipeManifestError
from pretorin.recipes.loader import LoadedRecipe

logger = logging.getLogger(__name__)


@dataclass
class RecipeScriptContext:
    """The ``ctx`` argument passed to every script's ``run`` function.

    Per RFC 0001 §"Tool surface": carries current system + framework, the
    authenticated API client, a logger, and the recipe id/version (for any
    audit-metadata stamping the script does itself when it makes platform-
    API write calls outside the per-tool MCP path).

    Scripts that make their own writes should pass ``recipe_context_id`` to
    the platform-API tool calls so audit metadata stamps correctly.
    """

    system_id: str | None
    framework_id: str | None
    api_client: Any  # PretorianClient — typed loosely to avoid import cycle
    logger: logging.Logger
    recipe_id: str
    recipe_version: str
    recipe_context_id: str | None
    """The active execution context id, when running inside a recipe context."""


@contextmanager
def _scripts_dir_on_syspath(scripts_dir: Path) -> Iterator[None]:
    """Context manager: add ``scripts_dir`` to ``sys.path`` for the duration.

    Scripts can ``import sibling_module`` to reach files inside the same
    ``scripts/`` directory. Path is removed after the block so we don't leak
    test fixtures or community recipes into the global module namespace.
    """
    str_path = str(scripts_dir)
    sys.path.insert(0, str_path)
    try:
        yield
    finally:
        try:
            sys.path.remove(str_path)
        except ValueError:
            pass


async def run_script(
    *,
    recipe: LoadedRecipe,
    script_name: str,
    ctx: RecipeScriptContext,
    params: dict[str, Any],
) -> dict[str, Any]:
    """Execute one of a recipe's declared scripts.

    Looks up the ``ScriptDecl`` for ``script_name`` in the recipe's manifest,
    resolves the script file, imports the module via importlib, and calls
    its ``async run(ctx, **params) -> dict`` callable. The script's return
    is passed through to the caller.

    Raises:
        RecipeManifestError: script_name not declared in the manifest, or
            the script file doesn't exist on disk.
        RecipeExecutionError: the script's ``run`` callable raised, or the
            script file imports cleanly but doesn't define ``run``.
    """
    if script_name not in recipe.manifest.scripts:
        raise RecipeManifestError(
            f"recipe {recipe.manifest.id!r} has no script named {script_name!r}; "
            f"available: {sorted(recipe.manifest.scripts.keys())}"
        )

    script_decl = recipe.manifest.scripts[script_name]
    recipe_dir = recipe.path.parent
    script_file = (recipe_dir / script_decl.path).resolve()

    if not script_file.is_file():
        raise RecipeManifestError(
            f"script {script_name!r} declared at {script_decl.path!r} but file {script_file} does not exist"
        )

    scripts_dir = script_file.parent

    # Build a unique module name so multiple recipes' scripts don't collide
    # in sys.modules. Includes the recipe id so debugging traces are clear.
    module_name = f"_pretorin_recipe_{recipe.manifest.id.replace('-', '_')}_{script_name}"

    with _scripts_dir_on_syspath(scripts_dir):
        spec = importlib.util.spec_from_file_location(module_name, script_file)
        if spec is None or spec.loader is None:
            raise RecipeExecutionError(f"Failed to build import spec for {script_file}")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            raise RecipeExecutionError(f"Importing recipe script {script_file} failed: {exc}") from exc

        run_callable = getattr(module, "run", None)
        if run_callable is None:
            raise RecipeExecutionError(
                f"Recipe script {script_file} must define `async def run(ctx, **params) -> dict`"
            )

        try:
            result = await run_callable(ctx, **params)
        except Exception as exc:
            raise RecipeExecutionError(f"Recipe script {recipe.manifest.id}/{script_name} raised: {exc}") from exc

    if not isinstance(result, dict):
        raise RecipeExecutionError(
            f"Recipe script {recipe.manifest.id}/{script_name} must return a dict; got {type(result).__name__}"
        )
    return result


__all__ = [
    "RecipeScriptContext",
    "run_script",
]
