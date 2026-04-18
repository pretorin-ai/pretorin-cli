# Documentation Sync Checklist

Reads the actual pretorin-cli codebase state and updates every doc file to match reality.

## Phase 1: Standalone Docs (top-level)

- [x] **1. README.md Sync** - Verify README matches current feature set, install instructions, version, and quick-start commands. Update stale sections.
- [x] **2. CLI.md Sync** - Read all typer commands in src/pretorin/cli/, compare against docs/CLI.md. Update command tables, examples, flags, and workflow descriptions.
- [x] **3. MCP.md Sync** - Read all MCP tools in src/pretorin/mcp/tools.py and handlers, compare against docs/MCP.md. Update tool tables, parameters, examples, and tool counts.

## Phase 2: mdBook Core Reference (docs/src/)

- [x] **4. Introduction & Getting Started** - Verify docs/src/introduction.md, installation.md, authentication.md, quickstart.md match current install flow, auth setup, and first-run experience.
- [x] **5. CLI Command Reference** - Read src/pretorin/cli/ and compare against docs/src/cli/command-reference.md. Verify every command, subcommand, flag, and argument is documented. Add missing commands, remove stale ones.
- [x] **6. CLI Feature Pages** - Read each CLI module (context.py, notes.py, evidence.py, etc.) and update the corresponding docs/src/cli/ page (context.md, notes.md, evidence.md, etc.). Verify examples work.
- [x] **7. MCP Tool Reference** - Read src/pretorin/mcp/tools.py and compare against docs/src/mcp/tools.md. Verify every tool, parameter, and description matches. Update tool counts.
- [x] **8. MCP Setup & Overview** - Verify docs/src/mcp/overview.md, setup.md, resources.md, troubleshooting.md match current MCP server behavior, config format, and resource URIs.

## Phase 3: Agent & Framework Docs

- [x] **9. Agent Docs** - Read src/pretorin/agent/ (tools.py, skills.py, runtime.py) and update docs/src/agent/ pages. Verify skill names, tool lists, and runtime behavior match code.
- [x] **10. Framework Docs** - Verify docs/src/frameworks/ pages (supported.md, control-ids.md, selection.md) match the current framework catalog. Check framework counts and ID format examples against actual data.

## Phase 4: Workflow Docs

- [x] **11. Workflow Pages** - Read src/pretorin/cli/ workflow commands (campaigns, evidence, narratives, vendors) and compare against docs/src/workflows/ pages. Update workflows that have changed.
- [x] **12. Changelog Sync** - Verify docs/src/reference/changelog.md matches CHANGELOG.md content. Ensure the latest version entry is present.
- [ ] **13. Environment Variables** - Read all env var references in src/pretorin/ and compare against docs/src/reference/environment.md. Add missing vars, remove stale ones.

## Phase 5: Generated Artifacts & Cross-references

- [ ] **14. llms.txt Manifests** - Regenerate docs/llms.txt and docs/llms-full.txt from current docs/src/ content. Verify they match the SUMMARY.md structure.
- [ ] **15. mdBook Build** - Run ./scripts/build-docs.sh to rebuild docs/book/ from docs/src/. Commit any changes to generated output.
- [ ] **16. Dead Doc Detection** - Find docs referencing deleted CLI commands, removed MCP tools, old env vars, or nonexistent file paths. Fix or remove stale content.
- [ ] **17. Cross-reference Validation** - Verify all internal markdown links in docs/src/ resolve to real files. Fix broken links. Check SUMMARY.md entries all point to existing pages.
- [ ] **18. Local Verification** - Run `./scripts/check.sh` to ensure no docs changes broke anything. If it passes, mark complete. Do NOT push, create a PR, or run CI — the outer script handles that.

## Progress Log

- **Task 1** (7c885bd): README.md — added missing commands (login/logout/whoami, control status/context, evidence link/delete, notes resolve), added Policy & Scope Questionnaires section.
- **Task 2** (c5d3ff2): CLI.md — added Control, Policy, Scope, Skill sections; added context verify/manifest, evidence link/delete, narrative create/list/push, notes create/push/resolve commands; fixed push vs push-file; updated reference table.
- **Task 3** (5f36941): MCP.md — updated tool count to 86; added get_cli_status, get_source_manifest, delete_evidence to tables; added detailed entries for search_evidence, delete_evidence, get_cli_status, get_source_manifest; fixed required/optional param annotations across all detailed entries.
- **Task 4** (09ca308): Introduction & Getting Started — updated version to 0.15.1 in installation.md; added login flags (--api-key/-k, --api-url) and whoami --json to authentication.md; fixed API URL to /api/v1/public; fixed evidence create example order in quickstart.md; added STIG/CCI browsing section; added vendor, STIG/CCI, policy/scope capabilities to introduction.md.
- **Task 5** (bba6235): CLI Command Reference — added Control, Policy, Scope, Skill sections; added context verify/manifest, evidence link/delete, narrative create/list/push, notes create/list/push/add commands; fixed frameworks control flag (--brief not --references), vendor delete flag (--yes not --force), agent run/mcp-add params, monitoring and review flags.
- **Task 6** (14addda): CLI Feature Pages — replaced deprecated --references with --brief/-b in frameworks.md; added context verify/manifest to context.md; added notes resolve to notes.md; added evidence link to evidence.md; added --framework-id/-f to review status; fixed --artifacts description in campaigns.md; fixed STIG severity values to cat_i/cat_ii/cat_iii; added full options table to monitoring.md.
- **Task 7** (fedce8f): MCP Tool Reference — updated tool count to 86; added get_cli_status, get_source_manifest, delete_evidence; fixed param names (provider_type, responsibility_mode, source_type, checkpoint_path, nist_control_id, cci_id); corrected required/optional annotations for scope-defaulting params; added missing params to campaign, STIG, and vendor tools.
- **Task 8** (2ac883f): MCP Setup & Overview — updated overview.md tool count from 23 to 86; expanded category table from 5 to 13 categories with correct tool counts; added status://cli and workflow://recipe/{recipe_id} resources to resources.md; setup.md and troubleshooting.md verified accurate.
- **Task 9** (6a1ad3f): Agent Docs — added stig-scan and cci-assessment skills to skills.md (6 total); fixed model key precedence in overview.md (config.api_key over OPENAI_API_KEY by default); added --max-turns, --no-mcp, short flags to overview.md; added --scope flag, http transport, and updated examples in runtime.md.
- **Task 10** (e213ea1): Framework Docs — added Tier column and Framework Tiers section (foundational/operational/strategic) to supported.md; added enhancement ID formats (ac-02.1, ac-02(1)) and auto-normalization section to control-ids.md; selection.md verified accurate.
- **Task 11** (6b15a06): Workflow Pages — fixed narrative-evidence.md push→push-file command; removed deprecated --references flag from gap-analysis.md and cross-framework.md (references now shown by default); added CLI commands (policy show/populate, scope show/populate) to policy-scope.md.
- **Task 12** (5ce460c): Changelog Sync — added missing v0.15.1 and v0.15.0 entries to docs/src/reference/changelog.md; fixed 0.11.0 date (04-01→04-02); added comparison links for new versions.
