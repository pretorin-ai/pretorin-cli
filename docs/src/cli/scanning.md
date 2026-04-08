# STIG Scanning

The `scan` command group runs STIG compliance scans using available scanner tools and manages test results.

## Check Scanner Availability

```bash
pretorin scan doctor
```

Lists which scanner tools are installed and available on your system:

| Scanner | Description |
|---------|-------------|
| OpenSCAP | Open-source SCAP scanner |
| InSpec | Chef InSpec compliance profiles |
| AWS Cloud Scanner | AWS-native compliance scanning |
| Azure Cloud Scanner | Azure-native compliance scanning |
| Manual | Manual review checklist |

## View Test Manifest

```bash
# Uses active system context
pretorin scan manifest

# Filter by STIG
pretorin scan manifest --system "My System" --stig <stig_id>
```

Shows which STIGs and rules are applicable to the system and which scanners can test them.

## Run Scans

```bash
# Run all applicable scans
pretorin scan run

# Target a specific STIG
pretorin scan run --stig <stig_id>

# Use a specific scanner
pretorin scan run --tool openscap

# Dry run (show what would execute)
pretorin scan run --dry-run
```

The scan orchestrator automatically detects available scanners, assigns rules to capable tools, and collects results.

### Options

| Option | Description |
|--------|-------------|
| `--system` / `-s` | Target system (uses active context if omitted) |
| `--stig` | Run only rules from this STIG benchmark |
| `--tool` / `-t` | Force a specific scanner tool |
| `--dry-run` | Show the test plan without executing |

## View Results

```bash
# All results for active system
pretorin scan results

# Filter by control
pretorin scan results --system "My System" --control ac-2
```

Shows CCI-level test results including pass/fail status, scanner used, and timestamp.

## Workflow

1. `pretorin scan doctor` — Verify scanner tools are installed
2. `pretorin scan manifest` — Review what will be tested
3. `pretorin scan run --dry-run` — Preview the test plan
4. `pretorin scan run` — Execute scans
5. `pretorin scan results` — Review results

Results are automatically submitted to the platform when a system context is active.
