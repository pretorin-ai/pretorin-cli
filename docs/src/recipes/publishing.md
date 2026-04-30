# Publishing Recipes

Recipes can ship at three tiers. The tier is set by the loader from the
recipe's source path, not by what the manifest declares. Where you put the
recipe directory determines who can run it and how.

## Three Distribution Models

### 1. Personal — User Folder

```
~/.pretorin/recipes/<id>/
```

Drop a recipe directory there and `pretorin recipe list` shows it
immediately. Loaded as `tier: community`. No further setup.

Use this when:

- You're prototyping a recipe.
- The recipe encodes a personal workflow no one else needs.
- You're working through the [10-minute walkthrough](./index.md#write-your-first-recipe-in-10-minutes).

The user folder isn't synced anywhere — it lives on your machine.

### 2. Team — Project Folder

```
<repo>/.pretorin/recipes/<id>/
```

Checked into your team's compliance repo (the same repo with `pretorin.yaml`
or your team's CLAUDE.md). The loader walks up from CWD looking for a
`.pretorin/recipes/` directory, so any teammate working in the repo gets
the recipes automatically.

Use this when:

- The recipe encodes a team-specific procedure (e.g., "pull our internal
  IAM audit log endpoint").
- You want your CI to validate the recipes alongside the rest of the
  compliance repo.
- The recipe is too domain-specific to belong upstream but everyone on
  the team needs it.

Loaded as `tier: community`. The project folder has higher precedence
than the user folder, so a team-shared recipe shadows a teammate's
personal copy with the same id.

### 3. Upstream — First-Party in pretorin-cli

```
src/pretorin/recipes/_recipes/<id>/
```

Forced to `tier: official` by the loader. Distributed with every
pretorin-cli install.

Use this when:

- The recipe is broadly useful to anyone running pretorin (a new scanner
  wrapper, a generic capture pattern).
- You're willing to maintain it — official recipes get tested in CI and
  block releases on regressions.
- The procedure is stable enough that a SemVer bump with backwards-
  incompatible changes would be unusual.

## How to Submit a First-Party Recipe

1. **Open an issue first.** Describe what the recipe does and why it
   belongs in the upstream set rather than as a community recipe. The
   first-party set is intentionally small — it's a curation surface, not
   a catch-all.

2. **Scaffold under `_recipes/`** — clone pretorin-cli and create the
   recipe directory:

   ```bash
   pretorin recipe new my-new-scanner --location builtin
   ```

   This drops the recipe under `src/pretorin/recipes/_recipes/<id>/`
   with the right structure.

3. **Set `tier: official` in the manifest.** The loader will override
   from the source path anyway, but it documents intent.

4. **Add a smoke test.** Every built-in recipe has at least one test
   under `tests/recipes/` that loads it through the registry and
   verifies the basic shape. Copy the pattern from
   `tests/recipes/test_builtin_scanner_recipes.py`.

5. **Run quality gates locally:**

   ```bash
   pretorin recipe validate my-new-scanner
   pytest tests/recipes/
   ./tools/check.sh quick
   ```

6. **PR the recipe.** Include in the description: what the recipe does,
   when an agent should pick it (your `use_when` text is a good start),
   and what scanners or platform APIs it depends on. Reference the
   issue from step 1.

7. **Maintenance commitment.** Once merged, the recipe ships with every
   pretorin-cli release. Be prepared to respond to issues against it.

## How to Share a Community Recipe

There's no central registry yet (pretorin's `recipe install <pkg>` is
v1.5). For now, share a community recipe by:

- **Posting the recipe directory in a gist or repo.** Anyone can clone
  it into their `~/.pretorin/recipes/` or `<repo>/.pretorin/recipes/`
  and use it.
- **Opening a PR against your team's compliance repo.** The recipe lands
  under `<repo>/.pretorin/recipes/<id>/` and is loaded automatically by
  every teammate.

When you publish a community recipe, fill out:

- **`license`** — required for anything you share publicly. SPDX
  identifier (`Apache-2.0`, `MIT`, etc.).
- **`author`** — your name or your team's name. Stamped in the audit
  metadata of every evidence record the recipe writes.
- **`description`** — clear enough that someone else's agent can decide
  whether to pick it without needing to read your team's wiki.

## Tier and Trust

The calling agent sees `tier` on every recipe in `pretorin_list_recipes`
output. v1 doesn't gate execution by tier — a community recipe runs
just like an official one. What tier does is:

- **Audit signal.** Every evidence record stamped by a community recipe
  carries the recipe id, version, and author. A reviewer can trace
  which recipes contributed to a system's evidence set.
- **Selection signal.** When two recipes both fit a task, the agent
  prefers the official one unless the community one's `description`
  makes a stronger case.

`partner` tier is reserved for recipes shipped via installed Python
packages (deferred to v1.5). The shape is: a Python package declares an
entry point pointing at a recipe directory inside the package; the
loader picks it up at install time.

## Versioning Your Recipe

Bump `version` in the manifest when:

- The recipe's behavior changes in a way that would surprise a previous
  consumer (different output shape, different side effects, different
  redaction rules).
- A bug fix changes results materially.

Don't bump for cosmetic edits to the body or doc-only changes. Recipe
version stamps every evidence record, so a version bump means the audit
trail reflects "results from a different procedure."

`recipe_schema_version` is independent — it tracks the frontmatter shape,
not the recipe's behavior. Most recipes pin this to `"1.0"` and never
touch it.
