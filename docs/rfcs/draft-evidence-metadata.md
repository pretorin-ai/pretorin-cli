# Draft: Evidence Baseline Metadata

- **Status**: Draft / discussion
- **Date**: 2026-04-28
- **Author**: Isaac Faber (drafted with Claude)
- **Related**: [RFC 0001 — Recipes](0001-recipes.md), PR #92, project memory `project_evidence_redesign`

## Why this exists

Reviewing PR #92 (`feat(evidence): inline redacted code/log capture`) surfaced a layering problem: the PR enforces a workflow-specific evidence shape (fenced code block + provenance footer in markdown) at the universal write boundary via a `model_validator` on `EvidenceCreate` / `EvidenceBatchItemCreate`. Once recipes (RFC 0001) land as the extensibility surface, that lock-in defeats the whole point — every recipe has to thread through the same one workflow's opinion of what evidence looks like.

The right separation:

- **Recipes own the body shape.** Markdown layout, code-block requirements, footer formatting, screenshot composition, attestation phrasing — recipe-layer policy. A recipe can refuse to emit evidence that doesn't match its own contract; that contract does not need to be enforced at the platform model.
- **The platform model owns baseline metadata.** The structured fields every evidence record carries regardless of which recipe (or no recipe) produced it. This is the auditor's "I trust this record because…" surface.

This note proposes what that baseline metadata should be.

## Framing

The CLI is a thin consumer of the platform's evidence model (per `feedback_cli_lightweight` memory and the approved evidence redesign). So this is fundamentally a **platform-model** question. The CLI's job is to populate whatever the platform decides; this note is the conversation-starter for what the platform should decide.

The hard tradeoff: every required field is friction at write time and a backwards-compat headache at the API. Every optional field is sparse data at audit time. The goal is the minimum required set that an auditor genuinely needs, with everything else optional-but-encouraged.

## Proposed baseline

### 1. Identity & lifecycle *(platform-stamped)*

| Field | Type | Notes |
|---|---|---|
| `evidence_id` | uuid | platform-generated |
| `created_at` | timestamp | platform-generated |
| `updated_at` | timestamp | platform-generated |
| `created_by` | user_id / agent_id | who initiated the write |
| `status` | enum | `active` \| `superseded` \| `revoked` \| `draft` |
| `supersedes` | evidence_id? | continuity link to prior record this replaces |

Rationale: `supersedes` matters because real compliance evidence is refreshed quarterly / annually; without a continuity chain you get a graveyard of orphan records.

### 2. Compliance binding *(the reason the record exists)*

| Field | Type | Notes |
|---|---|---|
| `system_id` | uuid | which SSP / system |
| `control_refs[]` | `{framework_id, control_id}[]` | ≥1 required; multi-control is real and common |
| `cci_refs[]` | string[] | optional finer-grained DoD-style binding |
| `stig_rule_refs[]` | string[] | optional, for STIG-driven evidence |

### 3. Provenance *(how the underlying truth was observed)*

| Field | Type | Notes |
|---|---|---|
| `captured_at` | timestamp | RFC3339 UTC. **Distinct from `created_at`.** When the state was actually true. |
| `source_type` | enum | `code_snippet` \| `log_excerpt` \| `configuration` \| `screenshot` \| `document` \| `attestation` \| `scan_result` \| … |
| `source_uri` | string | path / URL / ARN / git ref. Meaning depends on `source_type`. |
| `source_version` | string? | commit SHA, S3 versionId, doc revision |

The `captured_at` / `created_at` split is non-negotiable in my view: a log excerpt captured Tuesday and uploaded Thursday has two timestamps an auditor cares about distinctly.

### 4. Producer attribution *(who/what made this)*

| Field | Type | Notes |
|---|---|---|
| `producer_kind` | enum | `cli` \| `recipe` \| `agent` \| `manual_upload` \| `api` |
| `producer_id` | string? | `github-branch-protection`, `cli`, `claude-opus-4-7`, … |
| `producer_version` | string? | `0.1.0`, `0.17.0`, model id |

This is the field that makes recipes accountable later. "Which recipe produced the bad evidence" needs to be answerable when one starts emitting nonsense.

### 5. Integrity & transformation

| Field | Type | Notes |
|---|---|---|
| `content_hash` | sha256 | of the canonical body. Tamper detection. |
| `redaction_summary` | `{secrets: int, pii: int, …}` | auditor needs to know the body was transformed even if not what was removed |

### 6. Tagging *(discovery + recipe-authored opinion)*

| Field | Type | Notes |
|---|---|---|
| `tags[]` | string[] | free-form. Recipes use these to mark recipe-defined attributes; users add their own. |

## Required vs optional

Proposed minimum required set:

- `system_id`
- `control_refs[]` (≥1)
- `source_type`
- `captured_at`
- `producer_kind`

Everything else strongly encouraged but nullable. Small enough that manual uploads from the platform UI can clear it; rich enough that OSCAL export has something to key off.

## Open questions

1. **`captured_at` vs `created_at` — both, or one?** Recommendation: both. The cost is one timestamp field; the benefit is auditor clarity on temporal drift between observation and upload.

2. **How structured should `source_uri` be?** Two options:
   - **Plain string** (simplest; OSCAL export has to parse).
   - **Discriminated union**: `{type: "git", repo, path, commit}` vs `{type: "s3", bucket, key, version}` vs `{type: "url", url}` vs `{type: "local", path}`.

   Recommendation depends on how near-term OSCAL/SSP export is. If it's <6 months out, the discriminated union pays for itself. If it's >12 months out, ship the string and migrate later.

3. **Should `redaction_summary` be free-form or schema'd?** A schema (`{secrets: int, pii: int, custom: int}`) lets the platform render a badge consistently. Free-form (`{aws_keys: 2, github_pats: 1}`) preserves recipe-level granularity at the cost of UI consistency. Recommendation: schema'd top-level counts with optional `details: object` for per-recipe granularity.

4. **Multi-system evidence?** Today `system_id` is one. A vendor inheritance attestation might attest to a control across multiple systems. Punt: keep one for v1, model many-to-many in evidence-to-control linkage if needed later.

5. **What about `valid_from` / `valid_until`?** Logs cover a window; configs are point-in-time. A `valid_until` would let the platform automatically mark stale evidence — but it conflates "this evidence is past its window" with "this evidence is wrong." Punt to a separate freshness/staleness discussion.

## What this means for PR #92

If this baseline is right, PR #92 should be redirected to:

1. Populate the structured fields (`captured_at`, `source_type`, `source_uri`, `source_version`, `redaction_summary`, `content_hash`) on the API request as typed columns.
2. Drop the markdown-shape `model_validator`. The fenced-code-block + footer composition becomes the *capture recipe's* contract, not a platform invariant.
3. Keep `--no-capture` as the original issue specified (don't presume one workflow).
4. Keep the campaign-apply leak fix (running `enrich_evidence_recommendations` through redact + compose) — that stands on its own.

## Next steps

- Isaac to review categories tomorrow; push back on anything that feels over- or under-required.
- Once required-set is agreed, draft the platform model migration separately (this repo is the consumer, not the source of truth).
- Once platform model is settled, redirect PR #92 to populate the new fields.
