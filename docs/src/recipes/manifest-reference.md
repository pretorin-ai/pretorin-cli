# Manifest Reference

The manifest is the YAML frontmatter at the top of `recipe.md`. It's the
public contract between recipe authors and pretorin. The schema is defined
by the pydantic models in `src/pretorin/recipes/manifest.py` and frozen per
`contract_version`.

## Minimal Example

```markdown
---
id: my-first-recipe
version: 0.1.0
name: "My First Recipe"
description: "Capture the active IAM role's trust policy and attach it as a configuration record."
use_when: "The agent needs evidence that an IAM role's trust policy meets least-privilege requirements."
produces: evidence
author: "Jane Doe"
license: Apache-2.0
scripts:
  capture:
    path: scripts/capture.py
    description: "Pull the trust policy from AWS and return it as a redacted dict."
---

# My First Recipe Body

The agent reads everything below the closing `---` to understand what to do.
```

## Required Fields

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | Kebab-case (`^[a-z][a-z0-9-]*$`). Globally unique across loader paths. |
| `version` | string | SemVer-ish. Bumped when behavior changes. Stamped on evidence. |
| `name` | string | Display name shown in `pretorin recipe list`. |
| `description` | string | ≥ 50 chars. The text the agent reads to decide if this recipe fits. |
| `use_when` | string | ≥ 30 chars. Explicit "when the agent has X and needs Y" guidance. |
| `produces` | enum | `evidence` / `narrative` / `both`. What the recipe writes back to the platform. |
| `author` | string | Attribution. Stamped in evidence provenance. |

## Optional Fields

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `tier` | enum | `community` | `official` / `partner` / `community`. Loader overrides from source path. |
| `license` | string | `Apache-2.0` | SPDX identifier. Required for any recipe shared publicly. |
| `params` | map | `{}` | Recipe-level inputs. See [Params](#params). |
| `requires` | object | `{}` | CLI binaries / env vars the recipe needs. See [Requires](#requires). |
| `attests` | list | `[]` | `[{control, framework}]` hints. Filter, not binding. |
| `scripts` | map | `{}` | `tool_name → ScriptDecl`. Each becomes an MCP tool. See [Scripts](#scripts). |
| `contract_version` | int | `1` | Frontmatter shape version. Bumps only on breaking changes. |
| `recipe_schema_version` | string | `"1.0"` | Schema this recipe is written against. |
| `min_pretorin_version` | string | `null` | Loader refuses to load if running pretorin is older. |

## Tier

`tier` is set by the loader from the recipe's source path, **overriding**
whatever the manifest declares:

- Built-in path → `official`
- User folder, project folder, explicit path → `community`
- `partner` → reserved for installed packages (v1.5)

Authors should still declare a tier — it documents intent, and any
manifest-internal validation runs against the declared value.

## Params

Recipe-level params are inputs the calling agent supplies via
`pretorin_start_recipe(...)`. They flow through to scripts as kwargs.

```yaml
params:
  stig_id:
    type: string
    description: "STIG benchmark id targeting Linux baseline controls"
    required: true
  target:
    type: string
    description: "Optional connection string (e.g., 'ssh://host')"
    default: "local"
```

Supported types: `string`, `integer`, `number`, `boolean`, `array`. For
`array`, declare `items: { type: ... }` so the MCP renderer can emit a
real JSON Schema.

## Requires

Document the runtime environment the recipe needs. v1 captures the
requirements but does **not** run probes — the v1.5 `pretorin recipe
check` will. Failures surface at runtime when scripts try to invoke
missing tools.

```yaml
requires:
  cli:
    - { name: inspec, probe: "inspec --version" }
    - { name: jq, probe: "jq --version" }
  env:
    - AWS_PROFILE
    - INSPEC_TARGET
```

## Attests

`attests` is a list of `{control, framework}` entries the recipe is
**likely** relevant to. It's a hint for filtering, never a binding —
the agent picks recipes by reading `description` and `use_when`, not
by joining on `attests`.

```yaml
attests:
  - { control: AC-2, framework: nist-800-53-r5 }
  - { control: AC-6, framework: nist-800-53-r5 }
```

## Scripts

Each `ScriptDecl` becomes an MCP tool:

```yaml
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Pull the manifest, run the scan, return per-rule results."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id"
        required: true
      target:
        type: string
        description: "Connection string"
    timeout_seconds: 600
    writes_evidence: false
```

| Field | Notes |
|-------|-------|
| `path` | Relative to the recipe directory. The validator checks the file exists and contains `async def run`. |
| `description` | One-liner the agent sees on the tool. Be specific — this is the tool's "tooltip". |
| `params` | Per-script JSON Schema input. Independent of recipe-level `params`. |
| `timeout_seconds` | Wall-clock cap for one invocation. Default 300. |
| `writes_evidence` | Declared intent. The trust gate for community recipes considers it. |

The MCP tool name for this script is `pretorin_recipe_<safe_id>__run_scan`,
where `safe_id` is the recipe id with hyphens converted to underscores
(MCP tool names can't contain hyphens). The recipe author doesn't construct
this name — pretorin does.

## Contract and Schema Versioning

Two version fields exist for forward compatibility:

- `contract_version` — bumps only on backwards-incompatible shape changes
  to the frontmatter itself. Most recipes pin to `1`.
- `recipe_schema_version` — the schema this specific recipe is written
  against. The loader refuses to load a recipe whose schema is newer than
  what the running pretorin supports, with a hint to upgrade.

`min_pretorin_version` lets a recipe author require a specific runtime
version (e.g., when a recipe uses a writer tool that only exists in
pretorin ≥ 0.18).

## What the Loader Does to Your Manifest

1. Parses the YAML frontmatter.
2. Validates against the pydantic schema. A failure raises
   `RecipeManifestError` for *that* recipe — the registry keeps loading
   other recipes.
3. Overrides `tier` from the source path (built-in → official, otherwise
   community).
4. Caches the parsed manifest by `(path, mtime)`. If you edit the file,
   the next load re-parses it.
