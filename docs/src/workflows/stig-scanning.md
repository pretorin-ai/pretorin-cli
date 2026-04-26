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

### 1. Check Scanner Availability

```bash
pretorin scan doctor
```

Supported scanners: OpenSCAP, InSpec, AWS Cloud Scanner, Azure Cloud Scanner, Manual.

### 2. Review Test Manifest

```bash
pretorin scan manifest --system "My System"
```

Shows which STIGs, rules, and scanners apply to the system.

### 3. Run Scans

```bash
# Run all applicable scans
pretorin scan run --system "My System"

# Dry run first
pretorin scan run --system "My System" --dry-run

# Target specific STIG or tool
pretorin scan run --stig <stig_id> --tool openscap
```

### 4. Review Results

```bash
# All results
pretorin scan results --system "My System"

# Filter by control
pretorin scan results --system "My System" --control ac-2
```

### 5. Submit Results to Platform

Results are automatically submitted when scanning with an active system context. For manual submission via MCP:

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
