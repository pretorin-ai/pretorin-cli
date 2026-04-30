---
id: campaign
version: 0.1.0
name: "Compliance Campaign"
description: "Bulk control work across many controls (a family, an entire framework, or a filtered subset). Pick this when the user wants to draft narratives, capture evidence, and record gaps for a large set of controls in one coordinated run with checkpoint persistence and resume support."
use_when: "The user asks for bulk control work — 'draft narratives for the entire AC family', 'work through all FedRAMP Moderate controls that need narratives', 'campaign-apply' commands. Not for single-control work (use `single-control`) or questionnaire work (use `scope-question` / `policy-question`)."
produces: mixed
iterates_over: campaign_items
recipes_commonly_used:
  - code-evidence-capture
  - inspec-baseline
  - openscap-baseline
  - cloud-aws-baseline
  - cloud-azure-baseline
  - manual-attestation
---

# Compliance Campaign

Iterate over many controls (a family, a framework, or a filtered set) and
do narrative + evidence + notes work for each. Campaigns can run for
hundreds or thousands of items, so iteration runs **server-side** in
pretorin (using pretorin's own `CodexAgent`) — not in the calling agent's
context window. The calling agent kicks off the campaign and observes
its progress; the per-item generation happens on pretorin's side.

## Iteration shape

Server-side, batched, resumable. Each item gets its own claim/draft/submit
cycle with TTL-based leases. The calling agent does NOT iterate items
in its own loop.

## Step-by-step

1. **Prepare.** Build the campaign manifest with the target domain
   (controls, scope, or policy) and any filters:

   ```
   pretorin_prepare_campaign(system_id, framework_id,
                             domain="controls", mode="draft",
                             filters={"family": "ac"})
   ```

   Returns a `campaign_id` plus the planned item set.

2. **Show the plan.** Confirm with the user before claiming items.
   Bulk-drafting hundreds of controls is a multi-hour operation; the
   user should see what will run.

3. **Claim items.** Lease items in batches; pretorin's server-side
   iterator handles the loop:

   ```
   pretorin_claim_campaign_items(campaign_id, batch_size=20)
   ```

4. **Wait for proposals.** Pretorin's CodexAgent runs server-side over
   each claimed item. For each one it:
   - Reads control context (`pretorin_get_control_context`).
   - Inspects observable workspace facts.
   - Picks a recipe from the registry (or freelances when no recipe
     fits — same recipe-selection model as the per-item path; the
     calling agent isn't doing this, pretorin is).
   - Drafts narrative + evidence + notes.
   - Submits a proposal (`pretorin_submit_campaign_proposal`).

5. **Monitor.** Poll periodically:

   ```
   pretorin_get_campaign_status(campaign_id)
   ```

   Status surfaces per-batch progress, errors, and any items where
   server-side generation requested human input.

6. **Review and apply.** When the campaign reaches `ready_to_apply`,
   show the user the proposal set and confirm before pushing:

   ```
   pretorin_apply_campaign(campaign_id)
   ```

   Pushes accepted proposals to the platform with audit metadata
   stamped. The recipe-selection record per item is preserved on the
   resulting evidence/narrative records.

## What server-side iteration buys you

- **No context-window pressure** on the calling agent. Pretorin's
  CodexAgent processes items in isolation; the calling agent only
  sees status snapshots.
- **Resume across sessions.** If the user closes their IDE mid-campaign,
  the work continues. The calling agent re-enters by polling
  `pretorin_get_campaign_status`.
- **Same recipe model.** The recipes pretorin's CodexAgent picks
  per-item are the same recipes the calling agent picks in
  `single-control`. One playbook surface, two callers.

## What to avoid

- Don't run a campaign as a loop of `single-control` invocations from
  the calling agent. That defeats the server-side iteration premise
  and burns tokens for no reason.
- Don't apply without the user's explicit confirmation. A 500-control
  apply is irreversible; "apply with `--no-confirm`" is for CI, not
  interactive work.
- Don't claim items you can't process. Leases time out, but unfinished
  claims pollute the campaign status and slow other workers.
