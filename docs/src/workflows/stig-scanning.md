# STIG Compliance Scanning

Pretorin integrates STIG (Security Technical Implementation Guide) scanning to verify technical control implementations. The scanning workflow connects NIST 800-53 controls to specific technical checks via the CCI (Control Correlation Identifier) chain.

## Traceability Chain

```
NIST 800-53 Control → CCIs → SRGs → STIG Rules → Scanner Results
```

- **CCI** — Control Correlation Identifier: bridges a control requirement to testable items
- **SRG** — Security Requirements Guide: technology-neutral security requirements
- **STIG Rule** — Technology-specific check with detailed test and fix procedures

## Browse the Chain

### Find Applicable STIGs

```bash
# Show STIGs applicable to your system
pretorin stig applicable --system "My System"

# AI-infer STIGs from system profile
pretorin stig infer --system "My System"
```

### Explore the Traceability

```bash
# Full chain from a NIST control to STIG rules
pretorin cci chain ac-2 --system "My System"

# Browse CCIs for a control
pretorin cci list --control ac-2

# See what a specific CCI requires
pretorin cci show CCI-000015

# Browse STIG rules
pretorin stig rules <stig_id> --severity cat_i
```

## Scanning Workflow

Scanning is driven by **recipes** that the calling AI agent invokes through MCP.
Each scanner ships as a built-in recipe (`inspec-baseline`, `openscap-baseline`,
`cloud-aws-baseline`, `cloud-azure-baseline`, `manual-attestation`).

### 1. Discover Available Recipes

```bash
pretorin recipe list
pretorin recipe show inspec-baseline
```

### 2. Review Test Manifest

The agent uses `pretorin_get_test_manifest` (MCP) to see which STIGs and rules
apply to a system before running a scan. From the CLI you can browse the
relationships directly:

```bash
pretorin stig applicable --system "My System"
pretorin cci chain ac-2 --system "My System"
```

### 3. Ask the Agent to Run the Scan

Inside Claude Code, Codex CLI, or `pretorin agent run`, ask:

> "Run an inspec-baseline scan against `RHEL_9_STIG` on this system."

The agent will open a recipe context, call the recipe's `run_scan` script,
and submit results through `pretorin_submit_test_results`. There is no
direct CLI command for executing a scan — the recipe layer is the
contract surface.

### 4. Submit Results Manually

If you have raw scanner output and want to upload it without running through
a recipe, push it directly via MCP:

```
pretorin_submit_test_results(system_id, results)
```

## MCP Tools for STIG/CCI

| Tool | Description |
|------|-------------|
| `pretorin_list_stigs` | List benchmarks with filters |
| `pretorin_get_stig` | Benchmark detail |
| `pretorin_list_stig_rules` | Rules with severity/CCI filters |
| `pretorin_get_stig_rule` | Full rule: check text, fix text, CCIs |
| `pretorin_list_ccis` | CCIs with control filter |
| `pretorin_get_cci` | CCI detail with linked rules |
| `pretorin_get_cci_chain` | Full traceability chain |
| `pretorin_get_cci_status` | CCI compliance rollup |
| `pretorin_get_stig_applicability` | Applicable STIGs for a system |
| `pretorin_infer_stigs` | AI-infer applicable STIGs |
| `pretorin_get_test_manifest` | Test manifest for a system |
| `pretorin_submit_test_results` | Upload scan results |
