"""Tests for the recipe registry — read-side facade over the loader."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from pretorin.recipes import loader as loader_module
from pretorin.recipes.loader import clear_cache
from pretorin.recipes.registry import RecipeRegistry

_FIXTURES = Path(__file__).parent / "fixtures" / "valid"


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    clear_cache()


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    builtin.mkdir()
    user.mkdir()
    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: builtin)
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: user)
    return {"builtin": builtin, "user": user}


def _drop(source_dir: Path, fixture_name: str) -> None:
    shutil.copytree(_FIXTURES / fixture_name, source_dir / fixture_name)


# =============================================================================
# entries() and get()
# =============================================================================


def test_registry_empty_when_no_recipes(fake_dirs: dict[str, Path]) -> None:
    registry = RecipeRegistry()
    assert registry.entries() == []
    assert registry.get("any-id") is None


def test_registry_entries_sorted_by_id(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["builtin"], "another-recipe")
    registry = RecipeRegistry()
    ids = [e.active.manifest.id for e in registry.entries()]
    assert ids == ["another-recipe", "example-recipe"]


def test_registry_get_returns_entry(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    registry = RecipeRegistry()
    entry = registry.get("example-recipe")
    assert entry is not None
    assert entry.active.manifest.id == "example-recipe"
    assert entry.shadowed == ()


# =============================================================================
# Override precedence
# =============================================================================


def test_user_shadows_builtin(fake_dirs: dict[str, Path]) -> None:
    """When same id appears in builtin and user, user wins."""
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "example-recipe")
    registry = RecipeRegistry()
    entry = registry.get("example-recipe")
    assert entry is not None
    assert entry.active.source == "user"
    assert len(entry.shadowed) == 1
    assert entry.shadowed[0].source == "builtin"


def test_is_shadowed_flag(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "example-recipe")
    registry = RecipeRegistry()
    assert registry.is_shadowed("example-recipe") is True


def test_not_shadowed_when_only_one_source(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    registry = RecipeRegistry()
    assert registry.is_shadowed("example-recipe") is False


def test_active_tier_reflects_winning_source(fake_dirs: dict[str, Path]) -> None:
    """Shadowing affects displayed tier — user copy is community even when shadowing official."""
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "example-recipe")
    registry = RecipeRegistry()
    entry = registry.get("example-recipe")
    assert entry is not None
    assert entry.active.manifest.tier == "community"  # user wins
    assert entry.shadowed[0].manifest.tier == "official"  # builtin shadow


# =============================================================================
# Filtering
# =============================================================================


def test_filter_by_tier_official(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "another-recipe")
    registry = RecipeRegistry()
    official = registry.filter_by_tier("official")
    assert {e.active.manifest.id for e in official} == {"example-recipe"}


def test_filter_by_tier_community(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "another-recipe")
    registry = RecipeRegistry()
    community = registry.filter_by_tier("community")
    assert {e.active.manifest.id for e in community} == {"another-recipe"}


def test_filter_by_source(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["builtin"], "example-recipe")
    _drop(fake_dirs["user"], "another-recipe")
    registry = RecipeRegistry()
    builtin_only = registry.filter_by_source("builtin")
    assert {e.active.manifest.id for e in builtin_only} == {"example-recipe"}


def test_filter_returns_empty_when_no_matches(fake_dirs: dict[str, Path]) -> None:
    _drop(fake_dirs["user"], "another-recipe")
    registry = RecipeRegistry()
    assert registry.filter_by_tier("partner") == []


# =============================================================================
# Construct fresh per call
# =============================================================================


def test_fresh_registries_share_loader_cache(fake_dirs: dict[str, Path]) -> None:
    """Two registry instances see the same recipes (cache is module-level)."""
    _drop(fake_dirs["builtin"], "example-recipe")
    r1 = RecipeRegistry()
    r2 = RecipeRegistry()
    assert {e.active.manifest.id for e in r1.entries()} == {e.active.manifest.id for e in r2.entries()}
