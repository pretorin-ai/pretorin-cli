"""Tests for the recipe script runner (importlib-based execution)."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest

from pretorin.recipes.errors import RecipeExecutionError, RecipeManifestError
from pretorin.recipes.loader import clear_cache, load_explicit_path
from pretorin.recipes.runner import RecipeScriptContext, run_script

_FIXTURES = Path(__file__).parent / "fixtures" / "valid"


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    clear_cache()


def _build_recipe_with_script(
    tmp_path: Path,
    script_body: str,
    *,
    recipe_id: str = "test-runner-recipe",
) -> Path:
    """Copy the example fixture and overwrite scripts/example.py with custom code."""
    target = tmp_path / recipe_id
    shutil.copytree(_FIXTURES / "example-recipe", target)
    # Rewrite recipe.md to use the custom id.
    recipe_md = (target / "recipe.md").read_text().replace("id: example-recipe", f"id: {recipe_id}")
    (target / "recipe.md").write_text(recipe_md)
    scripts_dir = target / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "example.py").write_text(script_body)
    return target


def _make_ctx(recipe_id: str = "test-runner-recipe") -> RecipeScriptContext:
    return RecipeScriptContext(
        system_id="sys-1",
        framework_id="fw-1",
        api_client=None,
        logger=logging.getLogger("test"),
        recipe_id=recipe_id,
        recipe_version="0.1.0",
        recipe_context_id="ctx-test",
    )


@pytest.mark.asyncio
async def test_run_script_happy_path(tmp_path: Path) -> None:
    target = _build_recipe_with_script(
        tmp_path,
        '"""."""\n\nasync def run(ctx, **params):\n    return {"ok": True, "input": params.get("input")}\n',
    )
    recipe = load_explicit_path(target)
    result = await run_script(
        recipe=recipe,
        script_name="example_tool",
        ctx=_make_ctx(),
        params={"input": "hello"},
    )
    assert result == {"ok": True, "input": "hello"}


@pytest.mark.asyncio
async def test_run_script_unknown_name(tmp_path: Path) -> None:
    target = _build_recipe_with_script(tmp_path, '"""."""\nasync def run(ctx, **params):\n    return {}\n')
    recipe = load_explicit_path(target)
    with pytest.raises(RecipeManifestError, match="no script named"):
        await run_script(
            recipe=recipe,
            script_name="not-a-real-script",
            ctx=_make_ctx(),
            params={},
        )


@pytest.mark.asyncio
async def test_run_script_missing_file(tmp_path: Path) -> None:
    target = _build_recipe_with_script(tmp_path, '"""."""\nasync def run(ctx, **params):\n    return {}\n')
    # Now delete the script file the manifest references.
    (target / "scripts" / "example.py").unlink()
    recipe = load_explicit_path(target)
    with pytest.raises(RecipeManifestError, match="does not exist"):
        await run_script(
            recipe=recipe,
            script_name="example_tool",
            ctx=_make_ctx(),
            params={},
        )


@pytest.mark.asyncio
async def test_run_script_no_run_function(tmp_path: Path) -> None:
    target = _build_recipe_with_script(tmp_path, '"""no run function here"""\n')
    recipe = load_explicit_path(target)
    with pytest.raises(RecipeExecutionError, match="must define"):
        await run_script(
            recipe=recipe,
            script_name="example_tool",
            ctx=_make_ctx(),
            params={},
        )


@pytest.mark.asyncio
async def test_run_script_runtime_error_wrapped(tmp_path: Path) -> None:
    """A script raising propagates as RecipeExecutionError with context."""
    target = _build_recipe_with_script(
        tmp_path,
        '"""."""\nasync def run(ctx, **params):\n    raise ValueError("boom")\n',
    )
    recipe = load_explicit_path(target)
    with pytest.raises(RecipeExecutionError, match="raised: boom"):
        await run_script(
            recipe=recipe,
            script_name="example_tool",
            ctx=_make_ctx(),
            params={},
        )


@pytest.mark.asyncio
async def test_run_script_non_dict_return_rejected(tmp_path: Path) -> None:
    """Scripts must return a dict; lists/strings/etc. are an error."""
    target = _build_recipe_with_script(
        tmp_path,
        '"""."""\nasync def run(ctx, **params):\n    return ["not", "a", "dict"]\n',
    )
    recipe = load_explicit_path(target)
    with pytest.raises(RecipeExecutionError, match="must return a dict"):
        await run_script(
            recipe=recipe,
            script_name="example_tool",
            ctx=_make_ctx(),
            params={},
        )


@pytest.mark.asyncio
async def test_run_script_can_use_ctx_recipe_id(tmp_path: Path) -> None:
    """The ctx carries the active recipe id so scripts can stamp evidence correctly."""
    script_body = (
        '"""."""\n'
        "async def run(ctx, **params):\n"
        '    return {"recipe_id": ctx.recipe_id, "context_id": ctx.recipe_context_id}\n'
    )
    target = _build_recipe_with_script(tmp_path, script_body)
    recipe = load_explicit_path(target)
    result = await run_script(
        recipe=recipe,
        script_name="example_tool",
        ctx=_make_ctx(),
        params={},
    )
    assert result == {"recipe_id": "test-runner-recipe", "context_id": "ctx-test"}


@pytest.mark.asyncio
async def test_run_script_sys_path_cleaned_after_run(tmp_path: Path) -> None:
    """The scripts/ dir is removed from sys.path after the script returns."""
    import sys

    target = _build_recipe_with_script(
        tmp_path,
        '"""."""\nasync def run(ctx, **params):\n    return {}\n',
    )
    recipe = load_explicit_path(target)
    scripts_dir = str((target / "scripts").resolve())
    assert scripts_dir not in sys.path

    await run_script(
        recipe=recipe,
        script_name="example_tool",
        ctx=_make_ctx(),
        params={},
    )

    assert scripts_dir not in sys.path
