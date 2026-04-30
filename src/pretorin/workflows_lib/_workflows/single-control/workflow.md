---
id: single-control
version: 0.1.0
name: "Single Control Update"
description: "Update one control's narrative, evidence, and notes for one system. Pick this when the user is working on a specific control by id (e.g., 'review AC-2 for system X') and the work fits in one focused pass without iterating across a family or the whole framework."
use_when: "The user names exactly one control id (or a single control is the obvious target). Not for cross-framework work, family rollups, or campaign-style bulk updates."
produces: mixed
iterates_over: single_control
recipes_commonly_used:
  - code-evidence-capture
  - inspec-baseline
  - openscap-baseline
  - cloud-aws-baseline
  - cloud-azure-baseline
  - manual-attestation
---

# Single Control Update

Update one control's narrative + evidence + notes in one focused pass. The
workflow does not iterate across a family or framework — that's what
`campaign` is for. If the user has a list of controls, route to `campaign`
with a control filter instead.

## Iteration shape

The "iteration" here is degenerate: one item. Do the work below once.

## Step-by-step

1. **Resolve scope.** Confirm `system_id`, `control_id`, and `framework_id`
   are all set. Any one missing — ask the user. Do not guess.

2. **Read current state before writing.** The platform may already carry a
   narrative / evidence / notes for this control. Don't blindly overwrite.

   ```
   pretorin_get_control_context(system_id, control_id, framework_id)
   pretorin_get_narrative(system_id, control_id, framework_id)
   pretorin_get_control_implementation(system_id, control_id, framework_id)
   pretorin_search_evidence(system_id, control_id=control_id)
   pretorin_get_control_notes(system_id, control_id)
   ```

3. **Inspect the workspace.** Look at code, configs, and connected MCP
   sources for observable facts about how this control is implemented.
   Existing platform records are a *starting point*, not proof a gap
   exists. If the workspace shows stronger implementation than the
   platform record, plan to update the narrative to match observed
   reality.

4. **Pick recipes for each evidence/narrative artifact.** Call
   `pretorin_list_recipes` to see the menu. Match each piece of work to a
   recipe whose `use_when` fits:
   - Capturing a config snippet from a source file → `code-evidence-capture`.
   - Running a STIG scan → one of the `*-baseline` recipes.
   - Recording human attestation when no automated check exists →
     `manual-attestation`.
   - No recipe fits → fall through to direct platform writes
     (`pretorin_create_evidence`, `pretorin_update_narrative`) and note
     in the audit log why no recipe was a good match.

5. **Run each picked recipe** through the standard lifecycle:
   ```
   pretorin_start_recipe(recipe_id, recipe_version, params)  → context_id
   pretorin_recipe_<safe_id>__<script>(...)                  # one or more
   pretorin_create_evidence(..., recipe_context_id=context_id)
   pretorin_end_recipe(context_id, status)
   ```

6. **Update the narrative** to reflect observed implementation.
   `pretorin_update_narrative` carries the same audit-metadata stamping
   when called inside a recipe context.

7. **Record gaps as control notes.** Anything the workspace + connected
   sources couldn't verify becomes a `pretorin_add_control_note` entry
   in the standard Gap/Observed/Missing/Why missing/Manual next step
   format.

## What to avoid

- Don't open a recipe context unless you'll use it. Empty contexts
  create audit-trail noise.
- Don't nest contexts. Close one before opening another (the runtime
  enforces this).
- Don't write evidence without a `recipe_context_id` *if* a recipe was
  applicable. The audit trail loses the "why" otherwise.
- Don't fabricate evidence to fill an empty `evidence_recommendations`
  list. An empty list is a valid result *after* you confirmed the
  workspace has nothing.
