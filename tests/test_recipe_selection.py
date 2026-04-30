"""Tests for the per-item recipe selection — WS5d audit-trail wiring.

The selector surveys recipes' attests entries for a (control, framework)
match. The audit point is that *every* drafting call records which
recipe was picked (or that nothing matched and the workflow fell back
to freelance), so a reviewer can trace which recipes drove which
artifacts across a campaign.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from pretorin.recipes import loader as loader_module
from pretorin.recipes.loader import clear_cache
from pretorin.recipes.registry import RecipeRegistry
from pretorin.recipes.selection import (
    RecipeSelection,
    select_recipe_for_drafting,
    to_audit_dict,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hide user/project recipes so each test uses only what it loads."""
    clear_cache()
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: tmp_path / "u")
    monkeypatch.setattr(loader_module, "_project_recipes_root", lambda start=None: None)
    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: tmp_path / "b")
    (tmp_path / "u").mkdir(exist_ok=True)
    (tmp_path / "b").mkdir(exist_ok=True)


def _drop_recipe(
    parent: Path,
    *,
    recipe_id: str,
    attests: list[dict[str, str]] | None = None,
    version: str = "0.1.0",
) -> None:
    """Write a minimal valid recipe.md under ``parent``."""
    recipe_dir = parent / recipe_id
    (recipe_dir / "scripts").mkdir(parents=True, exist_ok=True)
    attests_yaml = ""
    if attests:
        attests_yaml = "attests:\n"
        for entry in attests:
            attests_yaml += f"  - {{ control: {entry['control']}, framework: {entry['framework']} }}\n"
    (recipe_dir / "recipe.md").write_text(
        f"""---
id: {recipe_id}
version: {version}
name: "{recipe_id.replace("-", " ").title()}"
description: "A test fixture recipe used by the WS5d selection tests; it does not produce real evidence."
use_when: "Only used by tests of the recipe-selection function."
produces: evidence
author: "Test"
license: Apache-2.0
{attests_yaml}scripts:
  example_tool:
    path: scripts/example.py
    description: "Test tool"
---

# {recipe_id}

Test fixture body.
"""
    )
    (recipe_dir / "scripts" / "example.py").write_text("async def run(ctx, **params):\n    return {'ok': True}\n")


# =============================================================================
# Selection: no match → fallback
# =============================================================================


def test_no_recipes_loaded_returns_fallback() -> None:
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    assert selection.selected_recipe is None
    assert selection.fallback_to_freelance is True
    assert "No recipe in the registry attests" in selection.reason


def test_loaded_recipes_with_no_matching_attests_returns_fallback(tmp_path: Path) -> None:
    _drop_recipe(
        tmp_path / "b",
        recipe_id="other-recipe",
        attests=[{"control": "CM-6", "framework": "nist-800-53-r5"}],
    )
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    assert selection.selected_recipe is None
    assert selection.fallback_to_freelance is True


# =============================================================================
# Selection: hint match
# =============================================================================


def test_attests_exact_match_picks_recipe(tmp_path: Path) -> None:
    _drop_recipe(
        tmp_path / "b",
        recipe_id="ac2-helper",
        attests=[{"control": "AC-2", "framework": "nist-800-53-r5"}],
    )
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    assert selection.selected_recipe == "ac2-helper"
    assert selection.fallback_to_freelance is False
    assert selection.confidence == "high"
    assert "hint" in selection.reason.lower()


def test_attests_match_is_case_insensitive_on_control(tmp_path: Path) -> None:
    """Manifests use 'AC-2', user passes 'ac-2'. Both should match."""
    _drop_recipe(
        tmp_path / "b",
        recipe_id="ac2-helper",
        attests=[{"control": "AC-2", "framework": "nist-800-53-r5"}],
    )
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    assert selection.selected_recipe == "ac2-helper"


def test_alternatives_listed_when_multiple_match(tmp_path: Path) -> None:
    _drop_recipe(
        tmp_path / "b",
        recipe_id="primary-helper",
        attests=[{"control": "AC-2", "framework": "nist-800-53-r5"}],
    )
    _drop_recipe(
        tmp_path / "b",
        recipe_id="alt-helper",
        attests=[{"control": "AC-2", "framework": "nist-800-53-r5"}],
    )
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    # Alphabetic order means alt-helper wins; primary-helper is alternate.
    assert selection.selected_recipe == "alt-helper"
    assert "primary-helper" in selection.alternatives_considered


def test_framework_must_match_when_specified(tmp_path: Path) -> None:
    _drop_recipe(
        tmp_path / "b",
        recipe_id="fedramp-helper",
        attests=[{"control": "AC-2", "framework": "fedramp-moderate"}],
    )
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    # fedramp-helper matches the control but not the framework — no pick.
    assert selection.selected_recipe is None
    assert selection.fallback_to_freelance is True


# =============================================================================
# Selection: caller-supplied registry
# =============================================================================


def test_caller_can_supply_registry_to_avoid_disk_walk() -> None:
    """A caller (e.g., a tight loop) can pass a pre-built registry."""
    fake_registry = MagicMock(spec=RecipeRegistry)
    fake_registry.entries.return_value = []
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
        registry=fake_registry,
    )
    assert selection.fallback_to_freelance is True
    fake_registry.entries.assert_called_once()


# =============================================================================
# Audit serialization
# =============================================================================


def test_to_audit_dict_round_trips_through_pydantic() -> None:
    selection = RecipeSelection(
        selected_recipe="ac2-helper",
        selected_recipe_version="0.1.0",
        confidence="high",
        reason="match",
        alternatives_considered=["other"],
        required_inputs_present=True,
        fallback_to_freelance=False,
    )
    out = to_audit_dict(selection)
    assert out["selected_recipe"] == "ac2-helper"
    assert out["confidence"] == "high"
    assert out["fallback_to_freelance"] is False
    # Reconstruct to confirm the dict is round-trippable.
    reconstructed = RecipeSelection.model_validate(out)
    assert reconstructed == selection


def test_fallback_record_serializes_cleanly() -> None:
    selection = select_recipe_for_drafting(
        framework_id="nist-800-53-r5",
        control_id="ac-2",
    )
    out = to_audit_dict(selection)
    assert out["selected_recipe"] is None
    assert out["fallback_to_freelance"] is True
    assert isinstance(out["reason"], str) and out["reason"]
