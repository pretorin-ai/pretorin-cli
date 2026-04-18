# Cross-Framework Mapping

Map controls across related frameworks to identify overlaps, reduce duplicate work, and understand framework relationships.

## When to Use Cross-Framework Mapping

- **Dual compliance** — Organization needs FedRAMP + CMMC. Map overlapping controls to avoid duplicate work.
- **Framework migration** — Moving from 800-171 to FedRAMP. Identify which controls already satisfy FedRAMP requirements.
- **Gap identification** — Already compliant with 800-53 and need CMMC. Find the delta.
- **Audit preparation** — Show auditors how controls in one framework map to another.

## Workflow

### Step 1: Start with the Source Control

Query the control with references to discover relationships:

```bash
pretorin frameworks control nist-800-53-r5 ac-02
```

References are shown by default. The **Related Controls** field reveals connections to other controls and frameworks.

### Step 2: Build the Mapping

Look up the equivalent control in each target framework:

| Framework | Control ID | Title |
|-----------|-----------|-------|
| NIST 800-53 Rev 5 | `ac-02` | Account Management |
| FedRAMP Moderate | `ac-02` | Account Management |
| NIST 800-171 Rev 3 | `03.01.01` | Account Management |
| CMMC Level 2 | `AC.L2-3.1.1` | Authorized Access Control |

### Step 3: Compare Requirements

Get details for each framework's version of the control:

```bash
pretorin frameworks control nist-800-53-r5 ac-02
pretorin frameworks control fedramp-moderate ac-02
pretorin frameworks control nist-800-171-r3 03.01.01
pretorin frameworks control cmmc-l2 AC.L2-3.1.1
```

Compare what each framework emphasizes. For Account Management:

- **NIST 800-53** — Full control with 13 enhancements. Covers account types, conditions, authorized users, managers, CRUD, monitoring, and atypical usage.
- **FedRAMP Moderate** — Same base control with FedRAMP-specific parameter values (e.g., specific timeframes for disabling inactive accounts).
- **NIST 800-171** — Streamlined from 800-53. Core requirements: defining types, assigning managers, establishing conditions, authorizing access, monitoring.
- **CMMC Level 2** — Maps directly to 800-171 03.01.01. Same core requirements framed as maturity practices.

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

**Key insight:** Compliance with a parent framework generally satisfies the child framework's corresponding control. Always verify with `pretorin frameworks control <fw> <ctrl>` to check for framework-specific parameters or additional requirements (references are included by default).

## Using MCP for Cross-Framework Mapping

With an MCP-connected AI agent, ask questions like:

> "Map Account Management controls across NIST 800-53, FedRAMP Moderate, and CMMC Level 2. Show me the overlaps and any unique requirements."

The agent will use `pretorin_get_control` and `pretorin_get_control_references` to discover and compare related controls across frameworks.
