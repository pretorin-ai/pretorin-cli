# Documentation Sync Checklist

Reads the actual pretorin-cli codebase state and updates every doc file to match reality.

## Phase 1: Standalone Docs (top-level)

- [x] **1. README.md Sync** - Verify README matches current feature set, install instructions, version, and quick-start commands. Update stale sections.
- [x] **2. CLI.md Sync** - Read all typer commands in src/pretorin/cli/, compare against docs/CLI.md. Update command tables, examples, flags, and workflow descriptions.
- [x] **3. MCP.md Sync** - Read all MCP tools in src/pretorin/mcp/tools.py and handlers, compare against docs/MCP.md. Update tool tables, parameters, examples, and tool counts.

## Phase 2: mdBook Core Reference (docs/src/)

- [ ] **4. Introduction & Getting Started** - Verify docs/src/introduction.md, installation.md, authentication.md, quickstart.md match current install flow, auth setup, and first-run experience.
- [ ] **5. CLI Command Reference** - Read src/pretorin/cli/ and compare against docs/src/cli/command-reference.md. Verify every command, subcommand, flag, and argument is documented. Add missing commands, remove stale ones.
- [ ] **6. CLI Feature Pages** - Read each CLI module (context.py, notes.py, evidence.py, etc.) and update the corresponding docs/src/cli/ page (context.md, notes.md, evidence.md, etc.). Verify examples work.
- [ ] **7. MCP Tool Reference** - Read src/pretorin/mcp/tools.py and compare against docs/src/mcp/tools.md. Verify every tool, parameter, and description matches. Update tool counts.
- [ ] **8. MCP Setup & Overview** - Verify docs/src/mcp/overview.md, setup.md, resources.md, troubleshooting.md match current MCP server behavior, config format, and resource URIs.

## Phase 3: Agent & Framework Docs

- [ ] **9. Agent Docs** - Read src/pretorin/agent/ (tools.py, skills.py, runtime.py) and update docs/src/agent/ pages. Verify skill names, tool lists, and runtime behavior match code.
- [ ] **10. Framework Docs** - Verify docs/src/frameworks/ pages (supported.md, control-ids.md, selection.md) match the current framework catalog. Check framework counts and ID format examples against actual data.

## Phase 4: Workflow Docs

- [ ] **11. Workflow Pages** - Read src/pretorin/cli/ workflow commands (campaigns, evidence, narratives, vendors) and compare against docs/src/workflows/ pages. Update workflows that have changed.
- [ ] **12. Changelog Sync** - Verify docs/src/reference/changelog.md matches CHANGELOG.md content. Ensure the latest version entry is present.
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
