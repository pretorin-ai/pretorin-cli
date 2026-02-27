#!/usr/bin/env bash
set -euo pipefail

# ── Pretorin CLI Demo Walkthrough ─────────────────────────────────────────────
# Guided tour of the full Pretorin CLI workflow for new beta users.
# Runs live commands against prod with pauses between sections for narration.
#
# Usage:  bash scripts/demo-walkthrough.sh
# ──────────────────────────────────────────────────────────────────────────────

GOLD='\033[33m'
ORANGE='\033[38;5;208m'
DIM='\033[2m'
BOLD='\033[1m'
RESET='\033[0m'

TEMP_NARRATIVE=""
DEMO_EVIDENCE_DIR=""

cleanup() {
    echo ""
    echo -e "${GOLD}${BOLD}── Cleanup ─────────────────────────────────────────${RESET}"
    if [[ -n "$TEMP_NARRATIVE" && -f "$TEMP_NARRATIVE" ]]; then
        rm -f "$TEMP_NARRATIVE"
        echo -e "  Removed temp narrative file: ${DIM}${TEMP_NARRATIVE}${RESET}"
    fi
    if [[ -n "$DEMO_EVIDENCE_DIR" && -d "$DEMO_EVIDENCE_DIR" ]]; then
        rm -rf "$DEMO_EVIDENCE_DIR"
        echo -e "  Removed demo evidence dir:   ${DIM}${DEMO_EVIDENCE_DIR}${RESET}"
    fi
    echo -e "${GOLD}Done.${RESET}"
}
trap cleanup EXIT

pause() {
    echo ""
    echo -e "${ORANGE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo -e "${ORANGE}${BOLD}  $1${RESET}"
    echo -e "${ORANGE}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
    echo ""
    read -r -p "  Press Enter to continue..." </dev/tty
    echo ""
}

run_cmd() {
    echo -e "  ${DIM}\$ $*${RESET}"
    echo ""
    "$@"
    echo ""
}

# ── Section 0: Pre-flight ────────────────────────────────────────────────────

echo ""
echo -e "${GOLD}${BOLD}"
echo "  ██████╗ ██████╗ ███████╗████████╗ ██████╗ ██████╗ ██╗███╗   ██╗"
echo "  ██╔══██╗██╔══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗██║████╗  ██║"
echo "  ██████╔╝██████╔╝█████╗     ██║   ██║   ██║██████╔╝██║██╔██╗ ██║"
echo "  ██╔═══╝ ██╔══██╗██╔══╝     ██║   ██║   ██║██╔══██╗██║██║╚██╗██║"
echo "  ██║     ██║  ██║███████╗   ██║   ╚██████╔╝██║  ██║██║██║ ╚████║"
echo "  ╚═╝     ╚═╝  ╚═╝╚══════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝"
echo -e "${RESET}"
echo -e "${ORANGE}  CLI Walkthrough Demo${RESET}"
echo ""
echo -e "  ${DIM}Pretorin is in closed beta. Framework/control browsing works for everyone.${RESET}"
echo -e "  ${DIM}Platform features (evidence, narratives, monitoring) require a beta code.${RESET}"
echo -e "  ${DIM}Sign up: https://pretorin.com/early-access/${RESET}"
echo ""
echo -e "  ${GOLD}${BOLD}Prerequisites:${RESET}"
echo -e "    • A Pretorin account with a beta code"
echo -e "    • A test system with the ${BOLD}fedramp-moderate${RESET} framework attached"
echo -e "    ${DIM}(Create both at https://platform.pretorin.com before running this demo)${RESET}"
echo ""

pause "Section 0: Pre-flight checks"

echo -e "  Checking that ${BOLD}pretorin${RESET} is on PATH..."
if ! command -v pretorin &>/dev/null; then
    echo -e "  ${GOLD}Error:${RESET} 'pretorin' not found. Install with: pip install pretorin"
    exit 1
fi
echo -e "  ✓ Found: $(command -v pretorin)"
echo ""

echo -e "  ${BOLD}Authenticate with your API key:${RESET}"
run_cmd pretorin login

echo -e "  ${BOLD}Confirming identity:${RESET}"
run_cmd pretorin whoami

# ── Section 1: Browse Frameworks ─────────────────────────────────────────────

pause "Section 1: Browse compliance frameworks"

echo -e "  ${BOLD}List all available frameworks:${RESET}"
run_cmd pretorin frameworks list

echo -e "  ${BOLD}Get details for FedRAMP Moderate:${RESET}"
run_cmd pretorin frameworks get fedramp-moderate

echo -e "  ${BOLD}List control families:${RESET}"
run_cmd pretorin frameworks families fedramp-moderate

echo -e "  ${BOLD}List Access Control controls (first 5):${RESET}"
run_cmd pretorin frameworks controls fedramp-moderate --family access-control --limit 5

echo -e "  ${BOLD}Drill into AC-02 (Account Management):${RESET}"
run_cmd pretorin frameworks control fedramp-moderate ac-02

# ── Section 2: System & Context ──────────────────────────────────────────────

pause "Section 2: Set your system context"

echo -e "  ${BOLD}List available systems:${RESET}"
run_cmd pretorin context list

echo ""
echo -e "  ${BOLD}If no systems appeared above, create one at platform.pretorin.com first.${RESET}"
echo -e "  ${DIM}(The demo will continue — 'context set' will fail if no systems exist.)${RESET}"
echo ""

echo -e "  ${BOLD}Select your active system (interactive picker):${RESET}"
echo -e "  ${DIM}This demo requires fedramp-moderate — select a system that has it.${RESET}"
echo ""
if ! pretorin context set; then
    echo ""
    echo -e "  ${GOLD}No systems available.${RESET}"
    echo -e "  Create a system with ${BOLD}fedramp-moderate${RESET} at ${BOLD}https://platform.pretorin.com${RESET} and re-run this demo."
    exit 1
fi

echo ""
echo -e "  ${BOLD}Show current context:${RESET}"
run_cmd pretorin context show

# Capture the active system name and framework for later commands
CONTEXT_JSON=$(pretorin context show --json 2>/dev/null || echo "{}")

ACTIVE_SYSTEM=$(echo "$CONTEXT_JSON" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('active_system_name', data.get('system', '')))
except Exception:
    pass
" 2>/dev/null || echo "")

ACTIVE_FRAMEWORK=$(echo "$CONTEXT_JSON" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('active_framework_id', data.get('framework', '')))
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -z "$ACTIVE_SYSTEM" ]]; then
    echo -e "  ${GOLD}Error:${RESET} Could not detect active system name."
    echo -e "  Create a system at ${BOLD}https://platform.pretorin.com${RESET} and re-run this demo."
    exit 1
fi

if [[ "$ACTIVE_FRAMEWORK" != "fedramp-moderate" ]]; then
    echo -e "  ${GOLD}Error:${RESET} This demo requires the ${BOLD}fedramp-moderate${RESET} framework."
    echo -e "  Selected framework: ${BOLD}${ACTIVE_FRAMEWORK:-none}${RESET}"
    echo ""
    echo -e "  Either:"
    echo -e "    1. Re-run this demo and select a system with fedramp-moderate attached"
    echo -e "    2. Attach fedramp-moderate to your system at ${BOLD}https://platform.pretorin.com${RESET}"
    exit 1
fi

echo -e "  ✓ Framework ${BOLD}fedramp-moderate${RESET} confirmed."

# ── Section 3: Evidence Workflow ─────────────────────────────────────────────

pause "Section 3: Create and push evidence"

DEMO_EVIDENCE_DIR="./evidence"

echo -e "  ${BOLD}Create a local evidence file for AC-02:${RESET}"
run_cmd pretorin evidence create ac-02 fedramp-moderate \
    -d "Role-based access control audit completed for demo walkthrough. All users verified against approved role matrix." \
    -n "Demo RBAC Evidence"

echo -e "  ${BOLD}List local evidence:${RESET}"
run_cmd pretorin evidence list

echo -e "  ${BOLD}Push evidence to the platform:${RESET}"
run_cmd pretorin evidence push

# ── Section 4: Narrative Workflow ────────────────────────────────────────────

pause "Section 4: Push an implementation narrative"

TEMP_NARRATIVE=$(mktemp /tmp/pretorin-demo-narrative-XXXXXX.md)

cat > "$TEMP_NARRATIVE" <<'NARRATIVE'
# AC-02 Account Management — Implementation Narrative

## Overview

The organization manages information system accounts through a centralized identity
provider (IdP) integrated with role-based access control (RBAC). Account lifecycle
events — creation, modification, disabling, and removal — are automated via
provisioning workflows tied to HR onboarding and offboarding processes.

## Key Controls

- **Account Creation**: Accounts are provisioned automatically when HR completes
  onboarding. Each account is assigned a role from the approved role matrix.
- **Periodic Review**: Quarterly access reviews are conducted by system owners.
  Results are documented and submitted to the compliance team.
- **Account Termination**: Accounts are disabled within 24 hours of separation
  notification from HR and removed after a 30-day retention period.

## Evidence

- Quarterly access review reports
- IdP provisioning audit logs
- HR separation workflow records
NARRATIVE

echo -e "  ${BOLD}Created temp narrative at:${RESET} ${DIM}${TEMP_NARRATIVE}${RESET}"
echo ""
echo -e "  ${DIM}--- narrative content ---${RESET}"
cat "$TEMP_NARRATIVE"
echo -e "  ${DIM}--- end ---${RESET}"
echo ""

if [[ -n "$ACTIVE_SYSTEM" ]]; then
    echo -e "  ${BOLD}Push narrative to platform:${RESET}"
    run_cmd pretorin narrative push ac-02 fedramp-moderate "$ACTIVE_SYSTEM" "$TEMP_NARRATIVE"
else
    echo -e "  ${GOLD}Skipping narrative push — could not detect active system name.${RESET}"
    echo -e "  ${DIM}Run manually: pretorin narrative push ac-02 fedramp-moderate <system> ${TEMP_NARRATIVE}${RESET}"
fi

# ── Section 5: Monitoring ────────────────────────────────────────────────────

pause "Section 5: Push a monitoring event"

echo -e "  ${BOLD}Push an access-review event:${RESET}"
run_cmd pretorin monitoring push \
    -t "Demo: Access review completed" \
    --severity info \
    --control ac-02 \
    --event-type access_review

# ── Section 6: Agent Skills (informational) ──────────────────────────────────

pause "Section 6: Agent skills (informational)"

echo -e "  ${BOLD}List available agent skills:${RESET}"
run_cmd pretorin agent skills

echo ""
echo -e "  ${DIM}The agent can run compliance tasks using an LLM backend.${RESET}"
echo -e "  ${DIM}Example (requires OPENAI_API_KEY or similar):${RESET}"
echo ""
echo -e "  ${DIM}  \$ pretorin agent run --skill gap-analysis${RESET}"
echo ""
echo -e "  ${DIM}Skills include: gap-analysis, narrative-generation,${RESET}"
echo -e "  ${DIM}evidence-collection, security-review.${RESET}"

# ── Section 7: MCP Integration (informational) ───────────────────────────────

pause "Section 7: MCP integration (informational)"

echo -e "  ${BOLD}Pretorin ships an MCP server for AI coding agents.${RESET}"
echo ""
echo -e "  Add it to Claude Code:"
echo ""
echo -e "  ${DIM}  \$ claude mcp add pretorin -- pretorin mcp-serve${RESET}"
echo ""
echo -e "  Or add to ${BOLD}.mcp.json${RESET}:"
echo ""
echo -e "  ${DIM}  {${RESET}"
echo -e "  ${DIM}    \"mcpServers\": {${RESET}"
echo -e "  ${DIM}      \"pretorin\": {${RESET}"
echo -e "  ${DIM}        \"command\": \"pretorin\",${RESET}"
echo -e "  ${DIM}        \"args\": [\"mcp-serve\"]${RESET}"
echo -e "  ${DIM}      }${RESET}"
echo -e "  ${DIM}    }${RESET}"
echo -e "  ${DIM}  }${RESET}"
echo ""
echo -e "  Once configured, Claude Code can browse frameworks, manage evidence,"
echo -e "  push narratives, and run compliance checks interactively."

# ── Section 8: Summary ───────────────────────────────────────────────────────

pause "Section 8: Summary"

echo -e "  ${GOLD}${BOLD}What we covered:${RESET}"
echo ""
echo -e "    1. ${BOLD}Authentication${RESET}     — login, whoami"
echo -e "    2. ${BOLD}Frameworks${RESET}         — list, get, families, controls, control detail"
echo -e "    3. ${BOLD}System context${RESET}     — list, set, show"
echo -e "    4. ${BOLD}Evidence${RESET}           — create, list, push"
echo -e "    5. ${BOLD}Narratives${RESET}         — write markdown, push to platform"
echo -e "    6. ${BOLD}Monitoring${RESET}         — push events (access reviews, scans, etc.)"
echo -e "    7. ${BOLD}Agent skills${RESET}       — gap-analysis, narrative-generation, and more"
echo -e "    8. ${BOLD}MCP integration${RESET}    — plug into Claude Code or any MCP-aware agent"
echo ""
echo -e "  ${ORANGE}Docs:${RESET}      https://docs.pretorin.com"
echo -e "  ${ORANGE}Platform:${RESET}  https://platform.pretorin.com"
echo -e "  ${ORANGE}Support:${RESET}   support@pretorin.com"
echo ""
echo -e "  ${GOLD}${BOLD}Thanks for trying Pretorin!${RESET}"
echo ""
