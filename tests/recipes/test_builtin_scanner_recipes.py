"""Smoke tests for the five built-in scanner recipes shipped with pretorin-cli.

These recipes live under ``src/pretorin/recipes/_recipes/`` and replace the
legacy ``pretorin scan`` CLI command. The point of this test file is to
verify they all load cleanly through the registry and declare the expected
shape (id, scripts.run_scan, params, scanner-binding requirements) so a
calling agent can dispatch them.

The recipe scripts themselves are exercised end-to-end elsewhere (the
underlying scanners have their own tests); here we only confirm the
manifests parse and route through the registry.
"""

from __future__ import annotations

import pytest

from pretorin.recipes import loader as loader_module
from pretorin.recipes.loader import clear_cache
from pretorin.recipes.registry import RecipeRegistry

_SCANNER_RECIPE_IDS = [
    "inspec-baseline",
    "openscap-baseline",
    "cloud-aws-baseline",
    "cloud-azure-baseline",
    "manual-attestation",
]


@pytest.fixture(autouse=True)
def _isolate_cache(tmp_path, monkeypatch):
    """Hide user/project recipes so the registry only sees built-ins."""
    clear_cache()
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: tmp_path / "no-user")
    monkeypatch.setattr(loader_module, "_project_recipes_root", lambda start=None: None)


def test_all_five_scanner_recipes_load_from_builtins() -> None:
    registry = RecipeRegistry()
    ids = {entry.active.manifest.id for entry in registry.entries()}
    for recipe_id in _SCANNER_RECIPE_IDS:
        assert recipe_id in ids, f"missing built-in scanner recipe: {recipe_id}"


@pytest.mark.parametrize("recipe_id", _SCANNER_RECIPE_IDS)
def test_scanner_recipe_has_run_scan_script(recipe_id: str) -> None:
    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    assert entry is not None
    manifest = entry.active.manifest
    assert "run_scan" in manifest.scripts, f"{recipe_id} must expose a run_scan script for the calling agent"
    assert manifest.scripts["run_scan"].path == "scripts/run_scan.py"


@pytest.mark.parametrize("recipe_id", _SCANNER_RECIPE_IDS)
def test_scanner_recipe_requires_stig_id(recipe_id: str) -> None:
    """All five scanner recipes are scoped to one STIG per run."""
    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    assert entry is not None
    params = entry.active.manifest.params
    assert "stig_id" in params
    assert params["stig_id"].required is True


@pytest.mark.parametrize("recipe_id", _SCANNER_RECIPE_IDS)
def test_scanner_recipe_tier_is_official(recipe_id: str) -> None:
    """Built-in path forces tier=official regardless of what the manifest says."""
    registry = RecipeRegistry()
    entry = registry.get(recipe_id)
    assert entry is not None
    assert entry.active.manifest.tier == "official"
    assert entry.active.source == "builtin"


def test_external_tool_recipes_declare_cli_requirements() -> None:
    """The four external-tool scanners declare their CLI binary; manual does not."""
    registry = RecipeRegistry()
    expected = {
        "inspec-baseline": "inspec",
        "openscap-baseline": "oscap",
        "cloud-aws-baseline": "aws",
        "cloud-azure-baseline": "az",
    }
    for recipe_id, cli_name in expected.items():
        entry = registry.get(recipe_id)
        assert entry is not None, recipe_id
        cli = entry.active.manifest.requires.cli
        assert cli, f"{recipe_id} should declare a required CLI"
        assert cli[0]["name"] == cli_name

    manual = registry.get("manual-attestation")
    assert manual is not None
    assert not manual.active.manifest.requires.cli
