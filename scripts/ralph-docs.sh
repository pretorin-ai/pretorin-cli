#!/bin/bash

# ralph-docs.sh - Autonomous documentation sync for pretorin-cli
# Reads the actual codebase state and updates all docs to match reality.
# Run after ralph-maintenance.sh to keep docs current.
#
# Usage:
#   ./scripts/ralph-docs.sh

set -e

CHECKLIST_FILE="docs-checklist.md"
LOG_DIR="logs/maintenance"
mkdir -p "$LOG_DIR"

# Resume logic - check if we have an existing checklist with incomplete tasks
if [ -f "$CHECKLIST_FILE" ]; then
  if grep -q "^\- \[ \]" "$CHECKLIST_FILE" && ! grep -q "ALL_TASKS_DONE" "$CHECKLIST_FILE"; then
    EXISTING_BRANCH=$(git branch --show-current)
    if [[ "$EXISTING_BRANCH" == docs-sync/* ]]; then
      echo "Resuming docs sync on existing branch: $EXISTING_BRANCH"
      BRANCH_NAME="$EXISTING_BRANCH"
      LOG_FILE="$LOG_DIR/$(echo $BRANCH_NAME | tr '/' '-').log"
      echo "=== Resuming at $(date) ===" >> "$LOG_FILE"
    else
      echo "Found incomplete checklist but not on docs-sync branch."
      echo "Options:"
      echo "  1) Delete $CHECKLIST_FILE and start fresh"
      echo "  2) Checkout the docs-sync branch and re-run"
      exit 1
    fi
  else
    rm -f "$CHECKLIST_FILE"
    BRANCH_NAME="docs-sync/$(date +%Y%m%d-%H%M%S)"
    LOG_FILE="$LOG_DIR/$(echo $BRANCH_NAME | tr '/' '-').log"
    git checkout -b "$BRANCH_NAME"
    echo "Starting fresh docs sync on branch: $BRANCH_NAME"
    echo "=== Started at $(date) ===" > "$LOG_FILE"
  fi
else
  BRANCH_NAME="docs-sync/$(date +%Y%m%d-%H%M%S)"
  LOG_FILE="$LOG_DIR/$(echo $BRANCH_NAME | tr '/' '-').log"
  git checkout -b "$BRANCH_NAME"
  echo "Starting docs sync on branch: $BRANCH_NAME"
  echo "=== Started at $(date) ===" > "$LOG_FILE"
fi

echo "Log file: $LOG_FILE"

# Initialize checklist if it doesn't exist
if [ ! -f "$CHECKLIST_FILE" ]; then
  cat > "$CHECKLIST_FILE" << 'EOF'
# Documentation Sync Checklist

Reads the actual pretorin-cli codebase state and updates every doc file to match reality.

## Phase 1: Standalone Docs (top-level)

- [ ] **1. README.md Sync** - Verify README matches current feature set, install instructions, version, and quick-start commands. Update stale sections.
- [ ] **2. CLI.md Sync** - Read all typer commands in src/pretorin/cli/, compare against docs/CLI.md. Update command tables, examples, flags, and workflow descriptions.
- [ ] **3. MCP.md Sync** - Read all MCP tools in src/pretorin/mcp/tools.py and handlers, compare against docs/MCP.md. Update tool tables, parameters, examples, and tool counts.

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

EOF
  echo "Created $CHECKLIST_FILE"
fi

echo ""
echo "Starting docs sync loop..."
echo "Checklist: $CHECKLIST_FILE"
echo "Branch: $BRANCH_NAME"
echo "Log: $LOG_FILE"
echo ""

# Log function
log() {
  echo "$@" | tee -a "$LOG_FILE"
}

ITERATION=0
MAX_ITERATIONS=26  # Safety cap (18 tasks + buffer for retries)

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
  ITERATION=$((ITERATION + 1))
  log ""
  log "=== Iteration $ITERATION of $MAX_ITERATIONS at $(date) ==="

  # Check if all tasks complete
  if grep -q "ALL_TASKS_DONE" "$CHECKLIST_FILE" 2>/dev/null; then
    log ""
    log "All docs sync tasks complete!"
    log "Pushing branch and creating PR..."
    git push -u origin "$BRANCH_NAME"

    gh pr create --title "docs: sync all documentation with current codebase" --body "$(cat <<'PREOF'
## Documentation Sync

Documentation update generated by `ralph-docs.sh`.

### What Changed:
- Synced all doc files against actual codebase state
- Updated CLI command references, MCP tool references, agent docs
- Regenerated llms.txt manifests and mdBook output
- Fixed stale commands, env vars, file paths, and broken links
- Removed references to deleted features or tools

### Review Notes:
- Each doc update committed separately for easy review
- See `docs-checklist.md` for detailed progress log
- No code changes — docs only

---
Generated by scripts/ralph-docs.sh
PREOF
)"
    log ""
    log "PR created. Review the changes on branch: $BRANCH_NAME"
    log "=== Completed at $(date) ==="
    exit 0
  fi

  # Run Claude for one task
  set +e
  OUTPUT=$(claude --dangerously-skip-permissions -p "@$CHECKLIST_FILE

You are a technical writer syncing documentation for pretorin-cli, a Python CLI and MCP server for compliance automation. Your job is to READ the real code and UPDATE docs to match.

Branch: $BRANCH_NAME

CRITICAL: Complete exactly ONE task, commit your changes, then output <promise>DONE</promise> and stop.

## PROJECT STRUCTURE

Source code:
- src/pretorin/cli/ — typer CLI commands (main.py registers all subcommands)
- src/pretorin/mcp/tools.py — MCP tool definitions (Tool objects with inputSchema)
- src/pretorin/mcp/handlers/ — MCP tool handler implementations
- src/pretorin/mcp/handlers/__init__.py — TOOL_HANDLERS dispatch dict
- src/pretorin/agent/tools.py — agent tool definitions
- src/pretorin/agent/skills.py — agent skill definitions with tool_names lists
- src/pretorin/client/api.py — PretorianClient API methods
- src/pretorin/attestation.py — source attestation and verification
- src/pretorin/__init__.py — __version__ string

Documentation:
- README.md — top-level project overview
- docs/CLI.md — standalone CLI reference (detailed, with examples)
- docs/MCP.md — standalone MCP reference (detailed, with examples)
- docs/src/ — mdBook source files
- docs/src/SUMMARY.md — mdBook table of contents
- docs/src/cli/ — CLI feature pages and command reference
- docs/src/mcp/ — MCP overview, setup, tools, resources, troubleshooting
- docs/src/agent/ — agent overview, skills, runtime
- docs/src/frameworks/ — supported frameworks, control ID formats
- docs/src/workflows/ — workflow guides
- docs/src/reference/ — env vars, changelog, contributing, artifact schema
- docs/src/getting-started/ — install, auth, quickstart
- docs/book/ — generated mdBook output (rebuild with ./scripts/build-docs.sh)
- docs/llms.txt — LLM-friendly doc manifest
- docs/llms-full.txt — full LLM doc manifest

Config & metadata:
- pyproject.toml — package version, dependencies
- CHANGELOG.md — release history
- .github/workflows/test.yml — CI pipeline

## SOURCE OF TRUTH FOR EACH TASK

**README.md Sync:**
- Read pyproject.toml for version, description, dependencies
- Read src/pretorin/cli/main.py for registered command groups
- Read src/pretorin/mcp/tools.py for tool count
- Compare against README.md sections

**CLI.md Sync:**
- Read every file in src/pretorin/cli/ for command decorators, arguments, options
- Run: grep -rn '@app.command\|@.*\.command' src/pretorin/cli/
- Run: grep -rn 'typer.Argument\|typer.Option' src/pretorin/cli/
- Compare against docs/CLI.md command tables and examples

**MCP.md Sync:**
- Read src/pretorin/mcp/tools.py for all Tool() definitions
- Read src/pretorin/mcp/handlers/__init__.py for TOOL_HANDLERS dict
- Count tools and compare against docs/MCP.md tool tables and counts

**CLI Command Reference:**
- Read src/pretorin/cli/ and compare against docs/src/cli/command-reference.md
- Every @app.command should have a row in the reference table

**CLI Feature Pages:**
- For each docs/src/cli/<feature>.md, read the corresponding src/pretorin/cli/<module>.py
- Verify examples, flags, and described behavior match the code

**MCP Tool Reference:**
- Read src/pretorin/mcp/tools.py tool by tool
- Compare names, descriptions, parameters against docs/src/mcp/tools.md

**Agent Docs:**
- Read src/pretorin/agent/tools.py for ToolDefinition objects
- Read src/pretorin/agent/skills.py for Skill objects and tool_names
- Compare against docs/src/agent/ pages

**Framework Docs:**
- Read the list_frameworks output format and supported framework IDs
- Check framework counts mentioned in docs

**Workflow Pages:**
- Read CLI command flows and compare against docs/src/workflows/ descriptions
- Verify command examples still work

**Changelog:**
- Diff CHANGELOG.md against docs/src/reference/changelog.md

**Environment Variables:**
- grep -rn 'os.environ\|os.getenv\|PRETORIN_' src/pretorin/
- Compare against docs/src/reference/environment.md

**llms.txt Manifests:**
- Read docs/src/SUMMARY.md for page list
- Regenerate docs/llms.txt (title + URL per page) and docs/llms-full.txt (full content concat)
- Follow the existing format in those files

**mdBook Build:**
- Run ./scripts/build-docs.sh
- Commit any changes to docs/book/

**Dead Doc Detection:**
- For each CLI command mentioned in docs, verify it exists in src/pretorin/cli/
- For each MCP tool mentioned in docs, verify it exists in src/pretorin/mcp/tools.py
- For each env var mentioned in docs, verify it's used in src/pretorin/
- Remove or update stale references

**Cross-reference Validation:**
- Find all markdown links in docs/src/ files
- Verify relative links resolve to existing files
- Check SUMMARY.md entries point to real pages

## RULES

1. **READ BEFORE WRITING** - Always read the actual code files before touching a doc. Never guess.
2. **PRESERVE STRUCTURE** - Keep existing doc organization. Don't restructure unless sections are genuinely wrong.
3. **BE CONCISE** - Match existing doc style. Don't bloat docs with excessive detail.
4. **NO FABRICATION** - If you can't verify something from the code, don't write it.
5. **ONE TASK ONLY** - Complete one checklist item per iteration.
6. **COMMIT EACH UPDATE** - Use message format: \"docs(<scope>): <what was updated>\"
7. **UPDATE CHECKLIST** - Mark [x] complete, add log entry with commit hash and brief summary.
8. **RUN TESTS** - Before committing, run uv run pytest -x -q to make sure nothing broke.

## WORKFLOW

1. Read checklist, find first unchecked [ ] task
2. Read the source-of-truth files for that task
3. Read the current doc file
4. Update the doc to match reality
5. Commit with descriptive message
6. Update checklist: mark [x], add log entry
7. Output <promise>DONE</promise>
8. STOP IMMEDIATELY

When ALL tasks are [x] complete, add 'ALL_TASKS_DONE' at the end of the checklist.")
  CLAUDE_EXIT_CODE=$?
  set -e

  echo "$OUTPUT" | tee -a "$LOG_FILE"

  if [ $CLAUDE_EXIT_CODE -ne 0 ]; then
    log ""
    log "WARNING: Claude command exited with code $CLAUDE_EXIT_CODE"
    if grep -q "ALL_TASKS_DONE" "$CHECKLIST_FILE" 2>/dev/null; then
      log "Tasks are complete despite error. Proceeding with PR creation..."
      continue
    fi
    log "Waiting before retry..."
    sleep 5
    continue
  fi

  if echo "$OUTPUT" | grep -q "<promise>DONE</promise>"; then
    log ""
    log "--- Task completed, restarting with fresh context ---"
  else
    log ""
    log "WARNING: No completion marker found"
  fi

  sleep 2
done

log ""
log "Reached max iterations ($MAX_ITERATIONS)."
log "Check $CHECKLIST_FILE for remaining tasks."
log "Re-run the script to resume."
log "=== Stopped at $(date) ==="
exit 1
