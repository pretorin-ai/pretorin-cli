# Control ID Format Reference

Correct ID formatting is critical. The Pretorin API returns errors on malformed IDs. Always discover IDs first with `pretorin_list_control_families` or `pretorin_list_controls` when unsure.

## NIST 800-53 Rev 5 / FedRAMP

**Framework IDs**: `nist-800-53-r5`, `fedramp-low`, `fedramp-moderate`, `fedramp-high`

**Family IDs** are lowercase slugs (not short codes):

| Correct | Incorrect |
|---|---|
| `access-control` | `ac` |
| `audit-and-accountability` | `au` |
| `identification-and-authentication` | `ia` |
| `system-and-communications-protection` | `sc` |
| `configuration-management` | `cm` |
| `incident-response` | `ir` |
| `risk-assessment` | `ra` |

**Control IDs** are zero-padded with a hyphen:

| Correct | Incorrect |
|---|---|
| `ac-01` | `ac-1`, `AC-1`, `ac1` |
| `ac-02` | `ac-2`, `AC-2`, `ac2` |
| `au-02` | `au-2`, `AU-2` |
| `sc-07` | `sc-7`, `SC-7` |

## CMMC 2.0

**Framework IDs**: `cmmc-l1`, `cmmc-l2`, `cmmc-l3`

**Family IDs** include a level suffix:

| Correct | Incorrect |
|---|---|
| `access-control-level-1` | `access-control`, `ac` |
| `access-control-level-2` | `access-control`, `ac-l2` |
| `incident-response-level-2` | `incident-response`, `ir` |
| `system-and-communications-protection-level-3` | `sc`, `sc-l3` |

**Control IDs** use dotted notation with a level prefix:

| Correct | Incorrect |
|---|---|
| `AC.L2-3.1.1` | `ac-01`, `3.1.1` |
| `SC.L3-3.13.2` | `sc-07`, `3.13.2` |
| `AC.L1-3.1.22` | `ac.l1-3.1.22` |

Note: CMMC control IDs are case-sensitive. Use uppercase for the family prefix.

## NIST 800-171 Rev 3

**Framework ID**: `nist-800-171-r3`

**Family IDs** are lowercase slugs (same convention as 800-53):

| Correct | Incorrect |
|---|---|
| `access-control` | `ac`, `3.1` |
| `incident-response` | `ir`, `3.6` |
| `identification-and-authentication` | `ia`, `3.5` |

**Control IDs** use dotted notation:

| Correct | Incorrect |
|---|---|
| `03.01.01` | `3.1.1`, `ac-01` |
| `03.01.02` | `3.1.2`, `ac-02` |
| `03.13.01` | `3.13.1`, `sc-01` |

Note: Leading zeros are required in 800-171 control IDs.

## Discovery Workflow

When a user provides an informal control reference (e.g., "AC-2" or "access control"), follow this pattern:

1. Call `pretorin_list_control_families` with the framework to find the correct family slug
2. Call `pretorin_list_controls` with the framework and family to find the correct control ID
3. Use the discovered ID in subsequent calls to `pretorin_get_control` or `pretorin_get_control_references`
