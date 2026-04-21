# RFC 0001: Recipes

- **Status**: Draft
- **Branch**: `claude/extensible-connector-system-Sw59B`
- **Date**: 2026-04-21

## Summary

Introduce **recipes** as the extensibility mechanism for `pretorin-cli`. A recipe is a directory containing a markdown file with optional Python helper scripts that instructs an agent (Pretorin's own agent or any external MCP-capable agent) to produce compliance evidence and narratives for specific controls.

Recipes declare the environment tools they need; Pretorin probes availability and reports. **Pretorin does not own credentials, connections, or auth.** Users configure their environment with the tools they already use; recipes reference them by name.

## Motivation

To attract open-source contributions and let a GRC engineer build their entire compliance pipeline as code, `pretorin-cli` needs a well-defined extensibility surface. Today the codebase exposes one real plugin pattern (`ScannerBase`) and a static skill dict; everything else is hardcoded.

A recipe system turns compliance knowledge into shareable, reusable artifacts. The contribution shape (markdown + a few Python scripts) is intentionally lightweight so a compliance engineer — not only a Python developer — can ship one in an afternoon.

## Goals

- Contributor ergonomics: first recipe in 10 minutes.
- Low-ceremony contract: markdown + scripts, not a code-only Python ABC.
- Agent-agnostic: runnable by Pretorin's agent, Claude Code, Codex CLI, or any MCP-capable agent.
- Dual-surface execution: CLI and MCP.
- Declarative environment requirements; Pretorin probes, Pretorin doesn't own.
- Clear trust tiers; no gatekeeping of community recipes.
- Private / forked / combined recipes supported naturally via loader precedence.
- Preserve existing scanner functionality by bundling scanners as first-party recipes.

## Non-goals

- Credential storage, secrets management, or any auth ownership.
- Hosted recipe registry (deferred; maybe never).
- Pipeline manifest and scheduled execution (deferred to v2).
- Sandboxed or isolated recipe execution (deferred).
- Replacing `campaigns` — they remain orthogonal.

## Terminology

| Term | Meaning |
|---|---|
| **Recipe** | A directory containing `recipe.md` and optional helper scripts. Executed by an agent to produce evidence / narratives. |
| **Source** | Any backend a recipe reads from (AWS CLI, `gh`, `az`, a GitHub MCP server, a CSV file, etc.). Pretorin probes; users configure. |
| **Tool** | Function the agent can call during recipe execution — either a recipe script, a Pretorin-provided writer, or a tool exposed by an attached MCP server. |
| **Probe** | A small command Pretorin runs to verify a source is available (e.g. `gh auth status`, `aws sts get-caller-identity`). |
| **Campaign** | Existing bulk AI-driven orchestration across controls. Orthogonal to recipes. |

## Design

### Recipe anatomy

```
<recipe-id>/
  recipe.md              # instructions + frontmatter manifest (required)
  scripts/               # optional helper scripts the recipe references
    list_repos.py
    check_protection.py
  tests/                 # optional test fixtures and unit tests
    fixtures/
    test_recipe.py
  README.md              # optional, for long-form contributor docs
```

### Frontmatter schema (v1)

```yaml
---
id: github-branch-protection
name: "GitHub Branch Protection Evidence"
description: "Attests that default branches in the org are protected."
version: 0.1.0
author: "Pretorin Core Team"
tier: official                   # official | partner | community
contract_version: 1

attests:
  - { control: AC-2, framework: nist-800-53-r5 }
  - { control: CM-3, framework: nist-800-53-r5 }

evidence_type: configuration     # must be a value in VALID_EVIDENCE_TYPES

requires:
  cli:
    - name: gh
      probe: "gh auth status"
  mcp:
    - github                     # optional — falls back to gh CLI if absent
  env:
    - GITHUB_ORG

params:
  repos:
    type: array
    items: { type: string }
    description: "Repos to check (defaults to all org repos)"

scripts:
  list_repos: ./scripts/list_repos.py
  check_protection: ./scripts/check_protection.py
---
```

The frontmatter schema is the **public contract**. It is frozen per `contract_version`. Fields added later without breaking existing recipes do not bump the version; removals / shape changes do.

### Execution model

`pretorin recipe run <id>`:

1. Resolves `<id>` via loader precedence (below) and parses `recipe.md`.
2. Runs probes for every entry in `requires`. Halts with actionable errors on failure unless `--force`.
3. Validates supplied `--param` values against the recipe's `params` schema.
4. Loads the recipe's scripts as callable tools. Attaches Pretorin-provided writer tools. Attaches any MCP servers named in `requires.mcp`.
5. Feeds the markdown body (frontmatter stripped) as the agent's system prompt.
6. Delegates to the configured agent runner. Default: Pretorin's existing Codex-based runner at `src/pretorin/agent/runner.py`. Overrideable via `--runner`.
7. Collects agent output. Evidence / narratives produced via the writer tools flow through the existing `create_evidence_batch` path with provenance attached.
8. Returns a `RecipeResult`: `status` (`pass` / `fail` / `needs_input`), evidence count, narrative count, errors, and provenance.

### Discovery and distribution

Five loader paths, all feeding one in-memory registry:

1. **Built-in**: `src/pretorin/recipes/<id>/` — first-party, ships with the CLI.
2. **Installed packages**: any package declaring a `pretorin.recipes` entry point that resolves to a directory of recipes.
3. **User folder**: `~/.pretorin/recipes/<id>/`.
4. **Project folder**: `./.pretorin/recipes/<id>/` — checked into a company compliance repo alongside `pretorin.yaml` (v2).
5. **Explicit path**: `pretorin recipe run /abs/path/to/recipe-dir`.

Contributors writing their first recipe use path (1) via `pretorin recipe new` and a PR — lowest friction. Power users and enterprises use (2)–(5).

### Override precedence

When the same `id` resolves from multiple sources, this is the order (highest wins):

1. Explicit path
2. Project folder
3. User folder
4. Installed packages (entry points)
5. Built-in

`pretorin recipe show <id> --sources` lists every location the id appears, marks which is active, and flags any shadowed.

This makes three workflows natural without inventing new mechanisms:

- **Private recipes** — drop a directory in the user or project folder. Never published.
- **Forked recipes** — copy a public recipe into the project folder, modify, and the local version wins by id. `show --sources` makes the shadowing obvious.
- **Combined recipes (v1, limited)** — one recipe's script relatively-imports a helper from a sibling recipe. Richer composition (`depends_on`, `extends`) is deferred to v2's pipeline manifest.

### Connections: declare → probe → report

Pretorin does not own connections or auth. Users configure their environment the way they already do (`aws configure`, `gh auth login`, `az login`, `.mcp.json`, etc.).

A recipe declares requirements in `requires`:

- `cli`: named binaries with optional probe commands.
- `mcp`: named MCP servers the user has configured.
- `env`: required environment variable names (not values).

Pretorin ships a small library of well-known probes in `src/pretorin/recipes/_probes/` so common backends work without per-recipe boilerplate: `aws`, `azure`, `gcp`, `github` (`gh`), `cloudflare`, `kubectl`, `inspec`, `openscap`, plus a generic MCP ping.

Three CLI surfaces expose availability:

- `pretorin recipe list` — every recipe with a status column: `ready` / `missing: gh` / `missing: github (mcp)` / `missing: env GITHUB_ORG`.
- `pretorin recipe check <id>` — full doctor for one recipe with actionable remediation printed.
- `pretorin recipe run <id>` — refuses to execute on failed probes unless `--force`.

### Tool surface given to the agent

When an agent runs a recipe, its tool surface is:

- **Recipe scripts** — each entry in `scripts:` registered as a named tool.
- **Evidence writer** — `pretorin.write_evidence(...)`: creates a `LocalEvidence` and pushes via the existing batch path with `_provenance` attached automatically.
- **Narrative writer** — `pretorin.draft_narrative(...)` and `pretorin.push_narrative(...)`: produces the canonical markdown-with-frontmatter format already validated by `ensure_audit_markdown`.
- **MCP passthrough** — for each server named in `requires.mcp`, its tools attached directly.
- **Context object** — current system id, framework id, authenticated API client, structured logger.

This set is the stable v1 contract. Its shape is frozen per `contract_version`.

### CLI surface

```
pretorin recipe list [--tier TIER] [--source SOURCE]
                     [--framework FW] [--control CTL] [--ready-only]
pretorin recipe show <id> [--sources]
pretorin recipe check <id>
pretorin recipe run <id> [--param KEY=VALUE ...]
                         [--runner RUNNER] [--force]
pretorin recipe new <id>                      # scaffolder
pretorin recipe install <pkg>                 # thin wrapper over `uv pip install`
pretorin recipe search <query>                # v2, index-backed
```

### MCP exposure

Every registered recipe auto-exposes as an MCP tool named `recipe_<id>`, with `inputSchema` derived from `params` and description from frontmatter. Agents discover recipes via `list_tools` on the Pretorin MCP server, enabling any MCP-capable agent (Claude Code, Codex CLI, custom) to invoke a recipe exactly as a Pretorin-side tool.

Auto-exposure lives alongside the existing static tool registry at `src/pretorin/mcp/handlers/__init__.py`; no refactor to that registry required.

### Scanner migration

The existing `ScannerBase` subclasses become importable helpers:

- `pretorin.scanners.inspec`
- `pretorin.scanners.openscap`
- `pretorin.scanners.cloud_aws`
- `pretorin.scanners.cloud_azure`
- `pretorin.scanners.manual`

Each continues to encapsulate binary detection and profile execution. No behavior change.

Concrete scan targets (DISA RHEL 9 STIG, CIS AWS Foundations, etc.) become first-party recipes in `src/pretorin/recipes/`. Each recipe's script imports the relevant scanner helper, runs the profile, and uses the writer tools to emit `scan_result` evidence plus a summary narrative.

`ScanOrchestrator` is removed; the recipe runner takes its place.

The user-facing install story is unchanged — `pip install pretorin` still provides scanner functionality, now shaped as recipes.

### Contract versioning

- Every recipe declares `contract_version`.
- The CLI declares the versions it supports.
- When the contract breaks backwards-compatibly, CLI supports the previous version for at least two minor releases.
- `pretorin recipe check` warns when a recipe's `contract_version` is approaching end-of-life.

The v1 contract freezes:

- Frontmatter schema (fields enumerated above).
- Tool surface (writer functions + MCP passthrough + context shape).
- Script invocation convention: a Python module exposing an async `run(ctx, **params) -> dict`.
- `RecipeResult` return shape.

## Community model

### Trust tiers — signaled, not gatekept

| Tier | What it means | Where it lives |
|---|---|---|
| **Official** | Core-team reviewed, CI-tested, versioned with the CLI | `src/pretorin/recipes/` in this repo |
| **Partner** | Meets a published quality bar (passes schema validation, has tests, claimed via PR against `docs/recipes-index.json`) | Any pip package or index-listed source |
| **Community** | Anything else — pip packages following `pretorin-recipes-*` convention, or folder-drops | Anywhere |

`pretorin recipe list` shows the tier. Nothing is hidden; nothing is gated. Users pick their own risk tolerance.

### Contribution flow (official)

1. `pretorin recipe new my-recipe-id` scaffolds a recipe under `src/pretorin/recipes/` with a frontmatter template, a stubbed script, a README, and a local test harness.
2. Author writes the markdown body and scripts.
3. `pretorin recipe check my-recipe-id` runs the doctor in the author's own environment.
4. `pytest tests/recipes/test_my_recipe_id.py` runs fixtures and unit tests.
5. PR to `pretorin-cli` with `CODEOWNERS` routing to the recipes team.
6. On merge, the recipe ships in the next minor release.

### Seed library (launch)

Before broad promotion, ship **10–15 real recipes** covering genuinely useful compliance jobs:

- Scanner-derived (existing): STIG baselines, CIS cloud baselines — ~5
- GitHub: branch protection, code scanning, secret scanning — 3
- AWS: IAM password policy, S3 encryption, CloudTrail — 3
- Azure: tenant MFA, conditional access, storage encryption — 2
- Cloudflare: WAF rules, TLS policy — 2

An empty registry attracts no contributors. A library with visible gaps invites contribution.

### Discovery phasing

- **v1** — `docs/src/reference/recipes-catalog.md`: static, hand-curated, lists official + known partner / community recipes.
- **v2** (if volume demands) — `docs/recipes-index.json` that partner / community authors PR to; rendered as a searchable site. `pretorin recipe search` queries it. Zero hosted infra.
- **v3** (only if adoption demands) — hosted registry. Probably years out, possibly never.

### Growth levers

- Stable SEO-indexed URL per recipe.
- Author attribution shown in `recipe list`, `recipe show`, and in the evidence provenance produced by a recipe.
- "Published by `<firm>`" for consulting-firm recipes: trust + amplification.
- Invite 2–3 compliance consultancies to publish launch recipes.
- Blog post per recipe category, linked to stable URLs.

## Phasing

### v1 (this RFC)

- Frontmatter schema + script invocation convention.
- Registry with all five loader paths and override precedence.
- CLI commands: `list`, `show`, `check`, `run`, `new`, `install`.
- MCP auto-exposure.
- Well-known probes library.
- Scanner extraction into recipes.
- 10–15 seed recipes.
- `docs/src/reference/recipes-catalog.md` + contributor guide.
- `pretorin recipe new` scaffolder.

### v2 (next)

- Pipeline manifest: `pretorin.yaml` + `pretorin run`.
- Recipe composition: `depends_on`, `extends`.
- `docs/recipes-index.json` + `pretorin recipe search`.
- Optional auto-detection of pre-configured cloud CLIs for nicer first-run UX.

### v3+ (speculative)

- Hosted registry.
- Signed recipe packages.
- Subprocess / sandboxed recipe execution.
- Deprecate or merge `Skill` dataclass into recipes.

## Open questions

1. **Agent binding in v1.** Support any MCP-capable agent out of the box, or restrict to Pretorin's Codex runner and open up later?
2. **Claude Code skill compatibility.** Drop a Pretorin recipe into `.claude/skills/` and have it work natively? Marginal cost if we align frontmatter.
3. **Override precedence.** Is `project > user > installed > built-in` the right order, or should explicit invocation always win even over project?
4. **Combined recipes in v1.** Limited sibling-script imports, or defer all composition to v2?
5. **Parameter binding to named connections.** Do we let users write `--connection aws-prod` (requiring a named-connection concept) or keep it purely at the env-var / profile-name level?
6. **Enterprise private registries.** Explicit feature (e.g. `pretorin-config` with custom index URL) or "just use a private PyPI"?

## Out of scope

- Credential storage or secrets management.
- Hosted recipe marketplace.
- Scheduled / cron-like execution.
- Recipe sandboxing.
- Replacing or merging with the Campaign system.
- Recipe monetization.

## References

- `src/pretorin/scanners/base.py` — existing `ScannerBase` ABC (migration source).
- `src/pretorin/agent/skills.py` — existing `Skill` dataclass (subsumed by recipes; deprecate in v2).
- `src/pretorin/agent/runner.py` — agent runner that recipes delegate to.
- `src/pretorin/mcp/server.py`, `src/pretorin/mcp/handlers/__init__.py` — MCP registration points.
- `src/pretorin/mcp/tools.py` — MCP tool schema generation.
- `src/pretorin/evidence/writer.py`, `src/pretorin/client/api.py` — evidence write + push paths recipes reuse.
- `src/pretorin/workflows/campaign.py` — campaign system (orthogonal, preserved).
- `src/pretorin/workflows/markdown_quality.py` — `ensure_audit_markdown` used by the narrative writer.
