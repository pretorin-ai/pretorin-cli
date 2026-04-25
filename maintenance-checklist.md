# Maintenance Checklist

This checklist drives automated maintenance for pretorin-cli. Each task should IDENTIFY and FIX issues.

## Phase 1: Analysis & Quick Fixes

- [x] **1. CI Health Check** - Review recent GitHub Actions runs, identify existing failures to fix
- [x] **2. Lint Fixes** - Run ruff check + format, auto-fix what's possible, document remaining issues
- [x] **3. Type Check Fixes** - Run mypy, fix type errors in critical paths (client, MCP handlers, CLI)
- [ ] **4. TODO/FIXME Audit** - Catalog all TODO/FIXME comments, resolve quick ones, create issues for complex ones

## Phase 2: Test Quality

- [ ] **5. Test Coverage Analysis** - Identify files <60% coverage, write missing tests for critical code (client, attestation, MCP handlers)
- [ ] **6. Dead Test Cleanup** - Find and remove tests for deleted features/code, fix flaky tests

## Phase 3: Code Quality

- [ ] **7. Code Duplication Audit** - Find redundant utilities, similar handler patterns, copy-paste code across CLI/MCP/agent surfaces
- [ ] **8. Dead Code Removal** - Find unused imports, functions, models, CLI commands. Remove them.
- [ ] **9. Dependency Updates** - Check for outdated or vulnerable dependencies, update safe ones, document risky ones

## Phase 4: Release & Config Health

- [ ] **10. Version Consistency** - Verify pyproject.toml version == __init__.py __version__ == CHANGELOG.md latest heading. Fix drift.
- [ ] **11. MCP Tool Registration Audit** - Verify every Tool in tools.py has a handler in __init__.py and vice versa. Flag orphans.
- [ ] **12. Agent Skill Tool Coverage** - Verify agent skills reference tools that actually exist in agent/tools.py. Flag stale references.

## Phase 5: Wrap-up

- [ ] **13. Local Verification** - Run `./scripts/check.sh` locally (lint, typecheck, all tests). If it passes, mark complete. Do NOT push, create a PR, or run CI — the outer script handles that.

## Progress Log

- **2026-04-25 Task 1 — CI Health Check**: All 15 recent CI runs green (14 success, 1 cancelled docs deploy superseded by later push). Workflows: Test (3.10/3.11/3.12), Lint, Type Check, Dependency Audit, Docker Test, Docs, Integration, Publish. No failures to fix. pip-audit ignores CVE-2026-4539 (pygments, no fix available). No changes needed.
- **2026-04-25 Task 2 — Lint Fixes** (7aec65a): Fixed 88 lint violations across 47 test files. src/pretorin was already clean. Issues fixed: F401 unused imports, I001 unsorted imports, N806 PascalCase mock vars, E501 long lines, E402 import ordering, F841 unused vars. Applied ruff format to all files. All 1584 tests pass, 0 lint errors remaining.
- **2026-04-25 Task 3 — Type Check Fixes** (0c41fd0): With overrides removed, mypy strict found 100 errors across 5 files. Fixed 90 errors in client/api.py (added _request_dict/_request_list typed helpers to narrow dict|list union at 82 call sites), client/config.py (added cast() to 8 properties returning Any from JSON dict), and cli/version_check.py (typed json.load and PyPI response). Removed 3 mypy override sections that suppressed real errors. Remaining 10 errors in mcp/server.py and mcp/resources.py are MCP library boundary issues (untyped decorators, AnyUrl vs str) — override retained. mypy strict clean, 1584 tests pass.

