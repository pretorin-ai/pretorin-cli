"""Recipe extensibility surface for Pretorin.

A recipe is a markdown + scripts directory the calling agent (Claude Code via MCP,
``pretorin agent run``, or any other MCP-capable agent) reads as a playbook and
executes by calling pretorin tools. Pretorin exposes recipes as a registry plus a
tool surface; **pretorin does not run a recipe-level LLM** — that's the
load-bearing architectural decision behind everything in this package.

See ``docs/rfcs/0001-recipes.md`` for the contract spec and the design doc at
``~/.gstack/projects/pretorin-ai-pretorin-cli/isaacfaber-recipe-implementation-design-20260429-120046.md``
for v1 implementation details.

Modules:
- ``errors``: shared exception hierarchy.
- ``manifest``: pydantic models for ``recipe.md`` frontmatter (RecipeManifest,
  RecipeParam, RecipeRequires, ScriptDecl).
- ``loader``: parses recipe.md from the four v1 loader paths (built-in, user,
  project, explicit). Lazy walk + mtime cache + per-recipe validation isolation.
- ``registry``: exposes loaded recipes for the CLI and MCP surfaces.
"""
