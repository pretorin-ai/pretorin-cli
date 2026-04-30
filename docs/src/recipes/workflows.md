# Workflows

Workflows sit one layer above recipes. A workflow is a **playbook** the
calling agent reads to learn how to iterate items in a domain (one
control, all pending scope questions, the entire campaign). Recipes
describe what to do per item; workflows describe how to walk the items.

Three-layer routing model:

```
engagement (deterministic Python rules)
  → workflow (markdown playbook the calling agent reads)
    → recipe (calling agent picks per item from the menu)
```

The engagement layer (`pretorin_start_task`) lands later — see the
roadmap. v1 ships the workflow registry and the per-workflow playbook
markdown so the agent can navigate manually.

## What Ships in v1

Four built-in workflows:

| ID | Iterates over | Pick when |
|----|---------------|-----------|
| `single-control` | one control | The user names exactly one control id and the work fits in a single focused pass. |
| `scope-question` | scope questionnaire items | The user references the scope questionnaire or scope is the active workflow-state blocker. |
| `policy-question` | policy questionnaire items | The user references an org policy questionnaire or policy is the active blocker. |
| `campaign` | many controls (server-side) | Bulk control work — drafting narratives or capturing evidence for a family or framework. |

Browse them:

```bash
pretorin recipe list  # for recipes (CLI)
```

There's no `pretorin workflow list` CLI yet — workflows are discovered
through MCP only:

- `pretorin_list_workflows` — summary metadata for every loaded workflow.
- `pretorin_get_workflow(workflow_id)` — full manifest plus the markdown body.

## How a Workflow's Body Looks

Every workflow body has the same shape: a brief intent statement, a
description of the iteration shape, a step-by-step block, and a "what
to avoid" closing section. Read one of the built-ins as a template:

```bash
cat src/pretorin/workflows_lib/_workflows/single-control/workflow.md
```

The frontmatter declares:

| Field | Notes |
|-------|-------|
| `id` | kebab-case, globally unique |
| `version` | SemVer-ish |
| `name` | display name |
| `description` | ≥ 50 chars, what the engagement layer matches against |
| `use_when` | ≥ 30 chars, explicit trigger guidance |
| `produces` | `evidence` / `narrative` / `answers` / `mixed` |
| `iterates_over` | `single_control` / `scope_questions` / `policy_questions` / `campaign_items` |
| `recipes_commonly_used` | hint list of recipe ids the agent often picks |

## Why Workflows Matter

Without workflows, the calling agent would freelance the iteration
pattern for every task. That's drift-prone — different agents hit the
same questionnaire and follow different orders, producing inconsistent
audit trails. The workflow body fixes the pattern: load pending items,
filter, iterate, pick a recipe per item, submit through the audit
boundary, optionally trigger review.

`recipes_commonly_used` is a hint, not a binding. The agent reads
`pretorin_list_recipes` at runtime and picks per-item by matching
`use_when` strings, then falls back to freelance only when no recipe
fits.

## Server-Side vs Calling-Agent Iteration

Three of the four workflows are **calling-agent iteration**: the agent
loops items in its own context window, calling MCP tools per item. Fine
for small sets (one control, ~50 questionnaire items).

`campaign` is **server-side iteration**: pretorin's own CodexAgent walks
items inside pretorin, calling the same recipe surface. The calling
agent kicks off the campaign and observes status — it doesn't iterate
items in its own context. This is what makes thousand-control campaigns
tractable without overwhelming the calling agent's context window.

## Authoring a New Workflow

v1 doesn't ship a workflow scaffolder — workflows are first-party only.
If you need a new iteration shape, open an issue describing:

- What domain it iterates (controls? questions? something else?).
- Why the existing four don't fit.
- The recipes the workflow would commonly use.

Community workflows land in v1.5 once the engagement layer is in place
and the routing rules can include community contributions safely.

## What's Already Wired

- **Engagement layer** (`pretorin_start_task`) — picks the workflow
  from the user's prompt entities. See [Engagement Layer](./engagement.md).
- **Recipe selection in the campaign hot site** — `draft_control_artifacts`
  consults `pretorin.recipes.selection.select_recipe_for_drafting` before
  falling through to freelance prose. The decision is recorded as a
  `RecipeSelection` record on the response and written to the audit
  trail. v1's built-in recipes don't cover narrative drafting, so the
  current path is "log selection → freelance"; community recipes that
  attest the matching `(control, framework)` plug in automatically.

## Roadmap

- **In-process recipe execution** — when the selector finds a recipe
  match, dispatch to `run_script` in-process instead of falling
  through to freelance. v1.5; v1 records the would-have-picked
  decision so the audit trail is forward-compatible.
- **Community workflows** — third loader path, scaffolder, validator.
  v1.5.
