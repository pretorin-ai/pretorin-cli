# Pretorin CLI — Claude Code Instructions

## Quick Reference

- **Main branch**: `master`
- **Language**: Python 3.10+, managed with `uv`
- **Docs**: mdBook (`docs/src/` → `docs/book/`, committed)

## Architecture

Pretorin CLI is **three things, not one** — keep these boundaries clean when modifying or extending the codebase:

1. **Platform API gateway** — most of the CLI (`src/pretorin/cli/evidence.py`, `cli/control.py`, `cli/scan.py`, `cli/vendor.py`, `cli/narrative.py`, etc.) and the entire MCP server (`src/pretorin/mcp/`) are thin wrappers over the platform API. **No LLM runs in pretorin in this path.** External agents (Claude Code, Codex CLI, custom MCP clients) call pretorin tools via MCP; the calling agent does all the reasoning. CLI commands run synchronously and call the platform; that's it.

2. **`pretorin agent run`** (`src/pretorin/cli/agent.py`) — the *only* place pretorin runs its own LLM. Backed by `CodexAgent` (`src/pretorin/agent/codex_agent.py`) or legacy OpenAI Agents SDK (`src/pretorin/agent/runner.py` → `ComplianceAgent`). Used when the user doesn't have their own local agent. Behaves like Claude Code: takes a prompt, reasons, calls pretorin's same platform-API tools (just over a Python in-process boundary instead of MCP). Optional dependency group: `pip install pretorin[builtin-agent]`.

3. **`pretorin skill install`** (`src/pretorin/cli/skill.py`) — installs a bundled "pretorin" skill into `~/.claude/skills/pretorin/` or `~/.codex/skills/pretorin/`. The skill content (markdown + scripts) is what the calling agent reads to understand pretorin's surface. `KNOWN_AGENTS` registry maps each known agent to its skill directory pattern. Adding support for a new agent is a one-line addition there.

**Recipes and workflows are playbooks the calling agent executes, not pretorin-side runtimes.** A recipe is markdown + scripts. The calling agent (whichever one) reads the body, plans, and calls tools as needed. Pretorin exposes recipes as a registry plus a tool surface. **There is no recipe-level LLM in pretorin.** This is the same model as Claude Code skills exactly. The only LLM pretorin runs is via `pretorin agent`, which from the recipe layer's perspective is just another calling agent.

When extending pretorin:
- New compliance feature that just exposes a platform API → new MCP handler in `mcp/handlers/` plus new CLI command in `cli/`. No agent code involved.
- New "way for an agent to do work" → new recipe under `src/pretorin/recipes/<id>/` (markdown + scripts). No new runtime, no new agent abstraction.
- New "kind of work the calling agent orchestrates" → new workflow playbook under `src/pretorin/workflows_lib/<id>/workflow.md`.
- New agent capability that requires its own LLM (rare; only the existing internal agent uses one) → extend `pretorin agent`. Don't create a new agent runtime.

**Recipe extensibility is a community contribution surface, not just a core-team surface.** Recipes load from four paths (highest precedence wins):

1. **Explicit path** — `pretorin recipe run /abs/path/...` for testing while authoring.
2. **Project folder** — `./.pretorin/recipes/<id>/` for team-shared recipes checked into the team's compliance repo.
3. **User folder** — `~/.pretorin/recipes/<id>/` for solo contributors' local recipes.
4. **Built-in** — `src/pretorin/recipes/<id>/` for first-party recipes that ship with pretorin-cli.

When adding a first-party recipe, drop it under `src/pretorin/recipes/<id>/` with `tier: official` in the frontmatter. When the recipe is genuinely external, the contributor uses `pretorin recipe new <id>` to scaffold (defaults to user folder, marked `tier: community`). Authoring docs live at `docs/src/recipes/`.

**RFC 0001 (`docs/rfcs/0001-recipes.md`)** is the authoritative recipe contract spec. **Draft RFC `docs/rfcs/draft-evidence-metadata.md`** describes the audit-trail metadata baseline that lands on the platform's evidence model.

## Dev Setup

```bash
uv pip install -e ".[dev]"
```

## Commands

```bash
# Tests
pytest                          # unit tests (60% coverage minimum)
pytest --cov=pretorin           # with coverage
pytest -m integration           # integration tests (needs PRETORIN_API_KEY)

# Lint + type check
ruff check src/pretorin
ruff format --check src/pretorin
mypy src/pretorin

# All-in-one
./tools/check.sh quick        # lint + typecheck + tests
```

## Version Bumps

Three files must stay in sync:
1. `pyproject.toml` → `version = "X.Y.Z"`
2. `src/pretorin/__init__.py` → `__version__ = "X.Y.Z"`
3. `CHANGELOG.md` + `docs/src/reference/changelog.md` (add entry + compare link)

Also update `docs/src/getting-started/installation.md` (expected output example).

## Docs Build

```bash
./tools/build-docs.sh
```

Rebuild and commit `docs/book/` whenever doc sources change — CI diffs the output. The Rust toolchain is pinned to 1.94.1 for deterministic search index hashes.

## Release Process

1. Bump version (see above)
2. Rebuild docs, commit everything
3. Merge to `master`
4. `git tag vX.Y.Z && git push origin vX.Y.Z`
5. `gh release create vX.Y.Z --title "vX.Y.Z" --notes "..."`
6. The `publish.yml` workflow automatically publishes to PyPI and the MCP Registry — the tag must match the package version

## Project Layout

See [CONTRIBUTING.md](CONTRIBUTING.md) for contributor guidelines and [docs/](docs/src/) for full documentation.
