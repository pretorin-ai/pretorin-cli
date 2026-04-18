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
- **2026-04-18 — Task 6: Dead Test Cleanup** — Thorough audit of all 1445 tests + 38 skipped. All imports resolve; no broken references. Removed 4 dead tests: 1 sham test (TestCliMainGuard in test_small_coverage_gaps.py — mocked app then called the mock, tested nothing, already covered by test_main_entry.py) and 3 duplicate tests (TestNormalizeControlId in test_api_client_coverage2.py — exact copies of tests in test_api_client.py). The 38 skipped tests are all integration tests that conditionally skip without PRETORIN_API_KEY — legitimate, not dead. No flaky tests found. Commit: 6421c58.
- **2026-04-18 — Task 7: Code Duplication Audit** — Found and fixed 3 categories of duplication: (1) `_safe_args()` was copy-pasted in 5 MCP handler files — extracted to `mcp/helpers.py` as `safe_args()`. (2) Validation constants (`VALID_EVIDENCE_TYPES`, `VALID_CONTROL_STATUSES`) were duplicated in CLI modules — now imported from `mcp/helpers.py`. (3) Four identical helper functions (`_platform_base_url`, `_validate_working_directory`, `_answer_map`, `_normalize_text`) in `cli/scope.py` and `cli/policy.py` — extracted to new `cli/questionnaire_helpers.py`. Net: 12 files changed, -8 lines (97 added, 105 removed). Also noted but left as-is: CLI error-handling boilerplate (decorator would be higher-risk refactor) and scope resolution wrappers (intentional layering). Commit: e801b5f.
- **2026-04-18 — Task 8: Dead Code Removal** — Audited entire src/pretorin/ for dead code. No unused imports (ruff F401 clean), no dead CLI commands, no orphaned modules. Removed 7 unused Pydantic model classes from client/models.py (APIError, ArtifactSubmissionResult, SystemSummary, ComplianceStatusResponse, ScopeQuestionResponse, MonitoringEventResponse, PolicyQuestionResponse — all defined but never referenced). Removed 1 unused helper function `_json_text()` from workflows/campaign.py. Net: 2 files changed, -74 lines. All 1441 tests pass. Commit: 03bee41.
- **2026-04-18 — Task 5: Test Coverage Analysis** — Overall coverage 74%. Identified critical low-coverage MCP handler files: stig.py (22%), vendors.py (23%), workflow.py (43%). Added 104 tests across 3 new test files. Results: stig.py 22%→99%, vendors.py 23%→100%, workflow.py 43%→77%. Client (76%) and attestation (95%) already at acceptable levels. Commit: cbbd130.

