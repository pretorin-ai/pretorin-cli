# Maintenance Checklist

This checklist drives automated maintenance for pretorin-cli. Each task should IDENTIFY and FIX issues.

## Phase 1: Analysis & Quick Fixes

- [x] **1. CI Health Check** - Review recent GitHub Actions runs, identify existing failures to fix
- [x] **2. Lint Fixes** - Run ruff check + format, auto-fix what's possible, document remaining issues
- [x] **3. Type Check Fixes** - Run mypy, fix type errors in critical paths (client, MCP handlers, CLI)
- [x] **4. TODO/FIXME Audit** - Catalog all TODO/FIXME comments, resolve quick ones, create issues for complex ones

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

- **2026-04-18 07:36 — Task 1: CI Health Check** — All 5 recent CI runs checked. 4/5 green. One prior failure on feat/evidence-delete was a docs build output mismatch (stale mdBook search index), already fixed before merge. Master CI is fully green. No action needed. (no code commit — analysis only)
- **2026-04-18 — Task 2: Lint Fixes** — Ran `ruff check src/pretorin --fix` and `ruff format src/pretorin`. All checks passed, 85 files unchanged by formatter. No lint or format issues found. (no code commit — already clean)
- **2026-04-18 — Task 3: Type Check Fixes** — Ran `mypy src/pretorin`. All 85 source files pass with no issues. No fixes needed. (no code commit — already clean)
- **2026-04-18 — Task 4: TODO/FIXME Audit** — Searched all source and test files for `# TODO`, `# FIXME`, `<!-- TODO -->` comments. Found zero developer TODOs/FIXMEs. All `TODO` occurrences are `[[PRETORIN_TODO]]` markers — a domain-specific placeholder used in compliance narrative generation, not developer action items. No fixes needed. (no code commit — already clean)

