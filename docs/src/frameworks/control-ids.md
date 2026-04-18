# Control ID Formats

Correct ID formatting is critical. The Pretorin API returns errors on malformed IDs. When unsure, discover IDs first with `pretorin frameworks families <id>` or `pretorin frameworks controls <id>`.

## NIST 800-53 Rev 5 / FedRAMP

**Framework IDs:** `nist-800-53-r5`, `fedramp-low`, `fedramp-moderate`, `fedramp-high`

### Family IDs

Family IDs are **lowercase slugs**, not short codes:

| Correct | Incorrect |
|---------|-----------|
| `access-control` | `ac` |
| `audit-and-accountability` | `au` |
| `identification-and-authentication` | `ia` |
| `system-and-communications-protection` | `sc` |
| `configuration-management` | `cm` |
| `incident-response` | `ir` |
| `risk-assessment` | `ra` |

### Control IDs

Control IDs are **zero-padded** with a hyphen:

| Correct | Incorrect |
|---------|-----------|
| `ac-01` | `ac-1`, `AC-1`, `ac1` |
| `ac-02` | `ac-2`, `AC-2`, `ac2` |
| `au-02` | `au-2`, `AU-2` |
| `sc-07` | `sc-7`, `SC-7` |

**Enhancement IDs** append a dot-suffix or parenthetical suffix:

| Format | Example |
|--------|---------|
| Dot notation | `ac-02.1` |
| Parenthetical | `ac-02(1)` |

## CMMC 2.0

**Framework IDs:** `cmmc-l1`, `cmmc-l2`, `cmmc-l3`

### Family IDs

CMMC family IDs include a **level suffix**:

| Correct | Incorrect |
|---------|-----------|
| `access-control-level-1` | `access-control`, `ac` |
| `access-control-level-2` | `access-control`, `ac-l2` |
| `incident-response-level-2` | `incident-response`, `ir` |
| `system-and-communications-protection-level-3` | `sc`, `sc-l3` |

### Control IDs

CMMC control IDs use **dotted notation with a level prefix** and are **case-sensitive**:

| Correct | Incorrect |
|---------|-----------|
| `AC.L2-3.1.1` | `ac-01`, `3.1.1` |
| `SC.L3-3.13.2` | `sc-07`, `3.13.2` |
| `AC.L1-3.1.22` | `ac.l1-3.1.22` |

Use uppercase for the family prefix (e.g., `AC`, not `ac`).

## NIST 800-171 Rev 3

**Framework ID:** `nist-800-171-r3`

### Family IDs

Family IDs use the same **lowercase slug** convention as NIST 800-53:

| Correct | Incorrect |
|---------|-----------|
| `access-control` | `ac`, `3.1` |
| `incident-response` | `ir`, `3.6` |
| `identification-and-authentication` | `ia`, `3.5` |

### Control IDs

Control IDs use **dotted notation with leading zeros**:

| Correct | Incorrect |
|---------|-----------|
| `03.01.01` | `3.1.1`, `ac-01` |
| `03.01.02` | `3.1.2`, `ac-02` |
| `03.13.01` | `3.13.1`, `sc-01` |

## Auto-Normalization

The CLI and MCP tools automatically normalize NIST 800-53 and FedRAMP control IDs: uppercase is lowered and single-digit numbers are zero-padded. For example, `AC-2` becomes `ac-02` and `SC-7.1` becomes `sc-07.1`. CMMC and NIST 800-171 IDs are passed through unchanged — use the exact format shown above.

## Discovery Workflow

When a user provides an informal control reference (e.g., "AC-2" or "access control"):

1. Call `pretorin frameworks families <framework_id>` to find the correct family slug
2. Call `pretorin frameworks controls <framework_id> --family <family_slug>` to find the correct control ID
3. Use the discovered ID in subsequent calls

## Quick Reference

| Framework | Family Format | Control Format | Example |
|-----------|---------------|----------------|---------|
| NIST 800-53 | `access-control` | `ac-01` | `pretorin frameworks control nist-800-53-r5 ac-02` |
| FedRAMP | `access-control` | `ac-01` | `pretorin frameworks control fedramp-moderate ac-02` |
| CMMC | `access-control-level-2` | `AC.L2-3.1.1` | `pretorin frameworks control cmmc-l2 AC.L2-3.1.1` |
| 800-171 | `access-control` | `03.01.01` | `pretorin frameworks control nist-800-171-r3 03.01.01` |
