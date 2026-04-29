"""Tests for the recipe loader.

Covers:

- Frontmatter parsing (delimiters, YAML, body extraction).
- Per-recipe validation isolation: malformed recipes don't break the registry.
- Tier override from source path (manifest-declared tier is overridden).
- mtime-based parse cache invalidation.
- Override precedence (explicit > project > user > built-in).
- Empty-source-root tolerance (missing ~/.pretorin/recipes/ → silent skip).
- ``load_explicit_path`` raises loudly on bad input (unlike registry walk).
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from pretorin.recipes import loader as loader_module
from pretorin.recipes.errors import RecipeManifestError
from pretorin.recipes.loader import (
    clear_cache,
    load_all,
    load_explicit_path,
    precedence_score,
)

_FIXTURES = Path(__file__).parent / "fixtures"
_VALID_FIXTURES = _FIXTURES / "valid"
_BROKEN_FIXTURES = _FIXTURES / "broken"


# =============================================================================
# Test scaffold — point loader's path-resolution helpers at fixture trees.
# =============================================================================


@pytest.fixture(autouse=True)
def _isolate_cache() -> None:
    """Each test starts with a clean parse cache."""
    clear_cache()


@pytest.fixture
def fake_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Build a fresh tmp directory tree mirroring the four loader paths.

    Returns a mapping of source name → path so individual tests can populate
    each tree with the fixture recipes they need.
    """
    builtin = tmp_path / "builtin"
    user = tmp_path / "user"
    project = tmp_path / "project_root" / ".pretorin" / "recipes"
    project.parent.mkdir(parents=True)
    project.mkdir(parents=True)
    builtin.mkdir()
    user.mkdir()

    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: builtin)
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: user)
    # _project_recipes_root walks up from `start`; pass the project_root.
    return {
        "builtin": builtin,
        "user": user,
        "project": project,
        "project_start": tmp_path / "project_root",
    }


def _drop_fixture(source_dir: Path, fixture_name: str, fixture_root: Path = _VALID_FIXTURES) -> None:
    """Copy a fixture recipe directory under a source root."""
    shutil.copytree(fixture_root / fixture_name, source_dir / fixture_name)


# =============================================================================
# Frontmatter parsing
# =============================================================================


def test_load_valid_recipe(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    by_id = load_all()
    assert "example-recipe" in by_id
    [loaded] = by_id["example-recipe"]
    assert loaded.manifest.name == "Example Recipe"
    assert loaded.manifest.tier == "official"  # builtin path → official
    assert loaded.source == "builtin"
    assert "Example Recipe Body" in loaded.body
    # Body has frontmatter stripped.
    assert "id: example-recipe" not in loaded.body


def test_load_recipe_without_scripts(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["user"], "another-recipe")
    by_id = load_all()
    [loaded] = by_id["another-recipe"]
    assert loaded.manifest.scripts == {}
    assert loaded.manifest.params == {}
    assert loaded.manifest.tier == "community"  # user path → community


def test_malformed_yaml_skipped_per_validation_isolation(fake_dirs: dict[str, Path]) -> None:
    """One bad recipe doesn't break the registry."""
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    _drop_fixture(fake_dirs["builtin"], "malformed-yaml", fixture_root=_BROKEN_FIXTURES)
    by_id = load_all()
    # The valid recipe is still there.
    assert "example-recipe" in by_id
    # The broken one is NOT — silently dropped per per-recipe validation isolation.
    assert "malformed-yaml" not in by_id


def test_missing_required_field_skipped(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    _drop_fixture(fake_dirs["builtin"], "missing-required", fixture_root=_BROKEN_FIXTURES)
    by_id = load_all()
    assert "example-recipe" in by_id
    assert "missing-required" not in by_id


def test_no_frontmatter_skipped(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "no-frontmatter", fixture_root=_BROKEN_FIXTURES)
    by_id = load_all()
    assert by_id == {}


def test_unterminated_frontmatter_skipped(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "unterminated", fixture_root=_BROKEN_FIXTURES)
    by_id = load_all()
    assert by_id == {}


# =============================================================================
# Tier override from source path
# =============================================================================


def test_tier_overridden_from_source_path(fake_dirs: dict[str, Path], tmp_path: Path) -> None:
    """An author-declared tier='official' in user folder is overridden to community."""
    user_dir = fake_dirs["user"] / "claims-official"
    user_dir.mkdir()
    (user_dir / "recipe.md").write_text(
        """---
id: claims-official
version: 0.1.0
name: "Claims Official"
description: "Author claims tier=official, but the recipe is in user folder."
use_when: "Tests tier override behavior."
produces: evidence
author: "Test"
tier: official
---

body
"""
    )
    by_id = load_all()
    [loaded] = by_id["claims-official"]
    assert loaded.manifest.tier == "community"  # loader overrides


# =============================================================================
# Override precedence and shadowing
# =============================================================================


def test_same_id_in_multiple_sources_returns_both(fake_dirs: dict[str, Path]) -> None:
    """When the same id appears in builtin and user, both are returned for shadow detection."""
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    _drop_fixture(fake_dirs["user"], "example-recipe")
    by_id = load_all()
    sources = by_id["example-recipe"]
    assert len(sources) == 2
    source_kinds = {r.source for r in sources}
    assert source_kinds == {"builtin", "user"}


def test_precedence_score_ordering() -> None:
    assert precedence_score("explicit") > precedence_score("project")
    assert precedence_score("project") > precedence_score("user")
    assert precedence_score("user") > precedence_score("builtin")


# =============================================================================
# Cache (mtime invalidation)
# =============================================================================


def test_cache_invalidates_on_mtime_change(fake_dirs: dict[str, Path]) -> None:
    """Editing recipe.md re-parses on next load, not stale-reads."""
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    by_id_first = load_all()
    [first] = by_id_first["example-recipe"]
    assert first.manifest.name == "Example Recipe"

    # Wait briefly to ensure mtime changes (fs resolution can be 1s on some systems).
    time.sleep(0.01)
    recipe_md = fake_dirs["builtin"] / "example-recipe" / "recipe.md"
    content = recipe_md.read_text().replace('"Example Recipe"', '"Edited Name"')
    recipe_md.write_text(content)
    # Touch mtime to be safe across filesystem resolutions.
    new_mtime = recipe_md.stat().st_mtime_ns + 10_000_000  # +10ms
    import os

    os.utime(recipe_md, ns=(new_mtime, new_mtime))

    by_id_second = load_all()
    [second] = by_id_second["example-recipe"]
    assert second.manifest.name == "Edited Name"


def test_clear_cache_forces_reread(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    load_all()  # populate cache
    clear_cache()
    # Should reload cleanly with no errors.
    by_id = load_all()
    assert "example-recipe" in by_id


# =============================================================================
# Empty-source-root tolerance
# =============================================================================


def test_empty_source_roots_silent(fake_dirs: dict[str, Path]) -> None:
    """No recipes anywhere → empty registry, no errors."""
    by_id = load_all()
    assert by_id == {}


def test_missing_user_root_is_tolerated(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A user with no ~/.pretorin/recipes/ doesn't see an error."""
    monkeypatch.setattr(loader_module, "_builtin_recipes_root", lambda: tmp_path / "builtin")
    monkeypatch.setattr(loader_module, "_user_recipes_root", lambda: tmp_path / "no-such-dir")
    by_id = load_all()
    assert by_id == {}


# =============================================================================
# Explicit-path loading
# =============================================================================


def test_load_explicit_path_succeeds(tmp_path: Path) -> None:
    target = tmp_path / "example-recipe"
    shutil.copytree(_VALID_FIXTURES / "example-recipe", target)
    loaded = load_explicit_path(target)
    assert loaded.source == "explicit"
    assert loaded.manifest.tier == "community"  # explicit defaults to community
    assert loaded.manifest.id == "example-recipe"


def test_load_explicit_path_missing_dir(tmp_path: Path) -> None:
    with pytest.raises(RecipeManifestError, match="recipe directory not found"):
        load_explicit_path(tmp_path / "no-such-dir")


def test_load_explicit_path_missing_recipe_md(tmp_path: Path) -> None:
    empty = tmp_path / "empty-dir"
    empty.mkdir()
    with pytest.raises(RecipeManifestError, match="recipe.md not found"):
        load_explicit_path(empty)


def test_load_explicit_path_raises_loudly_on_invalid(tmp_path: Path) -> None:
    """Unlike registry walk, explicit-path callers want errors."""
    target = tmp_path / "missing-required"
    shutil.copytree(_BROKEN_FIXTURES / "missing-required", target)
    with pytest.raises(RecipeManifestError):
        load_explicit_path(target)


# =============================================================================
# Multiple sources mixed
# =============================================================================


def test_load_all_returns_recipes_from_all_sources(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    _drop_fixture(fake_dirs["user"], "another-recipe")
    by_id = load_all()
    assert set(by_id.keys()) == {"example-recipe", "another-recipe"}
    [example] = by_id["example-recipe"]
    [another] = by_id["another-recipe"]
    assert example.source == "builtin"
    assert another.source == "user"


def test_loaded_recipe_path_is_resolved_absolute(fake_dirs: dict[str, Path]) -> None:
    _drop_fixture(fake_dirs["builtin"], "example-recipe")
    by_id = load_all()
    [loaded] = by_id["example-recipe"]
    assert loaded.path.is_absolute()
    assert loaded.path.name == "recipe.md"
