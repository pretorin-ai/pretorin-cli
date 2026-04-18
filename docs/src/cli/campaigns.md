# Campaign Workflows

The `campaign` command group runs bulk compliance operations across multiple controls, policies, or scope questions in a single coordinated run. Campaigns support an external-agent-first pattern with checkpoint persistence and lease-based concurrency for safe fan-out to multiple agents.

## Campaign Domains and Modes

| Domain | Mode | Description |
|--------|------|-------------|
| `controls` | `initial` | Draft new narratives and evidence for controls |
| `controls` | `notes-fix` | Address platform notes on existing controls |
| `controls` | `review-fix` | Fix findings from a family review job |
| `policy` | `answer` | Generate answers for policy questions |
| `policy` | `review-fix` | Fix findings from a policy review |
| `scope` | `answer` | Generate answers for scope questions |
| `scope` | `review-fix` | Fix findings from a scope review |

## Control Campaigns

### Draft New Narratives for a Family

```bash
pretorin campaign controls --mode initial --family AC \
  --system "My System" --framework-id fedramp-moderate
```

### Fix Controls with Platform Notes

```bash
pretorin campaign controls --mode notes-fix --family AC
```

### Fix Controls after Family Review

```bash
pretorin campaign controls --mode review-fix --family AC --review-job <job-id>
```

### Options

| Option | Description |
|--------|-------------|
| `--system` | Target system ID or name |
| `--framework-id` | Target framework ID |
| `--family` | Control family to target (e.g., `AC`, `AU`) |
| `--controls` | Specific control IDs (comma-separated) |
| `--all-controls` | Target all controls in the framework |
| `--mode` | Campaign mode: `initial`, `notes-fix`, `review-fix` |
| `--artifacts` | Artifact types to generate: `narratives`, `evidence`, or `both` (default: `both`) |
| `--review-job` | Review job ID (required for `review-fix` mode) |
| `--concurrency` | Number of parallel workers |
| `--max-retries` | Maximum retry attempts per item |
| `--checkpoint` | Path to checkpoint file for resume |
| `--apply` | Apply proposals to platform after completion |
| `--output` | Output mode: `auto`, `live`, `compact`, `json` |

## Policy Campaigns

### Answer All Incomplete Policy Questions

```bash
pretorin campaign policy --mode answer --all-incomplete
```

### Fix Policy Review Findings

```bash
pretorin campaign policy --mode review-fix --policies <policy-id>
```

## Scope Campaigns

### Answer Scope Questions

```bash
pretorin campaign scope --mode answer \
  --system "My System" --framework-id fedramp-moderate
```

## Checking Campaign Status

```bash
pretorin campaign status --checkpoint .pretorin/campaign-checkpoint.json
```

## Campaign Lifecycle

1. **Prepare** — The campaign snapshots platform state and creates a local checkpoint file
2. **Claim** — Items are claimed with TTL-based leases (safe for multiple agents)
3. **Draft** — Each item gets full context and drafting instructions
4. **Propose** — Proposals are submitted without writing to the platform
5. **Apply** — All accepted proposals are pushed to the platform in one operation

Use `--apply` to automatically apply after completion, or run `campaign status` to review before applying.
