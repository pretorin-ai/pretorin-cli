# Ralph Checklist

Automated codebase maintenance and documentation sync for pretorin-cli.

## Part A: Code Quality

### Analysis & Quick Fixes

- [x] **A1. CI Health Check** - Review recent GitHub Actions runs, identify existing failures to fix
- [x] **A2. Lint Fixes** - Run ruff check + format, auto-fix what's possible, document remaining issues
- [x] **A3. Type Check Fixes** - Run mypy, fix type errors in critical paths (client, MCP handlers, CLI)
- [x] **A4. TODO/FIXME Audit** - Catalog all TODO/FIXME comments, resolve quick ones, create issues for complex ones

### Test Quality

- [ ] **A5. Test Coverage Analysis** - Identify files <60% coverage, write missing tests for critical code (client, attestation, MCP handlers)
- [ ] **A6. Dead Test Cleanup** - Find and remove tests for deleted features/code, fix flaky tests

### Code Quality

- [ ] **A7. Code Duplication Audit** - Find redundant utilities, similar handler patterns, copy-paste code across CLI/MCP/agent surfaces
- [ ] **A8. Dead Code Removal** - Find unused imports, functions, models, CLI commands. Remove them.
- [ ] **A9. Dependency Updates** - Check for outdated or vulnerable dependencies, update safe ones, document risky ones

### Release & Config Health

- [ ] **A10. Version Consistency** - Verify pyproject.toml version == __init__.py __version__ == CHANGELOG.md latest heading. Fix drift.
- [ ] **A11. MCP Tool Registration Audit** - Verify every Tool in tools.py has a handler in __init__.py and vice versa. Flag orphans.
- [ ] **A12. Agent Skill Tool Coverage** - Verify agent skills reference tools that actually exist in agent/tools.py. Flag stale references.

### Maintenance Verification

- [ ] **A13. Maintenance Verification** - Run `./tools/check.sh` locally (lint, typecheck, all tests). If it passes, mark complete. Do NOT push, create a PR, or run CI — the outer script handles that.

## Part B: Documentation Sync

### Standalone Docs

- [ ] **B1. README.md Sync** - Verify README matches current feature set, install instructions, version, and quick-start commands. Update stale sections.
- [ ] **B2. CLI.md Sync** - Read all typer commands in src/pretorin/cli/, compare against docs/CLI.md. Update command tables, examples, flags, and workflow descriptions.
- [ ] **B3. MCP.md Sync** - Read all MCP tools in src/pretorin/mcp/tools.py and handlers, compare against docs/MCP.md. Update tool tables, parameters, examples, and tool counts.

### mdBook Core Reference

- [ ] **B4. Introduction & Getting Started** - Verify docs/src/introduction.md, installation.md, authentication.md, quickstart.md match current install flow, auth setup, and first-run experience.
- [ ] **B5. CLI Command Reference** - Read src/pretorin/cli/ and compare against docs/src/cli/command-reference.md. Verify every command, subcommand, flag, and argument is documented. Add missing commands, remove stale ones.
- [ ] **B6. CLI Feature Pages** - Read each CLI module and update the corresponding docs/src/cli/ page. Verify examples work.
- [ ] **B7. MCP Tool Reference** - Read src/pretorin/mcp/tools.py and compare against docs/src/mcp/tools.md. Verify every tool, parameter, and description matches. Update tool counts.
- [ ] **B8. MCP Setup & Overview** - Verify docs/src/mcp/overview.md, setup.md, resources.md, troubleshooting.md match current MCP server behavior, config format, and resource URIs.

### Agent & Framework Docs

- [ ] **B9. Agent Docs** - Read src/pretorin/agent/ (tools.py, skills.py, runtime.py) and update docs/src/agent/ pages. Verify skill names, tool lists, and runtime behavior match code.
- [ ] **B10. Framework Docs** - Verify docs/src/frameworks/ pages match the current framework catalog. Check framework counts and ID format examples against actual data.

### Workflow Docs

- [ ] **B11. Workflow Pages** - Read src/pretorin/cli/ workflow commands and compare against docs/src/workflows/ pages. Update workflows that have changed.
- [ ] **B12. Changelog Sync** - Verify docs/src/reference/changelog.md matches CHANGELOG.md content. Ensure the latest version entry is present.
- [ ] **B13. Environment Variables** - Read all env var references in src/pretorin/ and compare against docs/src/reference/environment.md. Add missing vars, remove stale ones.

### Generated Artifacts & Cross-references

- [ ] **B14. llms.txt Manifests** - Regenerate docs/llms.txt and docs/llms-full.txt from current docs/src/ content. Verify they match the SUMMARY.md structure.
- [ ] **B15. mdBook Build** - Run ./tools/build-docs.sh to rebuild docs/book/ from docs/src/. Commit any changes to generated output.
- [ ] **B16. Dead Doc Detection** - Find docs referencing deleted CLI commands, removed MCP tools, old env vars, or nonexistent file paths. Fix or remove stale content.
- [ ] **B17. Cross-reference Validation** - Verify all internal markdown links in docs/src/ resolve to real files. Fix broken links. Check SUMMARY.md entries all point to existing pages.
- [ ] **B18. Final Verification** - Run `./tools/check.sh` to ensure no changes broke anything. If it passes, mark complete. Do NOT push, create a PR, or run CI — the outer script handles that.

## Progress Log

- 2026-05-02 — A1 CI Health Check: reviewed last 15 GitHub Actions runs. All recent runs on `master`, release tags (`v0.17.0`, `v0.17.1`), and active feature branches passed. One historical failure on `feat/recipes-v1` (2026-04-30T06:15:37Z) was followed by a successful retry on the same branch, so it was already addressed before merge. No outstanding CI failures to fix. (no commit — observation-only task)
- 2026-05-02 — A2 Lint Fixes: ran `uv run ruff check .` and `uv run ruff format --check .` across the whole repo. All checks passed; 249 files already formatted. No remaining issues to document. (checklist-only commit)
- 2026-05-02 — A3 Type Check Fixes: ran `uv run mypy src/pretorin`. Result: "Success: no issues found in 119 source files". Type checking is clean across client, MCP handlers, CLI, and all other modules. No fixes required. (checklist-only commit)
- 2026-05-02 — A4 TODO/FIXME Audit: grep across `src/pretorin/` and `tests/` for `TODO|FIXME|XXX|HACK`. All matches fall into two intentional categories: (1) scaffolder template strings in `frameworks/templates.py` (init-custom output) and `cli/recipe.py` (`pretorin recipe new` output) — placeholders meant for end users to fill in, not code TODOs; (2) `[[PRETORIN_TODO]]` markers used by the narrative/evidence system to denote audit gaps (agent prompts, runner, narrative display, tests). Zero actual code TODO/FIXME comments to resolve. No code changes required. (checklist-only commit)
