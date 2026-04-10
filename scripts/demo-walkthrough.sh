#!/usr/bin/env bash
set -uo pipefail

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

DEMO_EVIDENCE_DIR=""
DEMO_NARRATIVES_DIR=""
DEMO_NOTES_DIR=""

cleanup() {
    echo ""
    echo -e "${GOLD}${BOLD}── Cleanup ─────────────────────────────────────────${RESET}"
    if [[ -n "$DEMO_EVIDENCE_DIR" && -d "$DEMO_EVIDENCE_DIR" ]]; then
        rm -rf "$DEMO_EVIDENCE_DIR"
        echo -e "  Removed demo evidence dir:    ${DIM}${DEMO_EVIDENCE_DIR}${RESET}"
    fi
    if [[ -n "$DEMO_NARRATIVES_DIR" && -d "$DEMO_NARRATIVES_DIR" ]]; then
        rm -rf "$DEMO_NARRATIVES_DIR"
        echo -e "  Removed demo narratives dir:  ${DIM}${DEMO_NARRATIVES_DIR}${RESET}"
    fi
    if [[ -n "$DEMO_NOTES_DIR" && -d "$DEMO_NOTES_DIR" ]]; then
        rm -rf "$DEMO_NOTES_DIR"
        echo -e "  Removed demo notes dir:       ${DIM}${DEMO_NOTES_DIR}${RESET}"
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
    if ! "$@"; then
        echo ""
        echo -e "  ${GOLD}⚠ Command failed:${RESET} $*"
        echo -e "  ${DIM}Continuing...${RESET}"
        echo ""
        return 1
    fi
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
echo -e "  ${DIM}Pretorin is in closed beta. Framework/control browsing works for authenticated users.${RESET}"
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

echo -e "  Checking authentication..."
if pretorin whoami &>/dev/null; then
    echo -e "  ✓ Already authenticated."
    echo ""
    echo -e "  ${BOLD}Current session:${RESET}"
    run_cmd pretorin whoami
else
    echo -e "  ${BOLD}Authenticate with your API key:${RESET}"
    run_cmd pretorin login

    echo -e "  ${BOLD}Confirming identity:${RESET}"
    run_cmd pretorin whoami
fi

# ── Section 1: Browse Frameworks ─────────────────────────────────────────────

pause "Section 1: Browse compliance frameworks"

echo -e "  ${BOLD}List all available frameworks:${RESET}"
run_cmd pretorin frameworks list

pause "Drill into FedRAMP Moderate"

echo -e "  ${BOLD}Get details for FedRAMP Moderate:${RESET}"
run_cmd pretorin frameworks get fedramp-moderate

echo -e "  ${BOLD}List control families:${RESET}"
run_cmd pretorin frameworks families fedramp-moderate

pause "Explore individual controls"

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

# Show which systems have fedramp-moderate before the picker
FEDRAMP_SYSTEMS=$(pretorin --json context list 2>/dev/null | python3 -c "
import sys, json
try:
    rows = json.load(sys.stdin)
    names = sorted(set(r['system_name'] for r in rows if r.get('framework_id') == 'fedramp-moderate'))
    if names:
        for n in names:
            print(n)
except Exception:
    pass
" 2>/dev/null || echo "")

if [[ -n "$FEDRAMP_SYSTEMS" ]]; then
    echo -e "  ${BOLD}Systems with fedramp-moderate attached:${RESET}"
    while IFS= read -r sysname; do
        echo -e "    ✓ ${sysname}"
    done <<< "$FEDRAMP_SYSTEMS"
    echo ""
else
    echo -e "  ${GOLD}⚠ No systems with fedramp-moderate detected.${RESET}"
    echo -e "  ${DIM}Attach fedramp-moderate to a system at https://platform.pretorin.com before continuing.${RESET}"
    echo ""
fi

echo -e "  ${BOLD}Select your active system (interactive picker):${RESET}"
echo -e "  ${DIM}Pick one of the fedramp-moderate systems listed above.${RESET}"
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
CONTEXT_JSON=$(pretorin --json context show 2>/dev/null || echo "{}")

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

SECTION3_OK=true

echo -e "  ${BOLD}Create a local evidence file for AC-02:${RESET}"
if ! run_cmd pretorin evidence create ac-02 fedramp-moderate \
    -d "- Role-based access control audit completed for demo walkthrough\n- All users verified against approved role matrix" \
    -n "Demo RBAC Evidence"; then
    echo -e "  ${GOLD}⚠ Evidence creation failed — skipping rest of Section 3.${RESET}"
    SECTION3_OK=false
fi

if $SECTION3_OK; then
    echo -e "  ${BOLD}List local evidence:${RESET}"
    run_cmd pretorin evidence list || true

    pause "Push evidence to the platform"

    echo -e "  ${BOLD}Push evidence to the platform:${RESET}"
    run_cmd pretorin evidence push || true
fi

# ── Section 4: Narrative Workflow ────────────────────────────────────────────

pause "Section 4: Create and push narratives"

DEMO_NARRATIVES_DIR="./narratives"

SECTION4_OK=true

NARRATIVE_CONTENT='- **Account Creation**: Accounts are provisioned automatically when HR completes onboarding. Each account is assigned a role from the approved role matrix.
- **Periodic Review**: Quarterly access reviews are conducted by system owners.
- **Account Termination**: Accounts are disabled within 24 hours of separation notification.

```yaml
# IdP provisioning config
auto_provision: true
role_assignment: matrix-based
review_cadence: quarterly
termination_sla: 24h
```

[IdP Documentation](https://docs.example.com/idp)'

echo -e "  ${BOLD}Create a local narrative for AC-02:${RESET}"
if ! run_cmd pretorin narrative create ac-02 fedramp-moderate \
    -c "$NARRATIVE_CONTENT" \
    -n "ac-02-account-management"; then
    echo -e "  ${GOLD}⚠ Narrative creation failed — skipping rest of Section 4.${RESET}"
    SECTION4_OK=false
fi

if $SECTION4_OK; then
    echo -e "  ${BOLD}List local narratives:${RESET}"
    run_cmd pretorin narrative list || true

    pause "Push narratives to the platform"

    echo -e "  ${BOLD}Push narratives to the platform:${RESET}"
    run_cmd pretorin narrative push || true
fi

# ── Section 5: Notes Workflow ────────────────────────────────────────────────

pause "Section 5: Create and push notes"

DEMO_NOTES_DIR="./notes"

SECTION5_OK=true

echo -e "  ${BOLD}Create a local note for AC-02:${RESET}"
if ! run_cmd pretorin notes create ac-02 fedramp-moderate \
    -c "Gap: Missing SSO evidence. Manual next step: collect IdP configuration screenshots from Okta admin console." \
    -n "sso-evidence-gap"; then
    echo -e "  ${GOLD}⚠ Note creation failed — skipping rest of Section 5.${RESET}"
    SECTION5_OK=false
fi

if $SECTION5_OK; then
    echo -e "  ${BOLD}List local notes:${RESET}"
    run_cmd pretorin notes list --local || true

    pause "Push notes to the platform"

    echo -e "  ${BOLD}Push notes to the platform:${RESET}"
    run_cmd pretorin notes push || true
fi

# ── Section 6: Monitoring ────────────────────────────────────────────────────

pause "Section 6: Push a monitoring event"

echo -e "  ${BOLD}Push an access-review event:${RESET}"
run_cmd pretorin monitoring push \
    -t "Demo: Access review completed" \
    --severity info \
    --control ac-02 \
    --event-type access_review || true

# ── Section 7: Agent Skills (informational) ──────────────────────────────────

pause "Section 7: Agent skills (informational)"

echo -e "  ${BOLD}List available agent skills:${RESET}"
run_cmd pretorin agent skills || true

echo ""
echo -e "  ${DIM}The agent can run compliance tasks using an LLM backend.${RESET}"
echo -e "  ${DIM}Example (requires pretorin login or OPENAI_API_KEY):${RESET}"
echo ""
echo -e "  ${DIM}  \$ pretorin agent run --skill gap-analysis${RESET}"
echo ""
echo -e "  ${DIM}Skills include: gap-analysis, narrative-generation,${RESET}"
echo -e "  ${DIM}evidence-collection, security-review.${RESET}"

# ── Section 8: MCP Integration (informational) ───────────────────────────────

pause "Section 8: MCP integration (informational)"

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

# ── Section 9: Summary ───────────────────────────────────────────────────────

pause "Section 9: Summary"

echo -e "  ${GOLD}${BOLD}What we covered:${RESET}"
echo ""
echo -e "    1. ${BOLD}Authentication${RESET}     — login, whoami"
echo -e "    2. ${BOLD}Frameworks${RESET}         — list, get, families, controls, control detail"
echo -e "    3. ${BOLD}System context${RESET}     — list, set, show"
echo -e "    4. ${BOLD}Evidence${RESET}           — create, list, push"
echo -e "    5. ${BOLD}Narratives${RESET}         — create, list, push (local-first workflow)"
echo -e "    6. ${BOLD}Notes${RESET}              — create, list --local, push (local-first workflow)"
echo -e "    7. ${BOLD}Monitoring${RESET}         — push events (access reviews, scans, etc.)"
echo -e "    8. ${BOLD}Agent skills${RESET}       — gap-analysis, narrative-generation, and more"
echo -e "    9. ${BOLD}MCP integration${RESET}    — plug into Claude Code or any MCP-aware agent"
echo ""
echo -e "  ${ORANGE}Docs:${RESET}      https://docs.pretorin.com"
echo -e "  ${ORANGE}Platform:${RESET}  https://platform.pretorin.com"
echo -e "  ${ORANGE}Support:${RESET}   support@pretorin.com"
echo ""
echo -e "  ${GOLD}${BOLD}Thanks for trying Pretorin!${RESET}"
echo ""
