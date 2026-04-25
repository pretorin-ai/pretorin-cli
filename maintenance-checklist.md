# Maintenance Checklist

This checklist drives automated maintenance for pretorin-cli. Each task should IDENTIFY and FIX issues.

## Phase 1: Analysis & Quick Fixes

- [x] **1. CI Health Check** - Review recent GitHub Actions runs, identify existing failures to fix
- [x] **2. Lint Fixes** - Run ruff check + format, auto-fix what's possible, document remaining issues
- [x] **3. Type Check Fixes** - Run mypy, fix type errors in critical paths (client, MCP handlers, CLI)
- [x] **4. TODO/FIXME Audit** - Catalog all TODO/FIXME comments, resolve quick ones, create issues for complex ones

## Phase 2: Test Quality

- [x] **5. Test Coverage Analysis** - Identify files <60% coverage, write missing tests for critical code (client, attestation, MCP handlers)
- [x] **6. Dead Test Cleanup** - Find and remove tests for deleted features/code, fix flaky tests

## Phase 3: Code Quality

- [x] **7. Code Duplication Audit** - Find redundant utilities, similar handler patterns, copy-paste code across CLI/MCP/agent surfaces
- [x] **8. Dead Code Removal** - Find unused imports, functions, models, CLI commands. Remove them.
- [x] **9. Dependency Updates** - Check for outdated or vulnerable dependencies, update safe ones, document risky ones

## Phase 4: Release & Config Health

- [x] **10. Version Consistency** - Verify pyproject.toml version == __init__.py __version__ == CHANGELOG.md latest heading. Fix drift.
- [x] **11. MCP Tool Registration Audit** - Verify every Tool in tools.py has a handler in __init__.py and vice versa. Flag orphans.
- [ ] **12. Agent Skill Tool Coverage** - Verify agent skills reference tools that actually exist in agent/tools.py. Flag stale references.

## Phase 5: Wrap-up

- [ ] **13. Local Verification** - Run `./scripts/check.sh` locally (lint, typecheck, all tests). If it passes, mark complete. Do NOT push, create a PR, or run CI — the outer script handles that.

## Progress Log

- **2026-04-25 Task 1 — CI Health Check**: All 15 recent CI runs green (14 success, 1 cancelled docs deploy superseded by later push). Workflows: Test (3.10/3.11/3.12), Lint, Type Check, Dependency Audit, Docker Test, Docs, Integration, Publish. No failures to fix. pip-audit ignores CVE-2026-4539 (pygments, no fix available). No changes needed.
- **2026-04-25 Task 2 — Lint Fixes** (7aec65a): Fixed 88 lint violations across 47 test files. src/pretorin was already clean. Issues fixed: F401 unused imports, I001 unsorted imports, N806 PascalCase mock vars, E501 long lines, E402 import ordering, F841 unused vars. Applied ruff format to all files. All 1584 tests pass, 0 lint errors remaining.
- **2026-04-25 Task 3 — Type Check Fixes** (0c41fd0): With overrides removed, mypy strict found 100 errors across 5 files. Fixed 90 errors in client/api.py (added _request_dict/_request_list typed helpers to narrow dict|list union at 82 call sites), client/config.py (added cast() to 8 properties returning Any from JSON dict), and cli/version_check.py (typed json.load and PyPI response). Removed 3 mypy override sections that suppressed real errors. Remaining 10 errors in mcp/server.py and mcp/resources.py are MCP library boundary issues (untyped decorators, AnyUrl vs str) — override retained. mypy strict clean, 1584 tests pass.
- **2026-04-25 Task 4 — TODO/FIXME Audit**: Searched all src/pretorin/ and tests/ files for developer TODO, FIXME, HACK, and XXX comments. Zero found. The only "TODO" strings in the codebase are `[[PRETORIN_TODO]]` markers — intentional product functionality used as narrative placeholders in compliance workflows. No action needed.
- **2026-04-25 Task 5 — Test Coverage Analysis** (0cbae39): Identified 8 files below 60% coverage. Wrote 68 new tests across 5 test files targeting the worst gaps: cli/cci.py (14%→100%), cli/vendor.py (20%→93%), cli/narrative.py (54%→80%), cli/notes.py (59%→81%), mcp/handlers/systems.py (65%→100%). Overall coverage improved from 77% to 80%. All 1652 tests pass, 0 regressions. Remaining low-coverage files: cli/scan.py (13%), cli/stig.py (14%), cli/skill.py (22%), scanners/* (0%) — these are lower-priority CLI modules and the scanner subsystem (not yet integrated).
- **2026-04-25 Task 6 — Dead Test Cleanup** (0d26c63): Audited all 83 test files (1652 tests). Zero dead tests found: all imports resolve to existing source symbols, all 200+ patch targets reference valid module paths, no empty/trivial test functions, no duplicate test names within the same scope. No flaky tests detected (consistent pass across multiple runs). Converted 12 tests in test_campaign_apply.py from manual asyncio.run() to native async/await, aligning with project's pytest-asyncio conventions and eliminating unnecessary event loop creation. One cosmetic ResourceWarning from CliRunner + asyncio.run() interaction in campaign CLI tests — CPython GC timing issue, not a test quality problem. All 1652 tests pass, 0 regressions.
- **2026-04-25 Task 7 — Code Duplication Audit** (b63186d): Audited all src/pretorin/ for cross-module duplication. Found the highest-impact pattern: narrative/writer.py, notes/writer.py, and evidence/writer.py each had identical copies of `_safe_path_component`, `_slugify`, and `_parse_frontmatter` (~50 LOC × 3). All three sync modules (narrative/sync.py, notes/sync.py, evidence/sync.py) duplicated the same frontmatter-rewrite logic. Created `local_file.py` as the single source of truth for these 4 shared functions. Refactored all 6 modules to import from it, retaining backward-compatible aliases. Net reduction: 46 LOC removed. Also identified lower-priority patterns (CLI auth/JSON-mode boilerplate, MCP handler error-handling patterns, agent-vs-MCP domain logic overlap) — these are structural patterns where extracting shared code would add indirection without proportional benefit. All 1652 tests pass, 0 regressions.
- **2026-04-25 Task 8 — Dead Code Removal** (de26c89): Scanned all src/pretorin/ for dead code using ruff (F401/F811/F841) and manual cross-reference analysis. Removed: 3 dead ROMEBOT_* constants in cli/main.py (duplicates of context.py, zero references), 3 dead functions in workflows/compliance_updates.py (_safe_value, build_narrative_todo_block, build_gap_note — zero production callers, only tested directly), 1 dead function in workflows/campaign.py (_is_valid_evidence_type — never called, validation handled by Pydantic), and 2 dead tests covering removed functions. Kept: PretorianClient.get_evidence (public API method for real endpoint), Pydantic response models (structurally required for API deserialization). Net: 81 lines removed, 4 files changed. All 1650 tests pass, 0 lint errors, mypy clean, 0 regressions.
- **2026-04-25 Task 10 — Version Consistency** (13a1747): All version sources consistent at 0.16.2: pyproject.toml, src/pretorin/__init__.py, CHANGELOG.md latest heading, docs/src/reference/changelog.md, docs/src/getting-started/installation.md. Fixed two drift issues in CHANGELOG.md: (1) added 10 missing compare links for versions 0.9.7 through 0.16.0, and (2) backported 4 missing version entries (0.10.0, 0.12.0, 0.13.0, 0.13.1) that had git tags and docs changelog entries but were absent from the main CHANGELOG. Note: v0.15.5 has a CHANGELOG entry but no git tag — pre-existing issue, not introduced by this maintenance.
- **2026-04-25 Task 9 — Dependency Updates** (1422b6a): Ran pip-audit: found 2 CVEs. Fixed CVE-2026-28684 by updating python-dotenv 1.2.1→1.2.2 (transitive via pydantic-settings). Also updated certifi 2026.1.4→2026.4.22 (CA bundle), click 8.3.1→8.3.3, typer 0.24.0→0.24.2 (patch-level, safe). Added pip CVE-2026-3219 to CI audit ignore (no fix available, same as existing pygments CVE-2026-4539 ignore). Risky updates deferred: rich 14→15 (major), starlette 0.52→1.0 (major), cryptography 46→47 (major), openai/openai-agents (significant minor bumps with breaking API changes likely). All 1650 tests pass, 0 regressions.
- **2026-04-25 Task 11 — MCP Tool Registration Audit**: Audited all 87 MCP tools. Compared tool definitions in mcp/tools.py (87 Tool objects with name=) against handler dispatch table in mcp/handlers/__init__.py (87 TOOL_HANDLERS entries). Perfect 1:1 match — every tool has a handler and every handler has a tool. Also verified server.py wiring: list_tools() exposes tools.py definitions, call_tool() dispatches via TOOL_HANDLERS dict. PUBLIC_TOOL_NAMES set (pretorin_get_cli_status) references a valid tool. Zero orphans, no changes needed.

