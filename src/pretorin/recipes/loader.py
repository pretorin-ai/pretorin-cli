"""Recipe loader — walks the four v1 paths and parses recipe.md frontmatter.

Per the design's WS2 §2 ("Loader paths in v1") and §1 (loader behavior):

- Four loader paths in v1: built-in, user folder, project folder, explicit.
- Override precedence (highest wins): explicit > project > user > built-in.
- Lazy walk: registry indexes recipe paths from all four paths at first
  access, parses on demand.
- Per-recipe parse cache: each recipe.md is parsed once per process and
  cached by ``(path, mtime)`` — re-parses on disk change.
- Per-recipe validation isolation: a malformed recipe raises
  ``RecipeManifestError`` for *that recipe* at load attempt, not at registry
  init. One bad recipe doesn't break the registry.

Tier signaling: the loader sets ``RecipeManifest.tier`` from the source path,
overriding any author-declared value. Built-in path → ``official``; user/
project folders → ``community`` by default; ``partner`` is reserved for
installed-package loading (deferred to v1.5).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from pretorin.recipes.errors import RecipeManifestError
from pretorin.recipes.manifest import RecipeManifest

logger = logging.getLogger(__name__)


LoaderSource = Literal["builtin", "user", "project", "explicit"]
"""Where a recipe was loaded from. Drives tier signaling and override precedence."""


# Override precedence — higher index wins when the same id appears at multiple
# sources. ``explicit`` paths (passed directly to ``pretorin recipe run /abs/path``)
# beat any registry-walked source.
_PRECEDENCE: dict[LoaderSource, int] = {
    "builtin": 0,
    "user": 1,
    "project": 2,
    "explicit": 3,
}


# Tier mapping per loader source. Author-declared tier in manifest is overridden.
_SOURCE_TO_TIER: dict[LoaderSource, str] = {
    "builtin": "official",
    "user": "community",
    "project": "community",
    "explicit": "community",
}


@dataclass(frozen=True)
class LoadedRecipe:
    """A successfully-parsed recipe, with provenance.

    The ``manifest`` has its ``tier`` field set by the loader based on
    ``source`` — author-declared tier (if any) was overridden during parsing.
    """

    manifest: RecipeManifest
    body: str
    """Recipe.md body with frontmatter stripped — the playbook text."""

    path: Path
    """Absolute path to the recipe.md file."""

    source: LoaderSource


def _builtin_recipes_root() -> Path:
    """Built-in recipes ship inside the pretorin package at src/pretorin/recipes/_recipes/.

    Located via this module's ``__file__`` so it works for both editable installs
    and wheel installs.
    """
    return Path(__file__).resolve().parent / "_recipes"


def _user_recipes_root() -> Path:
    """User-folder recipes at ``~/.pretorin/recipes/``."""
    return Path.home() / ".pretorin" / "recipes"


def _project_recipes_root(start: Path | None = None) -> Path | None:
    """Project-folder recipes at ``<git-root>/.pretorin/recipes/``.

    Walks up from ``start`` (defaults to CWD) looking for a directory that
    contains ``.pretorin/recipes/``. Returns ``None`` if no such directory is
    found within the walk-up. Stops at filesystem root.
    """
    cur = (start or Path.cwd()).resolve()
    while True:
        candidate = cur / ".pretorin" / "recipes"
        if candidate.is_dir():
            return candidate
        if cur.parent == cur:  # filesystem root
            return None
        cur = cur.parent


def _enumerate_paths(source: LoaderSource, *, start: Path | None = None) -> list[Path]:
    """Return absolute paths to every recipe.md from a given source.

    Returns an empty list if the source's root doesn't exist; the loader
    ignores missing roots silently (a fresh user with no ``~/.pretorin/recipes/``
    just gets the built-in recipes).
    """
    if source == "builtin":
        root = _builtin_recipes_root()
    elif source == "user":
        root = _user_recipes_root()
    elif source == "project":
        project_root = _project_recipes_root(start=start)
        if project_root is None:
            return []
        root = project_root
    else:  # "explicit" handled by load_explicit_path; not enumerated.
        return []

    if not root.is_dir():
        return []

    return sorted(root.glob("*/recipe.md"))


def _parse_frontmatter(content: str) -> tuple[dict[str, object], str]:
    """Split ``---\\n...\\n---\\n`` YAML frontmatter from the body.

    Returns ``({}, content)`` if no frontmatter delimiter is present at the top
    of the file. Raises ``RecipeManifestError`` if the frontmatter is malformed
    YAML or starts but doesn't terminate.
    """
    if not content.startswith("---"):
        raise RecipeManifestError("recipe.md must start with YAML frontmatter delimited by '---' lines")

    parts = content.split("---", 2)
    if len(parts) < 3:
        raise RecipeManifestError("recipe.md frontmatter is unterminated (expected closing '---' line)")

    fm_text = parts[1].strip()
    body = parts[2].lstrip("\n")

    try:
        fm_loaded = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        raise RecipeManifestError(f"recipe.md frontmatter is not valid YAML: {exc}") from exc

    if fm_loaded is None:
        return {}, body
    if not isinstance(fm_loaded, dict):
        raise RecipeManifestError("recipe.md frontmatter must be a YAML mapping at the top level")
    return fm_loaded, body


def _parse_recipe_file(path: Path, source: LoaderSource) -> LoadedRecipe:
    """Parse one recipe.md and validate against the manifest schema.

    Sets ``manifest.tier`` from the source path, overriding author-declared
    tier per design WS2 §1 ("Manifest-declared tier is at most a hint; loader
    path is authoritative.").
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RecipeManifestError(f"recipe.md at {path} could not be read: {exc}") from exc

    frontmatter, body = _parse_frontmatter(content)

    # Loader-set tier overrides any author-declared value.
    frontmatter["tier"] = _SOURCE_TO_TIER[source]

    try:
        manifest = RecipeManifest.model_validate(frontmatter)
    except Exception as exc:
        # Pydantic ValidationError carries enough info; wrap it for the consistent type.
        raise RecipeManifestError(f"recipe.md at {path} failed manifest validation: {exc}") from exc

    return LoadedRecipe(manifest=manifest, body=body, path=path.resolve(), source=source)


# Process-lifetime cache keyed by (path, mtime_ns). Re-parses on disk change.
# Module-level so it's shared across registry instances; cheap to keep correct.
_PARSE_CACHE: dict[tuple[Path, int], LoadedRecipe] = {}


def _load_with_cache(path: Path, source: LoaderSource) -> LoadedRecipe:
    """Parse a recipe.md, returning a cached result when possible.

    Cache key includes ``mtime_ns`` so an editor changing the file invalidates
    the entry on next read. Cheap (one stat call) and avoids re-parsing on
    every list/show invocation.
    """
    try:
        mtime = path.stat().st_mtime_ns
    except OSError as exc:
        raise RecipeManifestError(f"recipe.md at {path} could not be stat'd: {exc}") from exc

    key = (path.resolve(), mtime)
    cached = _PARSE_CACHE.get(key)
    if cached is not None:
        return cached

    loaded = _parse_recipe_file(path, source)
    _PARSE_CACHE[key] = loaded
    return loaded


def load_all(*, project_start: Path | None = None) -> dict[str, list[LoadedRecipe]]:
    """Walk all four loader paths and return every successfully-loaded recipe.

    Returns a mapping ``recipe_id → [LoadedRecipe, ...]`` so callers can detect
    shadowing (multiple paths produce the same id). Per the per-recipe validation
    isolation rule, malformed recipes are silently dropped (with a debug log)
    and do not break the registry.

    Order within each id's list reflects discovery order, not precedence —
    the registry layer applies precedence when picking the active recipe.
    """
    by_id: dict[str, list[LoadedRecipe]] = {}
    sources: tuple[LoaderSource, ...] = ("builtin", "user", "project")
    for source in sources:
        for path in _enumerate_paths(source, start=project_start):
            try:
                loaded = _load_with_cache(path, source)
            except RecipeManifestError as exc:
                # Per per-recipe validation isolation: log and skip; do not raise.
                logger.warning("Recipe at %s failed to load: %s", path, exc)
                continue
            by_id.setdefault(loaded.manifest.id, []).append(loaded)
    return by_id


def load_explicit_path(recipe_dir: Path) -> LoadedRecipe:
    """Load a recipe from an explicit absolute path.

    Used by ``pretorin recipe run /abs/path/to/recipe-dir`` while authoring.
    Highest precedence; never cached against the registry. Raises
    ``RecipeManifestError`` if the directory or recipe.md doesn't exist or
    fails validation — explicit-path callers want errors loudly.
    """
    recipe_dir = recipe_dir.resolve()
    if not recipe_dir.is_dir():
        raise RecipeManifestError(f"recipe directory not found: {recipe_dir}")
    recipe_md = recipe_dir / "recipe.md"
    if not recipe_md.is_file():
        raise RecipeManifestError(f"recipe.md not found in {recipe_dir}")
    return _load_with_cache(recipe_md, "explicit")


def precedence_score(source: LoaderSource) -> int:
    """Return a comparable integer for override precedence.

    Higher score wins. Used by the registry layer to pick the active recipe
    when multiple sources expose the same id (shadowing case).
    """
    return _PRECEDENCE[source]


def clear_cache() -> None:
    """Drop the process-lifetime parse cache.

    Used by ``pretorin recipe reload`` and by tests that author/edit recipes
    and need a clean read. Real callers rarely need to invoke this — mtime
    invalidation handles edit detection automatically.
    """
    _PARSE_CACHE.clear()
