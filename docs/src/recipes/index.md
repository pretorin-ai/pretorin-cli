# Authoring Recipes

Recipes are markdown-plus-Python playbooks that the calling AI agent invokes
through MCP. Each recipe is a directory with a `recipe.md` (frontmatter +
prose body) and one or more script files. The agent reads the body to
understand what the recipe does, picks one when its `use_when` matches the
task, and calls the recipe's scripts as MCP tools.

If you've ever written a Claude Code skill, the shape will feel familiar —
recipes are the same idea, scoped to compliance work and stamped with audit
metadata automatically.

## Why You Might Write One

Three concrete reasons:

- **Your team has a non-obvious procedure** for capturing a particular kind
  of evidence (e.g., "pull the latest IAM policy from the prod account, redact
  customer ARNs, attach as a configuration record"). Encoding it as a recipe
  means every teammate's agent does the same steps the same way.
- **You wrap an internal scanner** that produces STIG-style results. A recipe
  exposes it next to the built-in `inspec-baseline` / `openscap-baseline` so
  the calling agent can pick it for the rules it covers.
- **You're contributing back upstream**. First-party scanner recipes
  (`inspec-baseline`, `openscap-baseline`, etc.) live under
  `src/pretorin/recipes/_recipes/`. New contributions follow the same shape.

## Write Your First Recipe in 10 Minutes

```bash
# 1. Scaffold a fresh recipe in your user folder.
pretorin recipe new my-first-recipe

# 2. The scaffolder drops a directory at ~/.pretorin/recipes/my-first-recipe/
#    with recipe.md, scripts/main.py, README.md, tests/test_recipe.py.

# 3. Edit the description, use_when, and the body of recipe.md.
$EDITOR ~/.pretorin/recipes/my-first-recipe/recipe.md

# 4. Edit scripts/main.py — implement `async def run(ctx, **params)`.
$EDITOR ~/.pretorin/recipes/my-first-recipe/scripts/main.py

# 5. Validate.
pretorin recipe validate my-first-recipe
```

If validate passes, the recipe is in the registry. Restart your MCP client
and the agent can use it on the next task.

## What Ships in v1

- **Four loader paths** with clear precedence: explicit > project > user > built-in.
  See [Loader paths](#loader-paths) below.
- **`pretorin recipe list / show / new / validate`** CLI commands.
- **`pretorin_list_recipes` / `pretorin_get_recipe`** MCP discovery tools.
- **Per-script MCP tools** auto-registered as
  `pretorin_recipe_<safe_id>__<script_name>`.
- **Audit-metadata stamping**: the calling agent opens a recipe execution
  context with `pretorin_start_recipe(...)`; every platform write inside the
  context is stamped with `producer_kind="recipe"`, the recipe id, and the
  recipe version. The platform records the full chain.

## Loader Paths

| Source | Path | Use it when |
|--------|------|-------------|
| Built-in | `src/pretorin/recipes/_recipes/<id>/` | First-party recipes shipped with pretorin-cli. |
| User folder | `~/.pretorin/recipes/<id>/` | Your local recipes — survives across projects. |
| Project folder | `<repo>/.pretorin/recipes/<id>/` | Team-shared recipes checked into the compliance repo. |
| Explicit path | `pretorin recipe show --path /abs/...` | Testing a recipe while authoring. |

If the same id appears in two paths, the higher-precedence one wins.
`pretorin recipe show <id> --sources` lists every location and marks which
is active.

## Tier

Each loaded recipe gets a `tier` set by the loader from its source path:

- `official` — built-in, shipped with pretorin-cli (forced regardless of
  what the manifest says).
- `community` — anything from the user/project folders or explicit paths.
- `partner` — reserved for installed packages (v1.5).

The calling agent sees the tier in `pretorin_list_recipes` output and can
factor it in when picking. Community recipes are first-class — the tier
is signal, not a permission gate.

## Where to Read Next

- [Manifest reference](./manifest-reference.md) — every frontmatter field with examples.
- [Script contract](./script-contract.md) — the `async def run(ctx, **params) -> dict` signature.
- [Writer tools](./writer-tools.md) — the platform-API tools your scripts call, and how audit metadata gets stamped.
- [Testing](./testing.md) — pytest fixtures and patterns.
- [Publishing](./publishing.md) — how to share a community recipe or PR an official one.
- [Worked example](./example/index.md) — a community recipe walked through end-to-end.
