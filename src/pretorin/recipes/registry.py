"""Recipe registry — the read-side surface over the loader.

Per the design's WS2 §4 ("Recipe registry exposer"): this is **not a runner**.
There is no recipe-level LLM in pretorin. The registry's job is to expose
loaded recipes (via the four loader paths) to consumers (CLI, MCP, the
recipe-execution-context layer in WS2 Phase B).

The registry handles:

- Override precedence (explicit > project > user > built-in) when an id
  appears at multiple sources.
- Shadowing detection — every shadowed copy is enumerable so ``pretorin recipe
  show <id> --sources`` and the warning markers in ``pretorin recipe list``
  can surface the trust risk.
- Lazy loading — recipes parse on demand via the loader's mtime cache.

The registry instance is stateless; multiple instantiations share the loader's
module-level parse cache. Callers can construct a fresh instance whenever
they need a current view.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pretorin.recipes.loader import (
    LoadedRecipe,
    LoaderSource,
    load_all,
    load_explicit_path,
    precedence_score,
)


@dataclass(frozen=True)
class RegistryEntry:
    """One recipe id's full registry view: active version + any shadowed copies.

    ``active`` is the recipe that wins the precedence battle and is the one
    used for ``recipe show``, ``recipe run``, MCP tool registration, etc.
    ``shadowed`` lists every other source for the same id, in
    discovery order (loader walk order). Callers that want the trust signal
    use ``shadowed`` to flag the situation in user-facing output.
    """

    active: LoadedRecipe
    shadowed: tuple[LoadedRecipe, ...]


class RecipeRegistry:
    """Read-side facade over the loader. Instantiate per-call; cheap.

    Typical usage::

        registry = RecipeRegistry()
        for entry in registry.entries():
            print(entry.active.manifest.id, entry.active.manifest.tier)

        entry = registry.get("code-evidence-capture")
    """

    def __init__(self, *, project_start: Path | None = None) -> None:
        self._project_start = project_start
        self._by_id: dict[str, list[LoadedRecipe]] | None = None

    def _ensure_loaded(self) -> dict[str, list[LoadedRecipe]]:
        if self._by_id is None:
            self._by_id = load_all(project_start=self._project_start)
        return self._by_id

    def entries(self) -> list[RegistryEntry]:
        """Return one ``RegistryEntry`` per unique recipe id, sorted by id."""
        by_id = self._ensure_loaded()
        result: list[RegistryEntry] = []
        for recipe_id in sorted(by_id):
            sources = by_id[recipe_id]
            ranked = sorted(sources, key=lambda r: precedence_score(r.source), reverse=True)
            active = ranked[0]
            shadowed = tuple(ranked[1:])
            result.append(RegistryEntry(active=active, shadowed=shadowed))
        return result

    def get(self, recipe_id: str) -> RegistryEntry | None:
        """Return one entry by id, or ``None`` if no source provides it."""
        by_id = self._ensure_loaded()
        sources = by_id.get(recipe_id)
        if not sources:
            return None
        ranked = sorted(sources, key=lambda r: precedence_score(r.source), reverse=True)
        return RegistryEntry(active=ranked[0], shadowed=tuple(ranked[1:]))

    def is_shadowed(self, recipe_id: str) -> bool:
        """Quick check for ``recipe list`` shadow markers."""
        entry = self.get(recipe_id)
        return entry is not None and len(entry.shadowed) > 0

    def filter_by_tier(self, tier: str) -> list[RegistryEntry]:
        """Subset of entries whose active recipe matches the requested tier."""
        return [e for e in self.entries() if e.active.manifest.tier == tier]

    def filter_by_source(self, source: LoaderSource) -> list[RegistryEntry]:
        """Subset of entries whose active recipe was loaded from a given source."""
        return [e for e in self.entries() if e.active.source == source]


def load_explicit(recipe_dir: Path) -> LoadedRecipe:
    """Load a recipe from an explicit absolute path. Convenience re-export."""
    return load_explicit_path(recipe_dir)


__all__ = [
    "RegistryEntry",
    "RecipeRegistry",
    "load_explicit",
]
