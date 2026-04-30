"""Tests for the ``pretorin recipe`` CLI commands.

Covers ``list / show / new / validate / run``.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.recipe import app
from pretorin.recipes import loader as loader_module
from pretorin.recipes.context import reset_default_store
from pretorin.recipes.loader import clear_cache

_FIXTURES = Path(__file__).parent / "recipes" / "fixtures" / "valid"

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    clear_cache()
    reset_default_store()


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Point loader path-resolution helpers at tmp_path so each CLI test gets a clean tree.

    Loader and scaffolder both go through ``_user_recipes_root`` /
    ``_builtin_recipes_root`` so a single monkeypatch covers both. We do not
    monkeypatch ``Path.home`` to avoid divergence between the two surfaces.
    """
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    builtin.mkdir()
    user.mkdir()
    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: builtin)
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: user)
    return {"builtin": builtin, "user": user, "tmp": tmp_path}


def _drop(source_dir: Path, fixture_name: str) -> None:
    shutil.copytree(_FIXTURES / fixture_name, source_dir / fixture_name)


# =============================================================================
# `pretorin recipe list`
# =============================================================================


def test_list_empty(fake_dirs: dict[str, Path]) -> None:
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "No recipes found" in result.stdout


def test_list_one_recipe(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "example-recipe" in result.stdout
    assert "official" in result.stdout


def test_list_filter_by_tier(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "another-recipe")
    result = runner.invoke(app, ["list", "--tier", "community"])
    assert result.exit_code == 0
    assert "another-recipe" in result.stdout
    assert "example-recipe" not in result.stdout


def test_list_filter_by_source(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "another-recipe")
    result = runner.invoke(app, ["list", "--source", "user"])
    assert result.exit_code == 0
    assert "another-recipe" in result.stdout
    assert "example-recipe" not in result.stdout


def test_list_marks_shadowed(fake_dirs: dict[str, Path]) -> None:
    """Same id at builtin AND user → user wins, displayed with shadow marker."""
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "example-recipe")
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    # User wins, marked with *
    assert "example-recipe*" in result.stdout
    # Hint about --sources
    assert "shadowed" in result.stdout


# =============================================================================
# `pretorin recipe show`
# =============================================================================


def test_show_unknown_id_exits_nonzero(fake_dirs: dict[str, Path]) -> None:
    result = runner.invoke(app, ["show", "no-such-recipe"])
    assert result.exit_code == 1
    assert "No recipe found" in result.stdout


def test_show_basic(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    result = runner.invoke(app, ["show", "example-recipe"])
    assert result.exit_code == 0
    assert "example-recipe" in result.stdout
    assert "Example Recipe" in result.stdout
    # Body is shown
    assert "Example Recipe Body" in result.stdout


def test_show_sources_lists_active_and_shadowed(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "example-recipe")
    result = runner.invoke(app, ["show", "example-recipe", "--sources"])
    assert result.exit_code == 0
    assert "ACTIVE" in result.stdout
    assert "user" in result.stdout
    assert "builtin" in result.stdout
    assert "shadowed" in result.stdout


# =============================================================================
# `pretorin recipe new`
# =============================================================================


def test_new_creates_user_folder_recipe(fake_dirs: dict[str, Path]) -> None:
    """Default location is user folder so contributors don't need a fork."""
    result = runner.invoke(app, ["new", "my-helper", "--author", "Test"])
    assert result.exit_code == 0
    user_dir = fake_dirs["user"] / "my-helper"
    assert user_dir.is_dir()
    assert (user_dir / "recipe.md").is_file()
    assert (user_dir / "scripts" / "example.py").is_file()
    assert (user_dir / "README.md").is_file()
    assert (user_dir / "tests" / "__init__.py").is_file()


def test_new_recipe_md_has_required_fields(fake_dirs: dict[str, Path]) -> None:
    runner.invoke(app, ["new", "my-helper", "--author", "Test"])
    user_dir = fake_dirs["user"] / "my-helper"
    content = (user_dir / "recipe.md").read_text()
    # Required frontmatter fields are present.
    assert "id: my-helper" in content
    assert "version: 0.1.0" in content
    assert "produces: evidence" in content
    assert 'author: "Test"' in content


def test_new_rejects_invalid_id(fake_dirs: dict[str, Path]) -> None:
    """Invalid kebab-case ids are rejected at scaffold time, not at validate time."""
    result = runner.invoke(app, ["new", "Invalid_Id", "--author", "Test"])
    assert result.exit_code == 1
    assert "Invalid recipe id" in result.stdout


def test_new_unknown_location_fails(fake_dirs: dict[str, Path]) -> None:
    result = runner.invoke(app, ["new", "my-helper", "--location", "bogus"])
    assert result.exit_code == 1
    assert "Unknown --location" in result.stdout


def test_new_existing_directory_fails(fake_dirs: dict[str, Path]) -> None:
    """Don't overwrite an existing recipe."""
    runner.invoke(app, ["new", "my-helper", "--author", "Test"])
    result = runner.invoke(app, ["new", "my-helper", "--author", "Test"])
    assert result.exit_code == 1
    assert "already exists" in result.stdout


# =============================================================================
# `pretorin recipe validate`
# =============================================================================


def test_validate_unknown_id(fake_dirs: dict[str, Path]) -> None:
    result = runner.invoke(app, ["validate", "no-such-recipe"])
    assert result.exit_code == 1
    assert "No recipe found" in result.stdout


def test_validate_passes_for_valid_recipe(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    # The fixture references scripts/example.py which doesn't exist → must fail.
    # Drop a real script file in too.
    script_dir = fake_dirs["builtin"] / "example-recipe" / "scripts"
    script_dir.mkdir(exist_ok=True)
    (script_dir / "example.py").write_text('"""Example."""\n\nasync def run(ctx, **params):\n    return {}\n')
    result = runner.invoke(app, ["validate", "example-recipe"])
    assert result.exit_code == 0
    assert "validates cleanly" in result.stdout


def test_validate_catches_short_description(fake_dirs: dict[str, Path]) -> None:
    """A recipe with a description below the 50-char floor fails validation."""
    bad = fake_dirs["user"] / "short-desc"
    bad.mkdir()
    (bad / "recipe.md").write_text(
        """---
id: short-desc
version: 0.1.0
name: "Short"
description: "Too short."
use_when: "Validation test fixture for description-quality enforcement."
produces: evidence
author: "Test"
---

body
"""
    )
    result = runner.invoke(app, ["validate", "short-desc"])
    assert result.exit_code == 1
    assert "description is too short" in result.stdout


def test_validate_catches_short_use_when(fake_dirs: dict[str, Path]) -> None:
    bad = fake_dirs["user"] / "short-use-when"
    bad.mkdir()
    (bad / "recipe.md").write_text(
        """---
id: short-use-when
version: 0.1.0
name: "Short use_when"
description: "This description is at least fifty characters so the description check passes."
use_when: "Too short."
produces: evidence
author: "Test"
---

body
"""
    )
    result = runner.invoke(app, ["validate", "short-use-when"])
    assert result.exit_code == 1
    assert "use_when is too short" in result.stdout


def test_validate_catches_missing_script_file(fake_dirs: dict[str, Path]) -> None:
    """Manifest declares a script but the file isn't there → caught."""
    _drop(fake_dirs["builtin"], "example-recipe")
    # The fixture's scripts/example.py was never copied (we only copied recipe.md).
    result = runner.invoke(app, ["validate", "example-recipe"])
    assert result.exit_code == 1
    assert "does not exist" in result.stdout


def test_validate_catches_script_without_run(fake_dirs: dict[str, Path]) -> None:
    """Script file exists but has no async def run → caught."""
    _drop(fake_dirs["builtin"], "example-recipe")
    script_dir = fake_dirs["builtin"] / "example-recipe" / "scripts"
    script_dir.mkdir(exist_ok=True)
    (script_dir / "example.py").write_text("# no run function defined\n")
    result = runner.invoke(app, ["validate", "example-recipe"])
    assert result.exit_code == 1
    assert "must define" in result.stdout


def test_validate_explicit_path(fake_dirs: dict[str, Path]) -> None:
    """``--path /abs/path`` validates a recipe outside the registry."""
    target = fake_dirs["tmp"] / "isolated-recipe"
    shutil.copytree(_FIXTURES / "another-recipe", target)
    result = runner.invoke(app, ["validate", "ignored-id", "--path", str(target)])
    assert result.exit_code == 0
    assert "validates cleanly" in result.stdout


# =============================================================================
# Round-trip: scaffold → validate
# =============================================================================


def test_scaffold_then_validate_passes(fake_dirs: dict[str, Path]) -> None:
    """The 10-minute promise: pretorin recipe new + edit + validate succeeds.

    The scaffolded recipe.md has TODO placeholders for description/use_when that
    are above the 50/30 char floors (the templates are deliberately verbose), so
    validation passes immediately on a fresh scaffold without edits.
    """
    runner.invoke(app, ["new", "scaffolded-recipe", "--author", "Test"])
    # The scaffolded recipe is in the user folder which the registry walks.
    result = runner.invoke(app, ["validate", "scaffolded-recipe"])
    assert result.exit_code == 0
    assert "validates cleanly" in result.stdout


# =============================================================================
# `pretorin recipe run`
# =============================================================================


def _patched_client_ctx() -> object:
    """Build the async-context-manager mock that wraps a fake PretorianClient.

    `pretorin recipe run` uses `async with PretorianClient() as client`, so
    patching `PretorianClient` itself isn't enough — we need the constructed
    object to behave like an async context manager.
    """
    client = AsyncMock()
    aenter = AsyncMock()
    aenter.__aenter__ = AsyncMock(return_value=client)
    aenter.__aexit__ = AsyncMock(return_value=None)
    return aenter


def test_run_unknown_id_exits_nonzero(fake_dirs: dict[str, Path]) -> None:
    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        result = runner.invoke(app, ["run", "no-such-recipe", "--no-context"])
    assert result.exit_code == 1
    assert "No recipe found" in result.stdout


def test_run_returns_script_result(fake_dirs: dict[str, Path]) -> None:
    """End-to-end: scope param, run, see the script's return value rendered."""
    _drop(fake_dirs["builtin"], "runnable-recipe")
    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        result = runner.invoke(
            app,
            ["run", "runnable-recipe", "--param", "message=hi"],
        )
    assert result.exit_code == 0, result.stdout
    assert "hello from runnable-recipe" in result.stdout
    # message=hi is parsed as the bare string (JSON parse fails, falls back).
    assert '"message": "hi"' in result.stdout
    # context_id is rendered when --no-context is omitted.
    assert "context_id" in result.stdout


def test_run_no_context_skips_context_id(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "runnable-recipe")
    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        result = runner.invoke(
            app,
            ["run", "runnable-recipe", "--no-context", "--param", "message=hi"],
        )
    assert result.exit_code == 0, result.stdout
    assert '"recipe_context_id": null' in result.stdout


def test_run_param_parses_json_values(fake_dirs: dict[str, Path]) -> None:
    """`--param limit=20` → int 20, `--param items=[1,2]` → list."""
    _drop(fake_dirs["builtin"], "runnable-recipe")
    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        result = runner.invoke(
            app,
            [
                "run",
                "runnable-recipe",
                "--no-context",
                "--param",
                "limit=20",
                "--param",
                "items=[1,2,3]",
                "--param",
                "label=hello",
            ],
        )
    assert result.exit_code == 0, result.stdout
    assert '"limit": 20' in result.stdout
    assert '"items": [' in result.stdout
    assert '"label": "hello"' in result.stdout


def test_run_param_without_equals_errors(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "runnable-recipe")
    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        result = runner.invoke(
            app,
            ["run", "runnable-recipe", "--no-context", "--param", "missing-equals"],
        )
    assert result.exit_code != 0


def test_run_ambiguous_script_when_multiple(fake_dirs: dict[str, Path]) -> None:
    """A recipe with >1 script requires --script."""
    # Build an ad-hoc fixture with two scripts.
    target = fake_dirs["builtin"] / "two-script-recipe"
    target.mkdir()
    (target / "scripts").mkdir()
    (target / "recipe.md").write_text(
        """---
id: two-script-recipe
version: 0.1.0
name: "Two Script Recipe"
description: "A test fixture with two scripts so the run command's ambiguity check triggers."
use_when: "Only used by the cli run-command tests for the multi-script branch."
produces: evidence
author: "Test"
license: Apache-2.0
scripts:
  alpha:
    path: scripts/alpha.py
    description: "first"
  beta:
    path: scripts/beta.py
    description: "second"
---

# Two Script Recipe Body

Test fixture only.
"""
    )
    for name in ("alpha", "beta"):
        (target / "scripts" / f"{name}.py").write_text(
            "async def run(ctx, **params):\n    return {'name': '" + name + "'}\n"
        )

    with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
        ambiguous = runner.invoke(app, ["run", "two-script-recipe", "--no-context"])
        chose = runner.invoke(
            app,
            ["run", "two-script-recipe", "--no-context", "--script", "beta"],
        )

    assert ambiguous.exit_code == 1
    assert "specify one with --script" in ambiguous.stdout

    assert chose.exit_code == 0, chose.stdout
    assert '"name": "beta"' in chose.stdout


def test_run_json_mode(fake_dirs: dict[str, Path]) -> None:
    """JSON mode emits a structured payload the test can `json.loads`."""
    from pretorin.cli.output import set_json_mode

    _drop(fake_dirs["builtin"], "runnable-recipe")
    set_json_mode(True)
    try:
        with patch("pretorin.client.api.PretorianClient", return_value=_patched_client_ctx()):
            result = runner.invoke(
                app,
                ["run", "runnable-recipe", "--no-context"],
            )
    finally:
        set_json_mode(False)
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["recipe_id"] == "runnable-recipe"
    assert payload["script"] == "echo"
    assert payload["context_id"] is None
    assert payload["result"]["greeting"] == "hello from runnable-recipe"
