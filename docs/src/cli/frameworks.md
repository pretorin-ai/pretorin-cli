# Framework Browsing

The `frameworks` command group lets you browse compliance frameworks, control families, and individual controls. These commands are read-only and available to all authenticated users.

## List All Frameworks

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
│ ...         │             │             │              │          │          │
└─────────────┴─────────────┴─────────────┴──────────────┴──────────┴──────────┘

Total: 30+ framework(s)
```

The **ID** column is what you use in all other commands.

The exact total and available framework set can vary as the platform catalog expands. Use `pretorin frameworks list` to see the live catalog available to your account.

## Get Framework Details

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
╰──────────────────────────────────────────────────────────────────────────────╯
```

## List Control Families

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
│ ...                         │                             │       │          │
└─────────────────────────────┴─────────────────────────────┴───────┴──────────┘
```

> **Important:** Family IDs are slugs like `access-control`, not short codes like `ac`. The short code is shown in the **Class** column for reference, but commands require the full slug ID.

### CMMC Family IDs

CMMC frameworks use level-specific family slugs:

```bash
$ pretorin frameworks families cmmc-l2
```

CMMC family IDs include the level suffix, e.g., `access-control-level-2` instead of `access-control`.

## Get Family Details

```bash
pretorin frameworks family nist-800-53-r5 access-control
```

## List Controls

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
│ ...   │                              │                │
└───────┴──────────────────────────────┴────────────────┘

Showing 10 of 25 controls. Use --limit to see more.
```

Without `--family`, all controls for the framework are listed. Without `--limit`, all matching controls are shown.

> **Important:** Control IDs are zero-padded — use `ac-01`, not `ac-1`. See [Control ID Formats](../frameworks/control-ids.md) for details.

## Get Control Details

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

### Brief Mode

By default, the full control is shown including statement, guidance, and references. Use `--brief` to show only the basic info panel:

```bash
$ pretorin frameworks control nist-800-53-r5 ac-02 --brief
```

The default (no flag) includes:
- **Statement** — the formal control requirement text
- **Guidance** — implementation guidance from the framework
- **Related Controls** — other controls that relate to this one

### Common Mistakes

Using the wrong ID format produces an error:

```bash
$ pretorin frameworks control nist-800-53-r5 ac-1
[°~°] Looking up control details...
[°︵°] Couldn't find control ac-1 in nist-800-53-r5
Try pretorin frameworks controls nist-800-53-r5 to see available controls.
```

Use zero-padded IDs: `ac-01`, not `ac-1`.

## Document Requirements

```bash
pretorin frameworks documents fedramp-moderate
```

Returns explicit and implicit document requirements for the framework.

## Framework Metadata

Get per-control metadata for a framework:

```bash
pretorin frameworks metadata nist-800-53-r5
```

## Submit Artifacts

Submit a compliance artifact JSON file:

```bash
pretorin frameworks submit-artifact artifact.json
```

See [Artifact Generation](../workflows/artifacts.md) for the artifact schema.

## JSON Output

All framework commands support JSON output for scripting and AI agents:

```bash
pretorin --json frameworks list
pretorin --json frameworks control nist-800-53-r5 ac-02
```
