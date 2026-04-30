# Writer Tools

Recipe scripts call the platform API through `ctx.api_client`, which is
the same `PretorianClient` the rest of pretorin uses. This page covers the
common write paths and how audit metadata gets stamped automatically when
your recipe runs inside an execution context.

## How Audit Metadata Gets Stamped

The calling agent opens an execution context with
`pretorin_start_recipe(recipe_id, recipe_version, params)` and gets back a
`context_id`. Subsequent platform writes from that MCP session pick up the
context automatically and stamp:

```json
{
  "producer_kind": "recipe",
  "producer_id": "<recipe_id>",
  "producer_version": "<recipe_version>",
  "recipe_context_id": "<context_id>"
}
```

When your script makes an MCP-routed write — i.e., the calling agent's
write goes through `pretorin_create_evidence` or similar — the stamping is
**automatic**. You don't pass `producer_kind` yourself; the MCP handler
reads the context from the session and builds the metadata.

When your script makes a write **directly** through `ctx.api_client`
(skipping MCP), you have to pass `audit_metadata` yourself. The helper to
build it lives at `pretorin.evidence.audit_metadata`:

```python
from pretorin.evidence.audit_metadata import build_recipe_metadata

audit_metadata = build_recipe_metadata(
    recipe_id=ctx.recipe_id,
    recipe_version=ctx.recipe_version,
    recipe_context_id=ctx.recipe_context_id,
    source_type="configuration",
    content_hash=...,
    redaction_summary=...,
)

evidence = EvidenceCreate(
    control_id="ac-2",
    framework_id="nist-800-53-r5",
    name="...",
    evidence_type="configuration",
    description=composed_markdown,
    audit_metadata=audit_metadata,
)
await ctx.api_client.create_evidence(ctx.system_id, evidence)
```

Most recipes don't need the direct path — write through MCP and let the
handler stamp.

## Read-Side Helpers

You'll often need to read platform state before writing. The most useful
methods on `ctx.api_client`:

| Method | Returns | Use |
|--------|---------|-----|
| `list_systems()` | `list[dict]` | Find a system id when one wasn't passed in `ctx.system_id`. |
| `get_test_manifest(system_id, stig_id=None)` | `dict` | The applicable rules for a system, optionally narrowed to one STIG. |
| `get_control(framework_id, control_id)` | `ControlDetail` | Full control text + family + status. |
| `get_controls_batch(framework_id, control_ids)` | dict | Batch fetch — cheaper than N calls. |
| `get_control_implementation(...)` | dict | Current narrative + status for one control. |
| `get_stig_applicability(system_id)` | dict | Which STIGs apply to a system. |
| `get_compliance_status(system_id, framework_id)` | dict | High-level coverage rollup. |
| `get_source_manifest(system_id)` | dict | Verified-sources state for the system. |

### Manifest helpers for scanner recipes

If you're building a scanner recipe, three helpers in
`pretorin.scanners.manifest` cover the common shape:

```python
from pretorin.scanners.manifest import (
    fetch_test_manifest,
    rules_for_stig,
    summarize_results,
)

manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id="RHEL_9_STIG")
rules = rules_for_stig(manifest, "RHEL_9_STIG")
results = await my_scanner.execute(rules, config={"target": "local"})
summary = summarize_results(results)
```

Every built-in scanner recipe uses exactly this pattern. If you're wrapping
a new scanner, copy `inspec-baseline/scripts/run_scan.py` as a starting
point.

## Write-Side: Evidence

```python
from pretorin.client.models import EvidenceCreate

evidence = EvidenceCreate(
    control_id="ac-2",
    framework_id="nist-800-53-r5",
    name="RBAC configuration excerpt",
    evidence_type="configuration",
    description=composed_markdown,
    status="approved",
)
result = await ctx.api_client.create_evidence(ctx.system_id, evidence)
```

For batched writes (much faster when you have ≥ 10):

```python
from pretorin.client.models import EvidenceBatchItemCreate

items = [
    EvidenceBatchItemCreate(control_id="ac-2", name="...", evidence_type="...", ...)
    for _ in batch
]
response = await ctx.api_client.create_evidence_batch(
    ctx.system_id,
    framework_id="nist-800-53-r5",
    items=items,
)
```

For binary/unstructured artifacts (a screenshot, a PDF, an exported
report), upload the file:

```python
result = await ctx.api_client.upload_evidence(
    system_id=ctx.system_id,
    file_path="/tmp/my-screenshot.png",
    name="Console screenshot — IAM users page",
    evidence_type="screenshot",
    control_id="ac-2",
)
```

## Write-Side: Narratives

```python
await ctx.api_client.update_narrative(
    system_id=ctx.system_id,
    framework_id="nist-800-53-r5",
    control_id="ac-2",
    narrative=composed_text,
)
```

Narratives are stamped with the same audit metadata when written through
the MCP write handler.

## Write-Side: Test Results

For scanner recipes:

```python
await ctx.api_client.submit_test_results(
    system_id=ctx.system_id,
    benchmark_id="RHEL_9_STIG",
    results=[...],   # list of TestResult dicts
)
```

## Redaction and Markdown Composition

Two helpers from `pretorin.evidence`:

```python
from pretorin.evidence.redact import redact_secrets
from pretorin.evidence.markdown import compose

redacted_text, redaction = redact_secrets(raw_text)
markdown = compose(
    prose="The IAM trust policy is configured to require MFA for assume-role.",
    snippet=redacted_text,
    snippet_lang="json",
    file_path="iam/trust-policy.json",
)
```

`redact_secrets` returns a `RedactionResult` with counts per secret type
(AWS access keys, GitHub tokens, JWTs, etc.). `compose` turns prose +
snippet into the audit-grade markdown body the platform expects on
evidence records.

These two are the building blocks of the `code-evidence-capture` built-in
recipe — read its source under `src/pretorin/recipes/_recipes/code-evidence-capture/`
for a real-world usage pattern.

## What Recipe Scripts Should *Not* Do

- **Don't bypass `ctx.api_client`** to talk to the platform via raw HTTP.
  You'll skip the auth, retry, and error-handling logic the client
  provides.
- **Don't construct `audit_metadata` from scratch.** Use
  `build_recipe_metadata` / `build_recipe_metadata_from_context` so the
  shape stays consistent.
- **Don't call `pretorin_start_recipe` from inside a script.** The recipe
  context is already open — that's how the script got invoked. Nesting is
  forbidden.
- **Don't assume `ctx.system_id` is set.** If your recipe requires a
  system, raise early with a clear message rather than passing `None`
  through to the API.
