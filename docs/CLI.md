# CLI Reference

Comprehensive guide to the Pretorin CLI. For MCP server documentation, see [MCP.md](MCP.md).

## Getting Started

### Install

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
│ Frameworks Available: 8                                                      │
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

Total: 8 framework(s)
```

The **ID** column is what you'll use in all other commands.

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

### Show Current Context

```bash
$ pretorin context show
╭──────────────────────── Active Context ─────────────────────────╮
│ System: My Application                                          │
│ Framework: NIST SP 800-53 Rev 5                                │
│ Progress: 42% (136/324 implemented, 45 in progress)            │
╰─────────────────────────────────────────────────────────────────╯
```

### Clear Context

```bash
pretorin context clear
```

## Evidence Commands

The `evidence` command group manages local evidence files and syncs them to the platform.

### Create Local Evidence

```bash
pretorin evidence create --control-id ac-02 --framework-id fedramp-moderate \
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

Pushes all draft evidence files to the platform. Requires an active system context (`pretorin context set`).

## Narrative Commands

The `narrative` command group pushes implementation narratives to the platform.

### Push a Narrative File

```bash
pretorin narrative push ac-02 fedramp-moderate "My System" narrative-ac02.md
```

Reads a markdown/text file and submits it as the implementation narrative for a control. To generate narratives with AI, use the agent:

```bash
pretorin agent run --skill narrative-generation "Generate narrative for AC-02"
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

The `agent` command group runs autonomous compliance tasks using the Codex agent runtime. The agent has access to all Pretorin MCP tools and can perform multi-step compliance workflows.

### Run a Compliance Task

```bash
# Free-form task
pretorin agent run "Assess AC-2 implementation gaps for my system"

# Use a predefined skill
pretorin agent run --skill gap-analysis
pretorin agent run --skill narrative-generation "Generate narratives for all AC controls"
pretorin agent run --skill evidence-collection
pretorin agent run --skill security-review
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
pretorin agent mcp-add <name> --command <cmd> --args <args>
pretorin agent mcp-remove <name>
```

## Review Commands

The `review` command group helps you review local code against framework controls.

### Run a Review

```bash
# Uses active context for system/framework
pretorin review run --control-id ac-02 --path ./src

# Explicit system/framework override
pretorin review run --control-id ac-02 --framework-id nist-800-53-r5 --path ./src
```

If a system context is set, narratives and evidence are pushed to the platform. Otherwise, they're saved locally to `narratives/` and `evidence/` directories.

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
| `PRETORIN_API_BASE_URL` | Custom API URL (default: `https://platform.pretorin.com/api/v1/public`) |

## Utilities

### Version

```bash
$ pretorin version
pretorin version 0.1.0
```

### Update

Check for and install the latest version:

```bash
pretorin update
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
| `pretorin context list` | List systems and frameworks with progress |
| `pretorin context set` | Set active system/framework context |
| `pretorin context show` | Display current active context |
| `pretorin context clear` | Clear active context |
| `pretorin evidence create` | Create a local evidence file |
| `pretorin evidence list` | List local evidence files |
| `pretorin evidence push` | Push local evidence to the platform |
| `pretorin narrative push <ctrl> <fw> <sys> <file>` | Push a narrative file to the platform |
| `pretorin monitoring push` | Push a monitoring event to a system |
| `pretorin agent run "<task>"` | Run a compliance task with the Codex agent |
| `pretorin agent run --skill <name>` | Run a predefined agent skill |
| `pretorin agent doctor` | Validate Codex runtime setup |
| `pretorin agent install` | Download the pinned Codex binary |
| `pretorin agent skills` | List available agent skills |
| `pretorin agent mcp-list` | List configured MCP servers |
| `pretorin agent mcp-add` | Add an MCP server configuration |
| `pretorin agent mcp-remove` | Remove an MCP server configuration |
| `pretorin review run` | Review code against a control |
| `pretorin review status` | Check implementation status for a control |
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |
| `pretorin harness init` | Initialize harness config |
| `pretorin harness doctor` | Validate harness setup |
| `pretorin harness run "<task>"` | Run task through harness backend |
