# CLI Reference

Comprehensive guide to the Pretorin CLI. For MCP server documentation, see [MCP.md](MCP.md).

## Getting Started

### Install

```bash
uv tool install pretorin
```

Alternative installs:

```bash
pip install pretorin
```

Or with [pipx](https://pipx.pypa.io/) for an isolated install:

```bash
pipx install pretorin
```

### Authenticate

Get your API key from [platform.pretorin.com](https://platform.pretorin.com/), then:

```bash
pretorin login
```

You'll be prompted to enter your API key. Credentials are stored in `~/.pretorin/config.json`.

### Verify Authentication

```bash
$ pretorin whoami
[°~°] Checking your session...
╭──────────────────────────────── Your Session ────────────────────────────────╮
│ Status: Authenticated                                                        │
│ API Key: 4MAS****...9v7o                                                     │
│ API URL: https://platform.pretorin.com/api/v1                                │
│ Frameworks Available: 30+                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Browsing Frameworks

### List All Frameworks

```bash
$ pretorin frameworks list
[°~°] Consulting the compliance archives...
                        Available Compliance Frameworks
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┓
┃ ID          ┃ Title       ┃ Version     ┃ Tier         ┃ Families ┃ Controls ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━┩
│ cmmc-l1     │ CMMC 2.0    │ 2.0         │ tier1_essen… │        6 │       17 │
│             │ Level 1     │             │              │          │          │
│ cmmc-l2     │ CMMC 2.0    │ 2.0         │ tier1_essen… │       14 │      110 │
│             │ Level 2     │             │              │          │          │
│ cmmc-l3     │ CMMC 2.0    │ 2.0         │ tier1_essen… │       10 │       24 │
│             │ Level 3     │             │              │          │          │
│ fedramp-hi… │ FedRAMP Rev │ fedramp2.1… │ tier1_essen… │       18 │      191 │
│             │ 5 High      │             │              │          │          │
│ fedramp-low │ FedRAMP Rev │ fedramp2.1… │ tier1_essen… │       18 │      135 │
│             │ 5 Low       │             │              │          │          │
│ fedramp-mo… │ FedRAMP Rev │ fedramp2.1… │ tier1_essen… │       18 │      181 │
│             │ 5 Moderate  │             │              │          │          │
│ nist-800-1… │ NIST SP     │ 1.0.0       │ tier1_essen… │       17 │      130 │
│             │ 800-171     │             │              │          │          │
│             │ Revision 3  │             │              │          │          │
│ nist-800-5… │ NIST SP     │ 5.2.0       │ tier1_essen… │       20 │      324 │
│             │ 800-53 Rev  │             │              │          │          │
│             │ 5           │             │              │          │          │
└─────────────┴─────────────┴─────────────┴──────────────┴──────────┴──────────┘

Total: 30+ framework(s)
```

The **ID** column is what you'll use in all other commands.

The exact total and available framework set can vary as the platform catalog expands. Use `pretorin frameworks list` to see the live catalog available to your account.

### Get Framework Details

```bash
$ pretorin frameworks get fedramp-moderate
[°~°] Gathering framework details...
╭───────────────── Framework: FedRAMP Rev 5 Moderate Baseline ─────────────────╮
│ ID: fedramp-moderate                                                         │
│ Title: FedRAMP Rev 5 Moderate Baseline                                       │
│ Version: fedramp2.1.0-oscal1.0.4                                             │
│ OSCAL Version: 1.0.4                                                         │
│ Tier: tier1_essential                                                        │
│ Category: government                                                         │
│ Published: 2024-09-24T02:24:00Z                                              │
│ Last Modified: -                                                             │
│                                                                              │
│ Description:                                                                 │
│ No description available.                                                    │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## Control Families

### List Families for a Framework

```bash
$ pretorin frameworks families nist-800-53-r5
[°~°] Gathering control families...
                       Control Families - nist-800-53-r5
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ ID                          ┃ Title                       ┃ Class ┃ Controls ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ access-control              │ Access Control              │ ac    │       25 │
│ audit-and-accountability    │ Audit and Accountability    │ au    │       16 │
│ awareness-and-training      │ Awareness and Training      │ at    │        6 │
│ configuration-management    │ Configuration Management    │ cm    │       14 │
│ contingency-planning        │ Contingency Planning        │ cp    │       13 │
│ identification-and-authent… │ Identification and          │ ia    │       13 │
│                             │ Authentication              │       │          │
│ incident-response           │ Incident Response           │ ir    │       10 │
│ maintenance                 │ Maintenance                 │ ma    │        7 │
│ media-protection            │ Media Protection            │ mp    │        8 │
│ ...                         │                             │       │          │
└─────────────────────────────┴─────────────────────────────┴───────┴──────────┘

Total: 20 family(ies)
```

> **Important:** Family IDs are slugs like `access-control`, not short codes like `ac`. The short code is shown in the **Class** column for reference, but commands require the full slug ID.

### CMMC Family IDs

CMMC frameworks use level-specific family slugs:

```bash
$ pretorin frameworks families cmmc-l2
[°~°] Gathering control families...
                           Control Families - cmmc-l2
┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━┓
┃ ID                          ┃ Title                       ┃ Class ┃ Controls ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━┩
│ access-control-level-2      │ Access Control (Level 2)    │ AC-L2 │       22 │
│ audit-and-accountability-l… │ Audit and Accountability    │ AU-L2 │        9 │
│                             │ (Level 2)                   │       │          │
│ awareness-and-training-lev… │ Awareness and Training      │ AT-L2 │        3 │
│                             │ (Level 2)                   │       │          │
│ ...                         │                             │       │          │
└─────────────────────────────┴─────────────────────────────┴───────┴──────────┘

Total: 14 family(ies)
```

Note: CMMC family IDs include the level suffix, e.g., `access-control-level-2` instead of `access-control`.

## Controls

### List Controls for a Framework

```bash
$ pretorin frameworks controls nist-800-53-r5 --family access-control --limit 10
[°~°] Searching for controls...
   Controls - nist-800-53-r5 (Family: access-control)
┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ ID    ┃ Title                        ┃ Family         ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ ac-01 │ Policy and Procedures        │ ACCESS-CONTROL │
│ ac-02 │ Account Management           │ ACCESS-CONTROL │
│ ac-03 │ Access Enforcement           │ ACCESS-CONTROL │
│ ac-04 │ Information Flow Enforcement │ ACCESS-CONTROL │
│ ac-05 │ Separation of Duties         │ ACCESS-CONTROL │
│ ac-06 │ Least Privilege              │ ACCESS-CONTROL │
│ ac-07 │ Unsuccessful Logon Attempts  │ ACCESS-CONTROL │
│ ac-08 │ System Use Notification      │ ACCESS-CONTROL │
│ ac-09 │ Previous Logon Notification  │ ACCESS-CONTROL │
│ ac-10 │ Concurrent Session Control   │ ACCESS-CONTROL │
└───────┴──────────────────────────────┴────────────────┘

Showing 10 of 25 controls. Use --limit to see more.
```

Without `--family`, all controls for the framework are listed. Without `--limit`, all matching controls are shown.

> **Important:** Control IDs are zero-padded — use `ac-01`, not `ac-1`.

### CMMC Control IDs

CMMC uses a different control ID format:

```bash
$ pretorin frameworks controls cmmc-l2 --family access-control-level-2 --limit 5
[°~°] Searching for controls...
           Controls - cmmc-l2 (Family: access-control-level-2)
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID           ┃ Title                         ┃ Family                 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
│ AC.L2-3.1.1  │ Authorized Access Control     │ ACCESS-CONTROL-LEVEL-2 │
│ AC.L2-3.1.10 │ Session Lock                  │ ACCESS-CONTROL-LEVEL-2 │
│ AC.L2-3.1.11 │ Session Termination           │ ACCESS-CONTROL-LEVEL-2 │
│ AC.L2-3.1.12 │ Control Remote Access         │ ACCESS-CONTROL-LEVEL-2 │
│ AC.L2-3.1.13 │ Remote Access Confidentiality │ ACCESS-CONTROL-LEVEL-2 │
└──────────────┴───────────────────────────────┴────────────────────────┘

Showing 5 of 22 controls. Use --limit to see more.
```

## Control Details

### Get a Control

```bash
$ pretorin frameworks control nist-800-53-r5 ac-02
[°~°] Looking up control details...
╭─────────────────────────────── Control: AC-02 ───────────────────────────────╮
│ ID: ac-02                                                                    │
│ Title: Account Management                                                    │
│ Class: SP800-53                                                              │
│ Type: organizational                                                         │
│                                                                              │
│ AI Guidance: Available                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯

Parameters:
  - ac-02_odp.01: prerequisites and criteria
  - ac-02_odp.02: attributes (as required)
  - ac-02_odp.03: personnel or roles
  - ac-02_odp.04: policy, procedures, prerequisites, and criteria
  - ac-02_odp.05: personnel or roles
```

### Get Full Control Details with References

Add `--references` to include the statement text, guidance, and related controls:

```bash
$ pretorin frameworks control nist-800-53-r5 ac-02 --references
[°~°] Looking up control details...
╭─────────────────────────────── Control: AC-02 ───────────────────────────────╮
│ ID: ac-02                                                                    │
│ Title: Account Management                                                    │
│ Class: SP800-53                                                              │
│ Type: organizational                                                         │
│                                                                              │
│ AI Guidance: Available                                                       │
╰──────────────────────────────────────────────────────────────────────────────╯

Statement:
╭──────────────────────────────────────────────────────────────────────────────╮
│ a.. Define and document the types of accounts allowed and specifically       │
│ prohibited for use within the system;                                        │
│ b.. Assign account managers;                                                 │
│ c.. Require {{ insert: param, ac-02_odp.01 }} for group and role membership; │
│ ...                                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯

Guidance:
╭──────────────────────────────────────────────────────────────────────────────╮
│ Examples of system account types include individual, shared, group, system,  │
│ guest, anonymous, emergency, developer, temporary, and service. ...          │
╰──────────────────────────────────────────────────────────────────────────────╯

Related Controls:
  AC-01, AC-03, AC-04, AC-05, AC-06, AC-07, AC-08, AC-09, AC-10, AC-11

Parameters:
  - ac-02_odp.01: prerequisites and criteria
  - ac-02_odp.02: attributes (as required)
  - ac-02_odp.03: personnel or roles
  - ac-02_odp.04: policy, procedures, prerequisites, and criteria
  - ac-02_odp.05: personnel or roles
```

### Common Mistakes

Using the wrong ID format will produce an error:

```bash
$ pretorin frameworks control nist-800-53-r5 ac-1
[°~°] Looking up control details...
[°︵°] Couldn't find control ac-1 in nist-800-53-r5
Try pretorin frameworks controls nist-800-53-r5 to see available controls.
```

Use zero-padded IDs: `ac-01`, not `ac-1`.

## Document Requirements

```bash
$ pretorin frameworks documents fedramp-moderate
[°~°] Gathering document requirements...

Document Requirements for FedRAMP Rev 5 Moderate Baseline

Total: 0 document requirement(s)
```

> **Note:** Document requirements may not be populated for all frameworks yet. Check back as more data is added to the platform.

## Context Management

The `context` command group lets you set your active system and framework, similar to `kubectl config use-context`. All system-scoped commands use this context by default.

### List Available Systems

```bash
$ pretorin context list
[°~°] Fetching your systems...
                              Your Systems
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ System           ┃ Framework ID       ┃ Progress % ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ My Application   │ nist-800-53-r5     │        42% │ in_progress │
│ My Application   │ fedramp-moderate   │        28% │ in_progress │
│ Internal Tool    │ cmmc-l2            │        75% │ implemented │
└──────────────────┴────────────────────┴────────────┴───────────┘
```

### Set Active Context

```bash
# Interactive (prompts for selection)
pretorin context set

# Explicit
pretorin context set --system "My Application" --framework nist-800-53-r5
```

Pretorin stores the canonical system ID for stability and also caches the last known system name for display. If you switch API keys or platform endpoints with `pretorin login`, the stored active context is cleared automatically so old scope does not leak into the new environment.

Platform-backed compliance execution is single-scope. Commands that create or update evidence, notes, monitoring events, narratives, or control state operate within exactly one active `system + framework` pair. If you need to work across `fedramp-low` and `fedramp-moderate`, run them separately.

### Show Current Context

```bash
$ pretorin context show
╭──────────────────────── Active Context ─────────────────────────╮
│ System: My Application (sys-1234...)                           │
│ Framework: nist-800-53-r5                                      │
│ Progress: 42%                                                  │
│ Status: in_progress                                            │
╰─────────────────────────────────────────────────────────────────╯

# Compact summary for shell use
pretorin context show --quiet

# Exit non-zero if stored context is missing, stale, or cannot be verified
pretorin context show --quiet --check
```

`context show` validates stored scope against the platform when credentials are available and reports invalid or unverified context explicitly instead of silently showing deleted systems as active.

### Clear Context

```bash
pretorin context clear
```

### Verify Context

```bash
pretorin context verify
pretorin context verify --ttl 7200 --quiet
```

Verifies the active context with source attestation. The `--ttl` option sets the verification TTL in seconds (default: 3600).

### Source Manifest

```bash
pretorin context manifest
pretorin context manifest --quiet
```

Shows the resolved source manifest and evaluates it against detected sources.

## Control Commands

The `control` command group manages control implementation status and context.

### Update Control Status

```bash
pretorin control status ac-02 implemented
pretorin control status sc-07 in_progress --system "My System" --framework-id fedramp-moderate
```

Valid statuses: `implemented`, `partially_implemented`, `planned`, `in_progress`, `ready_to_approve`, `not_started`, `not_applicable`, `inherited`

### Get Control Context

```bash
pretorin control context ac-02
pretorin control context ac-02 --framework-id nist-800-53-r5 --system "My System"
```

Returns rich control context with AI guidance for implementation.

## Evidence Commands

The `evidence` command group manages local evidence files and syncs them to the platform.

### Create Local Evidence

```bash
pretorin evidence create ac-02 fedramp-moderate \
  --name "RBAC Configuration" --description "Role-based access control in Azure AD"
```

Creates a markdown file under `evidence/<framework>/<control>/` with YAML frontmatter.

### List Local Evidence

```bash
pretorin evidence list
pretorin evidence list --framework fedramp-moderate
```

### Push Evidence to Platform

```bash
pretorin evidence push
```

Pushes local evidence files to the platform using find-or-create upsert logic.
Requires an active single scope from `pretorin context set` unless both `--system` and `--framework` are provided via `evidence upsert`.

### Link Evidence to a Control

```bash
pretorin evidence link abc123 ac-02
pretorin evidence link abc123 sc-07 --framework-id fedramp-moderate
```

Links an existing evidence item to a control on the platform.

### Search Platform Evidence

```bash
pretorin evidence search --control-id ac-02 --framework-id fedramp-moderate
pretorin evidence search --system "My Application" --framework-id fedramp-moderate --limit 100
```

### Upsert Evidence

```bash
pretorin evidence upsert ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role mapping in IdP" \
  --type configuration
```

Finds and reuses exact matching evidence within the active system/framework scope by default, otherwise creates a new item, then ensures control linking.
Evidence descriptions must be auditor-ready markdown with no headings and at least one rich element (code block, table, list, or link). Markdown images are currently disallowed.
When `control_id` is involved, `framework_id` is required and the CLI validates that the framework belongs to the selected system before pushing.

### Delete Evidence

```bash
pretorin evidence delete ev-abc123
pretorin evidence delete ev-abc123 --yes   # skip confirmation
```

Permanently removes an evidence item and its associated embeddings. System-scoped, requires WRITE access.

## Narrative Commands

The `narrative` command group manages local narrative files and syncs them to the platform.

### Create Local Narrative

```bash
pretorin narrative create ac-02 fedramp-moderate \
  --content "This control is implemented through centralized account management..."
pretorin narrative create ac-02 fedramp-moderate --content "..." --ai-generated
```

Creates a local narrative file with YAML frontmatter.

### List Local Narratives

```bash
pretorin narrative list
pretorin narrative list --framework fedramp-moderate
```

### Get Current Narrative

```bash
pretorin narrative get ac-02 fedramp-moderate --system "My System"
```

### Push All Local Narratives

```bash
pretorin narrative push
pretorin narrative push --dry-run
```

### Push a Single Narrative File

```bash
pretorin narrative push-file ac-02 fedramp-moderate "My System" narrative-ac02.md
```

Reads a markdown/text file and submits it as the implementation narrative for a control. To generate narratives with AI, use the agent:
Narratives must be auditor-ready markdown with no headings, at least two rich elements, and at least one structural element (code block, table, or list).

```bash
pretorin agent run --skill narrative-generation "Generate narrative for AC-02"
```

## Notes Commands

The `notes` command group manages control implementation notes locally and on the platform.

### Create Local Note

```bash
pretorin notes create ac-02 fedramp-moderate --content "Gap: Missing SSO evidence ..."
```

Creates a local note file with YAML frontmatter.

### List Notes

```bash
# Platform notes
pretorin notes list ac-02 fedramp-moderate --system "My System"

# Local note files
pretorin notes list --local
pretorin notes list --local --framework fedramp-moderate
```

### Add Note (Direct to Platform)

```bash
pretorin notes add ac-02 fedramp-moderate \
  --content "Gap: Missing SSO evidence ..."
```

### Push Local Notes

```bash
pretorin notes push
pretorin notes push --dry-run
```

### Resolve or Reopen a Note

```bash
pretorin notes resolve ac-02 fedramp-moderate note-abc123
pretorin notes resolve ac-02 fedramp-moderate note-abc123 --reopen
pretorin notes resolve ac-02 fedramp-moderate note-abc123 --content "Updated content"
```

## Monitoring Commands

### Push a Monitoring Event

```bash
pretorin monitoring push --system "My System" --title "Quarterly Access Review" \
  --event-type access_review --severity info
```

Valid event types: `security_scan`, `configuration_change`, `access_review`, `compliance_check`
Valid severities: `critical`, `high`, `medium`, `low`, `info`

## Agent Commands

The `agent` command group runs autonomous compliance tasks using the Codex agent runtime. This is the hosted model mode (`pretorin agent run`).

If you already use another AI agent, use the MCP mode instead (`pretorin mcp-serve`) and connect Pretorin tools to that agent.

### Run a Compliance Task

```bash
# Free-form task
pretorin agent run "Assess AC-02 implementation gaps for my system"

# Use a predefined skill
pretorin agent run "Analyze my system compliance gaps" --skill gap-analysis
pretorin agent run --skill narrative-generation "Generate narratives for all AC controls"
pretorin agent run "Collect evidence for AC-02 in this repo" --skill evidence-collection
pretorin agent run "Review this codebase for AC-02 coverage" --skill security-review
```

### Available Skills

| Skill | Description |
|-------|-------------|
| `gap-analysis` | Analyze system compliance gaps across frameworks |
| `narrative-generation` | Generate implementation narratives for controls |
| `evidence-collection` | Collect and map evidence from codebase to controls |
| `security-review` | Review codebase for security controls and compliance posture |

### Agent Setup

```bash
# Check setup
pretorin agent doctor

# Install the Codex binary
pretorin agent install

# Manage MCP servers available to the agent
pretorin agent mcp-list
pretorin agent mcp-add <name> stdio <command> --arg <arg>
pretorin agent mcp-remove <name>
```

### Hosted Model Setup (Pretorin Endpoint)

Use this setup when you want `pretorin agent run` to call Pretorin-hosted `/v1` model endpoints.

```bash
# 1) Login with your Pretorin API key
pretorin login

# 2) Optional: custom/self-hosted Pretorin model endpoint
pretorin config set model_api_base_url https://platform.pretorin.com/api/v1/public/model

# 3) Validate runtime
pretorin agent doctor
pretorin agent install

# 4) Run a task
pretorin agent run "Assess AC-02 implementation gaps for my system"
```

Model key precedence for the agent runtime is:
- `OPENAI_API_KEY`
- `config.api_key` (from `pretorin login`)
- `config.openai_api_key`

If `OPENAI_API_KEY` is set in your shell, it overrides the stored Pretorin login key.

## Review Commands

The `review` command group helps you review local code against framework controls.

### Run a Review

```bash
# Uses active context for system/framework
pretorin review run --control-id ac-02 --path ./src

# Explicit system/framework override
pretorin review run --control-id ac-02 --framework-id nist-800-53-r5 --path ./src
```

`pretorin review run` does not push narratives or evidence. In normal mode it fetches control requirements and current implementation details for comparison. In `--local` mode it writes a markdown review artifact under `.pretorin/reviews/` or the path you pass with `--output-dir`.

### Check Implementation Status

```bash
$ pretorin review status --control-id ac-02
╭─────────────────── Control AC-02 Status ───────────────────────╮
│ Status: in_progress                                             │
│ Evidence items: 3                                               │
│ Narrative: This control is implemented through centralized     │
│ account management using Azure AD...                           │
╰─────────────────────────────────────────────────────────────────╯
```

## Policy Commands

The `policy` command group manages organization policy questionnaire workflows.

### List Policies

```bash
pretorin policy list
```

### Show Policy State

```bash
pretorin policy show --policy "access-control-policy"
```

Shows persisted policy questionnaire state and saved review findings. The `--policy` option accepts an ID, exact template ID, or unique exact name.

## Scope Commands

The `scope` command group manages scope questionnaire workflows.

### Show Scope State

```bash
pretorin scope show
pretorin scope show --system "My System" --framework-id fedramp-moderate
```

Shows persisted scope questionnaire state and saved review findings.

### Populate Scope from Workspace

```bash
pretorin scope populate --path ./src
pretorin scope populate --system "My System" --framework-id fedramp-moderate --apply
```

Drafts stateful scope questionnaire updates from the current workspace. Use `--apply` to persist changed answers back to the platform.

## Skill Commands

The `skill` command group installs the Pretorin skill for AI coding agents.

### Install Skill

```bash
pretorin skill install
pretorin skill install --agent claude --agent codex
pretorin skill install --path ./custom-skills --force
```

Installs the Pretorin compliance skill for AI agents (Claude Code, Codex). Omit `--agent` to install for all supported agents.

## Configuration

### List Configuration

```bash
$ pretorin config list
          Pretorin Configuration
┏━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┓
┃ Key     ┃ Value           ┃ Source      ┃
┡━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━┩
│ api_key │ 4MAS****...9v7o │ config file │
└─────────┴─────────────────┴─────────────┘

Config file: /home/user/.pretorin/config.json
```

### Get / Set / Path

```bash
# Get a specific config value
pretorin config get api_key

# Set a config value
pretorin config set api_base_url https://custom-api.example.com/api/v1

# Show config file location
$ pretorin config path
/home/user/.pretorin/config.json
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key (overrides stored config) |
| `PRETORIN_PLATFORM_API_BASE_URL` | Platform REST API URL (default: `https://platform.pretorin.com/api/v1/public`) |
| `PRETORIN_API_BASE_URL` | Backward-compatible alias for `PRETORIN_PLATFORM_API_BASE_URL` |
| `PRETORIN_MODEL_API_BASE_URL` | Model API URL for agent/harness flows (default: `https://platform.pretorin.com/api/v1/public/model`) |
| `OPENAI_API_KEY` | Optional model key override for the agent runtime |

## Utilities

### Version

```bash
$ pretorin version
pretorin version 0.8.1
```

### Update

Check for and install the latest version:

```bash
pretorin update
```

Passive update notifications are shown only for interactive runs. To disable them:

```bash
export PRETORIN_DISABLE_UPDATE_CHECK=1
# or
pretorin config set disable_update_check true
```

The CLI also checks for updates automatically on startup and notifies you when a new version is available.

### Logout

```bash
pretorin logout
```

## ID Format Reference

Different frameworks use different ID conventions. Always use `pretorin frameworks families <id>` and `pretorin frameworks controls <id>` to discover the correct IDs.

### NIST 800-53 / FedRAMP

| Type | Format | Example |
|------|--------|---------|
| Framework ID | lowercase slug | `nist-800-53-r5`, `fedramp-moderate` |
| Family ID | lowercase slug | `access-control`, `audit-and-accountability` |
| Control ID | zero-padded | `ac-01`, `ac-02`, `au-06` |

### CMMC

| Type | Format | Example |
|------|--------|---------|
| Framework ID | lowercase slug | `cmmc-l1`, `cmmc-l2`, `cmmc-l3` |
| Family ID | slug with level suffix | `access-control-level-2`, `incident-response-level-2` |
| Control ID | dotted notation | `AC.L2-3.1.1`, `SC.L2-3.13.1` |

### NIST 800-171

| Type | Format | Example |
|------|--------|---------|
| Framework ID | lowercase slug | `nist-800-171-r3` |
| Family ID | lowercase slug | `access-control`, `audit-and-accountability` |
| Control ID | dotted notation | `03.01.01`, `03.01.02` |

## Available Frameworks

| ID | Title | Families | Controls |
|----|-------|----------|----------|
| `cmmc-l1` | CMMC 2.0 Level 1 (Foundational) | 6 | 17 |
| `cmmc-l2` | CMMC 2.0 Level 2 (Advanced) | 14 | 110 |
| `cmmc-l3` | CMMC 2.0 Level 3 (Expert) | 10 | 24 |
| `fedramp-high` | FedRAMP Rev 5 High Baseline | 18 | 191 |
| `fedramp-low` | FedRAMP Rev 5 Low Baseline | 18 | 135 |
| `fedramp-moderate` | FedRAMP Rev 5 Moderate Baseline | 18 | 181 |
| `nist-800-171-r3` | NIST SP 800-171 Revision 3 | 17 | 130 |
| `nist-800-53-r5` | NIST SP 800-53 Rev 5 | 20 | 324 |

## Campaign Commands

The `campaign` command group runs bulk compliance operations across multiple controls, policies, or scope questions.

### Control Campaigns

```bash
# Draft new narratives for the Access Control family
pretorin campaign controls --mode initial --family AC \
  --system "My System" --framework-id fedramp-moderate

# Fix controls flagged by platform notes
pretorin campaign controls --mode notes-fix --family AC

# Fix controls flagged by family review
pretorin campaign controls --mode review-fix --family AC --review-job <job-id>
```

### Policy Campaigns

```bash
pretorin campaign policy --mode answer --all-incomplete
```

### Scope Campaigns

```bash
pretorin campaign scope --mode answer \
  --system "My System" --framework-id fedramp-moderate
```

### Campaign Status

```bash
pretorin campaign status --checkpoint .pretorin/campaign-checkpoint.json
```

Campaign modes: `initial` (new drafts), `notes-fix` (fix platform notes), `review-fix` (fix review findings), `answer` (policy/scope questions).

## Vendor Commands

The `vendor` command group manages vendor entities and their evidence documents.

```bash
pretorin vendor list
pretorin vendor create "AWS" --type csp --description "Cloud provider"
pretorin vendor get <vendor_id>
pretorin vendor update <vendor_id> --name "AWS GovCloud"
pretorin vendor delete <vendor_id> --force
pretorin vendor upload-doc <vendor_id> ./soc2-report.pdf --name "SOC 2" --attestation-type third_party_attestation
pretorin vendor list-docs <vendor_id>
```

Vendor types: `csp`, `saas`, `managed_service`, `internal`

## STIG Commands

Browse STIG benchmarks and rules.

```bash
pretorin stig list --technology-area "Network"
pretorin stig show <stig_id>
pretorin stig rules <stig_id> --severity high
pretorin stig applicable --system "My System"
pretorin stig infer --system "My System"
```

## CCI Commands

Browse CCIs and the full traceability chain from NIST 800-53 controls to STIG rules.

```bash
pretorin cci list --control ac-2
pretorin cci show CCI-000015
pretorin cci chain ac-2 --system "My System"
```

## Scan Commands

Run STIG compliance scans using available scanner tools.

```bash
pretorin scan doctor                          # check installed scanners
pretorin scan manifest --system "My System"   # view test manifest
pretorin scan run --system "My System"        # execute scans
pretorin scan run --dry-run                   # preview without executing
pretorin scan results --control ac-2          # view CCI-level results
```

Supported scanners: OpenSCAP, InSpec, AWS Cloud Scanner, Azure Cloud Scanner, Manual.

## Complete Command Reference

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display authentication status |
| `pretorin version` | Show CLI version |
| `pretorin update` | Update to latest version |
| `pretorin mcp-serve` | Start the MCP server |
| `pretorin frameworks list` | List all frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks controls <id>` | List controls (`--family`, `--limit`) |
| `pretorin frameworks control <fw> <ctrl>` | Get control details (`--references`) |
| `pretorin frameworks documents <id>` | Get document requirements |
| `pretorin frameworks family <fw> <family>` | Get control family details |
| `pretorin frameworks metadata <id>` | Get per-control framework metadata |
| `pretorin frameworks submit-artifact <file>` | Submit a compliance artifact JSON file |
| `pretorin context list` | List systems and frameworks with progress |
| `pretorin context set` | Set active system/framework context |
| `pretorin context show` | Display and validate current active context |
| `pretorin context clear` | Clear active context |
| `pretorin context verify` | Verify active context with source attestation |
| `pretorin context manifest` | Show resolved source manifest |
| `pretorin control status <ctrl> <status>` | Update control implementation status |
| `pretorin control context <ctrl>` | Get rich control context with AI guidance |
| `pretorin evidence create` | Create a local evidence file |
| `pretorin evidence list` | List local evidence files |
| `pretorin evidence push` | Push local evidence to the platform |
| `pretorin evidence link <eid> <ctrl>` | Link evidence to a control |
| `pretorin evidence search` | Search platform evidence |
| `pretorin evidence upsert <ctrl> <fw>` | Find-or-create evidence and link it |
| `pretorin evidence delete <eid>` | Delete an evidence item (`--yes`) |
| `pretorin narrative create` | Create a local narrative file |
| `pretorin narrative list` | List local narrative files |
| `pretorin narrative get <ctrl> <fw>` | Get current control narrative |
| `pretorin narrative push` | Push all local narratives to the platform |
| `pretorin narrative push-file <ctrl> <fw> <sys> <file>` | Push a single narrative file |
| `pretorin notes create` | Create a local note file |
| `pretorin notes list <ctrl> <fw>` | List control notes (`--local` for local files) |
| `pretorin notes add <ctrl> <fw> --content ...` | Add a note directly to the platform |
| `pretorin notes push` | Push local notes to the platform |
| `pretorin notes resolve <ctrl> <fw> <note_id>` | Resolve or reopen a control note (`--reopen`) |
| `pretorin monitoring push` | Push a monitoring event to a system |
| `pretorin policy list` | List org policies for questionnaire work |
| `pretorin policy show` | Show policy questionnaire state (`--policy`) |
| `pretorin scope show` | Show scope questionnaire state |
| `pretorin scope populate` | Draft scope updates from workspace (`--apply`) |
| `pretorin campaign controls` | Run bulk control campaign (`--mode`, `--family`, `--apply`) |
| `pretorin campaign policy` | Run bulk policy campaign (`--mode`, `--all-incomplete`) |
| `pretorin campaign scope` | Run bulk scope campaign (`--mode`) |
| `pretorin campaign status` | Check campaign progress (`--checkpoint`) |
| `pretorin vendor list` | List all vendors |
| `pretorin vendor create <name>` | Create a vendor (`--type`, `--description`) |
| `pretorin vendor get <id>` | Get vendor details |
| `pretorin vendor update <id>` | Update vendor fields |
| `pretorin vendor delete <id>` | Delete a vendor (`--force`) |
| `pretorin vendor upload-doc <id> <file>` | Upload vendor evidence document |
| `pretorin vendor list-docs <id>` | List vendor documents |
| `pretorin stig list` | List STIG benchmarks (`--technology-area`, `--product`) |
| `pretorin stig show <id>` | Show STIG benchmark detail |
| `pretorin stig rules <id>` | List STIG rules (`--severity`, `--cci`) |
| `pretorin stig applicable` | Show applicable STIGs for active system |
| `pretorin stig infer` | AI-infer applicable STIGs |
| `pretorin cci list` | List CCIs (`--control`, `--status`) |
| `pretorin cci show <id>` | Show CCI detail |
| `pretorin cci chain <ctrl>` | Full traceability chain (`--system`) |
| `pretorin scan doctor` | Check installed scanner tools |
| `pretorin scan manifest` | Show test manifest (`--system`, `--stig`) |
| `pretorin scan run` | Run STIG scans (`--tool`, `--dry-run`) |
| `pretorin scan results` | View CCI-level results (`--control`) |
| `pretorin agent run "<task>"` | Run a compliance task with the Codex agent |
| `pretorin agent run --skill <name>` | Run a predefined agent skill |
| `pretorin agent doctor` | Validate Codex runtime setup |
| `pretorin agent install` | Download the pinned Codex binary |
| `pretorin agent version` | Show pinned Codex version and install status |
| `pretorin agent skills` | List available agent skills |
| `pretorin agent mcp-list` | List configured MCP servers |
| `pretorin agent mcp-add` | Add an MCP server configuration |
| `pretorin agent mcp-remove` | Remove an MCP server configuration |
| `pretorin review run` | Review code against a control |
| `pretorin review status` | Check implementation status for a control |
| `pretorin skill install` | Install Pretorin skill for AI agents (`--agent`) |
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |
| `pretorin harness init` | Deprecated: initialize harness config |
| `pretorin harness doctor` | Deprecated: validate harness setup |
| `pretorin harness run "<task>"` | Deprecated: run task through harness backend |
