# Example: Cross-Framework Control Mapping

This example demonstrates how to map Account Management controls across four related frameworks using `pretorin_get_control_references` to discover relationships.

## Mapping: Account Management

### Step 1: Start with the Source Control

Query AC-02 in NIST 800-53 Rev 5 using `pretorin_get_control_references`:

```
framework_id: nist-800-53-r5
control_id: ac-02
```

The `related_controls` field in the response reveals connections to other controls and frameworks.

### Step 2: Build the Mapping

| Framework | Control ID | Title | Controls |
|---|---|---|---|
| NIST 800-53 Rev 5 | `ac-02` | Account Management | 324 total |
| FedRAMP Moderate | `ac-02` | Account Management | 181 total (same ID, framework-specific parameters) |
| NIST 800-171 Rev 3 | `03.01.01` | Account Management | 130 total |
| CMMC Level 2 | `AC.L2-3.1.1` | Authorized Access Control | 110 total |

### Step 3: Compare Requirements

Call `pretorin_get_control_references` for each framework's version of the control to compare:

**NIST 800-53 (ac-02)** — Full control with 13 enhancements. Covers account types, conditions for group membership, authorized users, account managers, account creation/modification/disabling/removal, monitoring, and atypical usage.

**FedRAMP Moderate (ac-02)** — Same base control as 800-53 but with FedRAMP-specific parameter values (e.g., specific timeframes for disabling inactive accounts, required account types to document).

**NIST 800-171 (03.01.01)** — Derived from 800-53 AC-02 but streamlined. Focuses on the core requirements: defining account types, assigning account managers, establishing conditions, authorizing access, and monitoring usage.

**CMMC Level 2 (AC.L2-3.1.1)** — Maps directly to NIST 800-171 03.01.01. Same core requirements framed as maturity practices.

### Step 4: Identify Gaps and Overlaps

```
NIST 800-53 AC-02 (most comprehensive)
  ├── Includes all FedRAMP Moderate AC-02 requirements ✓
  ├── Includes all NIST 800-171 03.01.01 requirements ✓
  └── Includes all CMMC L2 AC.L2-3.1.1 requirements ✓

FedRAMP Moderate AC-02
  ├── Satisfies NIST 800-171 03.01.01 ✓
  └── Satisfies CMMC L2 AC.L2-3.1.1 ✓

NIST 800-171 03.01.01
  └── Satisfies CMMC L2 AC.L2-3.1.1 ✓
```

**Key insight**: Compliance with a parent framework generally satisfies the child framework's corresponding control, but always verify using `pretorin_get_control_references` to check for framework-specific parameters or additional requirements.

## When to Use Cross-Framework Mapping

- **Dual compliance**: Organization needs FedRAMP + CMMC. Map overlapping controls to avoid duplicate work.
- **Framework migration**: Moving from 800-171 to FedRAMP. Identify which controls already satisfy FedRAMP requirements.
- **Gap identification**: Already compliant with 800-53 and need CMMC. Find the delta.
- **Audit preparation**: Show auditors how controls in one framework map to another.

## Workflow

1. Call `pretorin_get_control_references` for the source control
2. Note the `related_controls` in the response
3. For each related control in a target framework, call `pretorin_get_control_references` to compare
4. Document the mapping with any differences in parameters, enhancements, or scope
5. Identify controls in the target framework that have no mapping (these are the gaps)
