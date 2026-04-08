# Campaign Workflows

Campaigns are the recommended way to run bulk compliance operations across multiple controls, policies, or scope questions. They replace manual one-at-a-time updates with a coordinated prepare-claim-propose-apply lifecycle.

## When to Use Campaigns

- **Initial control implementation** — Draft narratives and evidence for an entire control family
- **Fixing review findings** — Address issues flagged by family or policy reviews
- **Answering questionnaires** — Bulk-answer policy or scope questions
- **Notes remediation** — Fix controls flagged by platform notes

## Campaign Lifecycle

```
Prepare → Claim → Draft → Propose → Apply
```

1. **Prepare** — Snapshot platform state and create a checkpoint file. This captures the current state of all target items so the campaign works from a consistent baseline.

2. **Claim** — Lease items for drafting. TTL-based leases prevent concurrent editing when multiple agents are working in parallel.

3. **Draft** — For each claimed item, get full context (control requirements, current state, guidance) and produce a draft.

4. **Propose** — Submit drafts as proposals without writing to the platform. This provides a review opportunity before any changes are persisted.

5. **Apply** — Push all accepted proposals to the platform as a single operation.

## External Agent Pattern

Campaigns are designed for external agents (Claude Code, Codex, Cursor, etc.) operating through MCP:

```
Agent A: prepare_campaign → claim_campaign_items → get_campaign_item_context → submit_campaign_proposal
Agent B: claim_campaign_items → get_campaign_item_context → submit_campaign_proposal
...
Coordinator: get_campaign_status → apply_campaign
```

The checkpoint file enables independent agent execution. Agents can claim non-overlapping items and work in parallel.

## CLI Usage

### Control Campaign

```bash
# Draft narratives for the Access Control family
pretorin campaign controls --mode initial --family AC \
  --system "My System" --framework-id fedramp-moderate

# Fix controls flagged by notes
pretorin campaign controls --mode notes-fix --family AC

# Fix controls flagged by review
pretorin campaign controls --mode review-fix --family AC --review-job <job-id>

# Auto-apply after completion
pretorin campaign controls --mode initial --family AC --apply
```

### Policy Campaign

```bash
# Answer all incomplete policy questions
pretorin campaign policy --mode answer --all-incomplete

# Fix review findings for a specific policy
pretorin campaign policy --mode review-fix --policies <policy-id>
```

### Scope Campaign

```bash
pretorin campaign scope --mode answer \
  --system "My System" --framework-id fedramp-moderate
```

### Check Status

```bash
pretorin campaign status --checkpoint .pretorin/campaign-checkpoint.json
```

## MCP Tool Sequence

For AI agents working through MCP:

1. `pretorin_get_workflow_state` — Understand what needs work
2. `pretorin_get_pending_families` — Identify target families
3. `pretorin_prepare_campaign` — Create the campaign
4. `pretorin_claim_campaign_items` — Claim items
5. `pretorin_get_campaign_item_context` — Get context per item
6. `pretorin_submit_campaign_proposal` — Submit drafts
7. `pretorin_get_campaign_status` — Review progress
8. `pretorin_apply_campaign` — Push to platform
