# STIG & CCI Browsing

The `stig` and `cci` command groups let you browse STIG benchmarks, rules, and CCIs with full traceability from NIST 800-53 controls down to individual STIG check rules.

## STIG Commands

### List STIG Benchmarks

```bash
pretorin stig list
pretorin stig list --technology-area "Network"
pretorin stig list --product "Windows" --limit 10
```

### Show STIG Details

```bash
pretorin stig show <stig_id>
```

Shows benchmark metadata including title, version, release info, and severity breakdown of rules.

### List Rules for a STIG

```bash
pretorin stig rules <stig_id>
pretorin stig rules <stig_id> --severity cat_i
pretorin stig rules <stig_id> --cci CCI-000015 --limit 20
```

### Show Applicable STIGs

```bash
# Uses active system context
pretorin stig applicable

# Explicit system
pretorin stig applicable --system "My System"
```

### AI-Infer Applicable STIGs

```bash
pretorin stig infer
pretorin stig infer --system "My System"
```

Uses the system's profile to recommend which STIG benchmarks should apply.

## CCI Commands

CCIs (Control Correlation Identifiers) bridge NIST 800-53 controls to specific STIG rules via SRGs (Security Requirements Guides).

### List CCIs

```bash
pretorin cci list
pretorin cci list --control ac-2
pretorin cci list --status draft --limit 50
```

### Show CCI Details

```bash
pretorin cci show CCI-000015
```

Shows the CCI definition, linked SRGs, and linked STIG rules.

### Full Traceability Chain

```bash
pretorin cci chain ac-2
pretorin cci chain ac-2 --system "My System"
```

Shows the complete chain: **NIST 800-53 Control -> CCIs -> SRGs -> STIG rules** (and test results when `--system` is provided).

This is useful for understanding exactly which technical checks validate a given control requirement.
