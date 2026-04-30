---
name: pretorin
description: >
  This skill should be used when the user asks about compliance frameworks,
  security controls, control families, document requirements, FedRAMP, NIST 800-53,
  NIST 800-171, CMMC, STIGs, CCIs, vendor inheritance, compliance campaigns,
  policy/scope questionnaires, or wants to perform a compliance gap analysis,
  generate compliance artifacts, map controls across frameworks, run bulk
  compliance workflows, manage vendor responsibility, scan for STIG compliance,
  capture code or attestation evidence, or check what documents are needed for
  certification. Trigger phrases include "list frameworks", "show controls",
  "what documents do I need", "compliance check", "control requirements",
  "gap analysis", "audit my code", "run campaign", "vendor inheritance",
  "STIG rules", "CCI chain", "scan compliance", and "use a recipe".
version: 0.17.0
---

# Pretorin Compliance Skill

Query authoritative compliance framework data via the Pretorin MCP server. Access controls, families, document requirements, implementation guidance, STIG/CCI traceability, vendor inheritance, and campaign-based bulk workflows across NIST 800-53, NIST 800-171, FedRAMP (Low/Moderate/High), and CMMC (Level 1/2/3).

For repeatable evidence-capture and scanning procedures, prefer **recipes** (see [Recipes](#recipes) below) over freelancing — recipes are pretorin's curated playbooks, and writes inside a recipe context get audit metadata stamped automatically.

## Prerequisites

The Pretorin MCP server must be connected. If tools like `pretorin_list_frameworks` are not available, instruct the user to run:

```bash
uv tool install pretorin
pretorin login
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

When the user says "my current system" or relies on stored CLI scope, suggest `pretorin context show --quiet --check` before assuming the local context is still valid.

## Available Frameworks

| Framework ID | Title | Controls |
|---|---|---|
| `nist-800-53-r5` | NIST SP 800-53 Rev 5 | 324 |
| `nist-800-171-r3` | NIST SP 800-171 Rev 3 | 130 |
| `fedramp-low` | FedRAMP Rev 5 Low | 135 |
| `fedramp-moderate` | FedRAMP Rev 5 Moderate | 181 |
| `fedramp-high` | FedRAMP Rev 5 High | 191 |
| `cmmc-l1` | CMMC 2.0 Level 1 | 17 |
| `cmmc-l2` | CMMC 2.0 Level 2 | 110 |
| `cmmc-l3` | CMMC 2.0 Level 3 | 24 |

Always call `pretorin_list_frameworks` to get the current list rather than relying on this table.

## Control ID Formatting

Control and family IDs must be formatted correctly or the API will return errors. See `references/control-id-formats.md` for the full format guide. Key rules:

- **NIST/FedRAMP**: families are slugs (`access-control`), controls are zero-padded (`ac-01`)
- **CMMC**: families include level (`access-control-level-2`), controls are dotted (`AC.L2-3.1.1`)
- **800-171**: controls are dotted (`03.01.01`)

When unsure of an ID, discover it first with `pretorin_list_control_families` or `pretorin_list_controls`.
When the user already supplied a control ID and you have an active scope, try the exact control lookup in that active framework first. Do not silently remap the request to a different control or framework.

## Tools

### Browsing Frameworks
- **`pretorin_list_frameworks`** — List all available frameworks. No parameters. Start here when the user hasn't specified a framework.
- **`pretorin_get_framework`** — Get framework metadata and AI context (purpose, target audience, regulatory context, scope, key concepts). Pass `framework_id`.
- **`pretorin_list_control_families`** — List control families with AI context (domain summary, risk context, implementation priority). Pass `framework_id`.

### Querying Controls
- **`pretorin_list_controls`** — List controls for a framework. Pass `framework_id` and optionally `family_id` to filter by family.
- **`pretorin_get_control`** — Get full control details including AI guidance (summary, control intent, evidence expectations, implementation considerations, common failures, complexity). Pass `framework_id` and `control_id`. The `ai_guidance` field provides the richest context for generating narratives and analyzing gaps.
- **`pretorin_get_control_references`** — Get implementation guidance, objectives, and related controls. Pass `framework_id` and `control_id`. This is the most detailed view — use it to understand how to implement a control.

### Documentation
- **`pretorin_get_document_requirements`** — Get required and implied documents for a framework. Pass `framework_id`. Returns explicit (required) and implicit (control-implied) documents with their control references.

### Systems
- **`pretorin_list_systems`** — List systems in the organization. Start here when the user has not identified a target system.
- **`pretorin_get_system`** — Get system metadata including attached frameworks and security impact level. Pass a canonical `system_id` or a friendly system name.
- **`pretorin_get_compliance_status`** — Get framework progress and implementation posture for a system. Pass a canonical `system_id` or a friendly system name.

### System & Implementation Context
- **`pretorin_get_control_context`** — Get rich context for a control including AI guidance, statement, objectives, scope status, and current implementation details. Pass `system_id`, `control_id`, and `framework_id`. This is the most comprehensive view for understanding both what a control requires and how it's currently implemented.
- **`pretorin_get_scope`** — Get system scope/policy information including excluded controls and Q&A responses. Pass `system_id`. Useful for understanding what's in/out of scope before generating narratives.
- **`pretorin_get_control_implementation`** — Get implementation details including current narrative, evidence_count, and notes. Use this to read current state before writing updates.
- **`pretorin_get_narrative`** — Get the current narrative record for a control. Pass `system_id`, `control_id`, and `framework_id`.
- **`pretorin_get_control_notes`** — Get notes for a control implementation. Pass `system_id`, `control_id`, and optionally `framework_id`.
- **`pretorin_update_narrative`** — Push a narrative text update for a control implementation. Pass `system_id`, `control_id`, `framework_id`, and `narrative`. Use this after generating a narrative to save it to the platform.
- **`pretorin_create_evidence`** — Upsert evidence (find-or-create by default with `dedupe: true`) and return whether it was created or reused. Pass `system_id`, `name`, `description`, `evidence_type`, and control/framework context.
- **`pretorin_link_evidence`** — Link an existing evidence item to a control (low-level helper).
- **`pretorin_add_control_note`** — Add a note for unresolved gaps or manual follow-up actions.

### Evidence Search
- **`pretorin_search_evidence`** — Search evidence inside the active or explicit system/framework scope. Pass `system_id` when you want to override the active scope; friendly system names are accepted.

### Review, Monitoring, and Drafting
- **`pretorin_generate_control_artifacts`** — Generate read-only AI drafts for a control narrative and evidence-gap assessment using the same Codex workflow as the CLI. Use this when the user wants a draft without writing to the platform yet.
- **`pretorin_push_monitoring_event`** — Record a monitoring event for notable findings such as scans, access reviews, or configuration changes.
- **`pretorin_update_control_status`** — Update a control implementation status when findings justify a state change.

### Batch Operations
- **`pretorin_get_controls_batch`** — Get detailed control data for many controls in one framework-scoped request. Pass `framework_id` and optionally `control_ids` (omit to get all).
- **`pretorin_create_evidence_batch`** — Create and link multiple evidence items within one system/framework scope. Pass `system_id`, `framework_id`, and `items` array.

### Workflow State & Analytics
- **`pretorin_get_workflow_state`** — Get lifecycle state for a system+framework showing which stage needs work (scope, policies, controls, evidence) and the next recommended action.
- **`pretorin_get_analytics_summary`** — Lightweight system progress snapshot: scope completion, policy completion, control coverage, evidence gaps.
- **`pretorin_get_family_analytics`** — Per-family breakdown with narrative coverage, evidence coverage, and status distribution.
- **`pretorin_get_policy_analytics`** — Per-policy breakdown with answer completion and review status.

### Family Operations
- **`pretorin_get_pending_families`** — Identify which control families need work (returns counts of pending vs total controls).
- **`pretorin_get_family_bundle`** — Get all controls in one family with status, narrative presence, evidence presence, and note counts.
- **`pretorin_trigger_family_review`** — Trigger AI review of all controls in a family (2-4 minutes for large families). Returns a job ID.
- **`pretorin_get_family_review_results`** — Poll family review results with aggregated findings showing severity, affected control IDs, and recommended fixes.

### Scope Workflow
- **`pretorin_get_pending_scope_questions`** — Get only unanswered scope questions (lightweight).
- **`pretorin_get_scope_question_detail`** — Get guidance, tips, and examples for a specific scope question.
- **`pretorin_answer_scope_question`** — Answer one scope question with partial update support.
- **`pretorin_trigger_scope_generation`** — Trigger AI generation of scope document from answered questions.
- **`pretorin_trigger_scope_review`** — Trigger AI review of scope answers.
- **`pretorin_get_scope_review_results`** — Poll for structured scope review findings.

### Policy Workflow
- **`pretorin_get_pending_policy_questions`** — Get only unanswered policy questions.
- **`pretorin_get_policy_question_detail`** — Get guidance, tips, and examples for a specific policy question.
- **`pretorin_answer_policy_question`** — Answer one policy question.
- **`pretorin_get_policy_workflow_state`** — Check per-policy completion status, document generation, and review status.
- **`pretorin_trigger_policy_generation`** — Trigger AI generation of policy document from answered questions.
- **`pretorin_trigger_policy_review`** — Trigger AI review of policy answers/document.
- **`pretorin_get_policy_review_results`** — Poll for structured policy review findings.

### Campaign Operations
Campaigns enable bulk compliance operations across multiple controls, policies, or scope questions with checkpoint persistence and lease-based concurrency.

- **`pretorin_prepare_campaign`** — Prepare a workflow-aligned campaign run with platform context snapshot.
- **`pretorin_claim_campaign_items`** — Claim items for drafting with TTL-based leases.
- **`pretorin_get_campaign_item_context`** — Get full item context plus drafting instructions.
- **`pretorin_submit_campaign_proposal`** — Submit a proposal without applying to the platform.
- **`pretorin_apply_campaign`** — Push accepted proposals to the platform.
- **`pretorin_get_campaign_status`** — Get structured campaign status snapshot.

### Vendor Management
- **`pretorin_list_vendors`** — List all vendor entities (CSP, SaaS, managed services, internal).
- **`pretorin_create_vendor`** — Create a new vendor entity.
- **`pretorin_get_vendor`** — Get vendor details.
- **`pretorin_update_vendor`** — Update vendor fields.
- **`pretorin_delete_vendor`** — Delete a vendor entity.
- **`pretorin_upload_vendor_document`** — Upload vendor evidence documents.
- **`pretorin_list_vendor_documents`** — List documents linked to a vendor.
- **`pretorin_link_evidence_to_vendor`** — Link evidence to a vendor with attestation type.

### Inheritance & Responsibility
- **`pretorin_set_control_responsibility`** — Mark a control as inherited/shared from a provider.
- **`pretorin_get_control_responsibility`** — Check if a control is inherited and from where.
- **`pretorin_remove_control_responsibility`** — Convert inherited control to system-specific.
- **`pretorin_generate_inheritance_narrative`** — AI-generate inheritance narrative from vendor docs.
- **`pretorin_get_stale_edges`** — Identify controls with stale inheritance.
- **`pretorin_sync_stale_edges`** — Bulk update inherited controls from source narratives.

### STIG & CCI
- **`pretorin_list_stigs`** — List STIG benchmarks, filterable by technology area or product.
- **`pretorin_get_stig`** — Get STIG benchmark details.
- **`pretorin_list_stig_rules`** — List rules for a benchmark with severity/CCI filters.
- **`pretorin_get_stig_rule`** — Get full rule detail: check text, fix text, linked CCIs.
- **`pretorin_list_ccis`** — List CCI items, filterable by NIST 800-53 control.
- **`pretorin_get_cci`** — Get CCI detail with linked SRGs and STIG rules.
- **`pretorin_get_cci_chain`** — Full traceability: Control -> CCIs -> SRGs -> STIG rules.
- **`pretorin_get_cci_status`** — CCI-level compliance rollup for a system.
- **`pretorin_get_stig_applicability`** — Which STIGs apply to a system.
- **`pretorin_infer_stigs`** — AI-infer applicable STIGs from system profile.
- **`pretorin_get_test_manifest`** — Fetch test manifest for a system.
- **`pretorin_submit_test_results`** — Upload STIG scan results.

### Engagement (Routing)

**ALWAYS call `pretorin_start_task` FIRST** when the user references compliance work (a control, system, framework, questionnaire, or campaign). It picks the workflow for you so you don't have to guess.

- **`pretorin_start_task`** — Extract entities from the user prompt (intent_verb, system_id, framework_id, control_ids, scope_question_ids, policy_question_ids, raw_prompt) and pass them in. Pretorin runs deterministic rules and returns an `EngagementSelection` naming the workflow plus an `inspect_summary` of platform state. If `ambiguous: true` is returned, surface the `ambiguity_reason` to the user and ask for clarification — do NOT proceed to writes.

The response shape:

```
{
  "selected_workflow": "single-control" | "scope-question" | "policy-question" | "campaign" | null,
  "workflow_params": { ... },
  "inspect_summary": { workflow_state, compliance_status, pending_*, ... },
  "ambiguous": false,
  "rule_matched": "len(control_ids) == 1"
}
```

After `pretorin_start_task` returns a workflow, call `pretorin_get_workflow(selected_workflow)` to load the body and follow it.

Reference questions ("show me AC-2", "list frameworks") skip `pretorin_start_task` and go directly to read-side tools.

### Workflow Playbooks

Workflows describe **how to iterate items** in a domain (one control, scope questions, policy questions, the whole campaign). The engagement layer (`pretorin_start_task`) picks one for you; you can also browse them manually:

- **`pretorin_list_workflows`** — List loaded workflow playbooks with `description`, `use_when`, `iterates_over`, `recipes_commonly_used`. Filter by `iterates_over` to narrow.
- **`pretorin_get_workflow`** — Return one workflow's full manifest and body. The body is the prose playbook the calling agent reads.

Built-in workflows:
- `single-control` — Update one control's narrative + evidence + notes for one system.
- `scope-question` — Walk a system's scope questionnaire, one question at a time.
- `policy-question` — Walk an org policy's questionnaire, one question at a time.
- `campaign` — Bulk control work across many controls (server-side iteration via pretorin's CodexAgent).

### Recipes

Recipes are markdown-plus-Python playbooks for repeatable compliance work — capturing code as evidence, running scanners, collecting attestations. Pick a recipe over freelancing whenever one's `use_when` matches the task. Writes inside a recipe context get `producer_kind="recipe"` audit metadata stamped automatically.

- **`pretorin_list_recipes`** — List available recipes (built-in + project + user). Returns `id`, `name`, `description`, `use_when`, `tier`, `produces` for each. Start here to scan the menu.
- **`pretorin_get_recipe`** — Get full recipe detail including the markdown body and per-script tool names. Pass `recipe_id`. Read the body to understand what the recipe does before invoking it.
- **`pretorin_start_recipe`** — Open a recipe execution context. Pass `recipe_id`, `recipe_version`, and any required `params`. Returns a `context_id` that the agent forwards on subsequent writes (`recipe_context_id=...`) so audit metadata stamps correctly. Contexts auto-expire after 1 hour idle.
- **`pretorin_end_recipe`** — Close the recipe context. Pass `context_id` and `status` (`pass` / `fail` / `needs_input`). Returns a `RecipeResult` summary with evidence/narrative counts.
- **`pretorin_recipe_<safe_id>__<script>`** — Each recipe's scripts are auto-registered as MCP tools using this name pattern (hyphens in `recipe_id` become underscores). Inspect the recipe via `pretorin_get_recipe` to discover the tool names and per-script param schemas.

## Recipe Workflow

For any compliance task that fits a recipe (evidence capture, scanning, attestation), follow this lifecycle:

1. List the available recipes: `pretorin_list_recipes`.
2. Pick the one whose `description` and `use_when` match the task. Prefer `tier: official` over `community` when both fit, but read the descriptions — a community recipe with a precise match beats an official one with a vague match.
3. Read the recipe body: `pretorin_get_recipe`. The body is the prompt the recipe author wrote for you.
4. Open the context: `pretorin_start_recipe(recipe_id, recipe_version, params)` → returns `context_id`.
5. Invoke the recipe's scripts as MCP tools (`pretorin_recipe_<safe_id>__<script>`). Read each return value before deciding the next step.
6. Submit the results through the platform write tools (`pretorin_create_evidence`, `pretorin_submit_test_results`, `pretorin_update_narrative`) **inside** the same MCP session. Pass `recipe_context_id=<context_id>` so audit metadata stamps correctly.
7. Close the context: `pretorin_end_recipe(context_id, status)`.

Recipes available out of the box (always check `pretorin_list_recipes` for the current set):

- `code-evidence-capture` — Pull a snippet from a source file, redact secrets, compose audit-grade markdown.
- `inspec-baseline` — Run a Chef InSpec scan against a STIG and submit per-rule results.
- `openscap-baseline` — Same as above, with OpenSCAP.
- `cloud-aws-baseline` — AWS-cloud STIG checks against the configured account.
- `cloud-azure-baseline` — Azure-cloud STIG checks against the configured tenant/subscription.
- `manual-attestation` — Capture per-rule human attestations for STIGs that have no automated coverage.
- `scope-q-answer` — Redact secrets in a candidate scope-question answer before submission (used inside the `scope-question` workflow).
- `policy-q-answer` — Redact secrets in a candidate policy-question answer before submission (used inside the `policy-question` workflow).

## Recipe Authoring

When the user wants to **write** a recipe (rather than use one), point them at the authoring docs in `docs/src/recipes/` (or `https://docs.pretorin.com/recipes/` once published). The fast path is:

```bash
pretorin recipe new my-recipe         # scaffold under ~/.pretorin/recipes/
$EDITOR ~/.pretorin/recipes/my-recipe/recipe.md
$EDITOR ~/.pretorin/recipes/my-recipe/scripts/example.py
pretorin recipe validate my-recipe    # check manifest + scripts + descriptions
pretorin recipe run my-recipe         # exercise locally before invoking via MCP
```

Full reference at `docs/src/recipes/index.md`.

## Campaign Workflow

For bulk compliance operations, follow this lifecycle:

1. Check what needs work: `pretorin_get_workflow_state` and `pretorin_get_pending_families`
2. Prepare the campaign: `pretorin_prepare_campaign` with the target domain (controls, policy, or scope) and mode
3. Claim items: `pretorin_claim_campaign_items` to lease items for drafting
4. Get context: `pretorin_get_campaign_item_context` for each claimed item
5. Draft and submit: `pretorin_submit_campaign_proposal` for each item
6. Review status: `pretorin_get_campaign_status` to check progress
7. Apply: `pretorin_apply_campaign` to push all proposals to the platform

## Vendor Inheritance Workflow

For controls inherited from vendors (CSPs, SaaS providers):

1. Create the vendor: `pretorin_create_vendor`
2. Upload vendor documentation: `pretorin_upload_vendor_document` (SOC 2 reports, CRMs, FedRAMP packages)
3. Set responsibility: `pretorin_set_control_responsibility` to mark controls as inherited/shared
4. Generate narratives: `pretorin_generate_inheritance_narrative` to AI-draft grounded inheritance narratives
5. Monitor staleness: `pretorin_get_stale_edges` to find controls where source narratives changed
6. Sync updates: `pretorin_sync_stale_edges` to bulk update inherited controls

## Narrative + Evidence + Notes Workflow

For any control update, follow this exact sequence:

1. Resolve the target `system_id`, `control_id`, and `framework_id`
2. Read current state first:
   - `pretorin_get_control_context`
   - `pretorin_get_narrative` or `pretorin_get_control_implementation`
   - `pretorin_search_evidence`
   - `pretorin_get_control_notes`
3. Treat existing Pretorin narratives, notes, and status fields as a starting point, not proof that a control gap exists
4. Inspect the relevant implementation in the workspace and connected MCP systems, then collect only observable facts
5. If code or connected systems show stronger implementation than the current platform record, update the narrative to reflect the observed implementation and record any remaining evidence gap separately
6. Draft updates:
   - Narrative update (include TODO placeholders for unknowns)
   - Evidence upserts
   - Gap notes for unresolved/manual items
7. Push updates:
   - `pretorin_update_narrative`
   - `pretorin_create_evidence` (dedupe on by default; pass `control_id` whenever possible so the evidence auto-links)
   - `pretorin_link_evidence` for any additional controls that should reference the same evidence item
   - `pretorin_add_control_note`

## Read-Only Draft Workflow

When the user wants drafts before any platform writes:

1. Resolve `system_id`, `control_id`, and `framework_id`
2. Read current state first:
   - `pretorin_get_control_context`
   - `pretorin_get_narrative` or `pretorin_get_control_implementation`
   - `pretorin_search_evidence`
   - `pretorin_get_control_notes`
3. Call `pretorin_generate_control_artifacts`
4. Present the generated draft as read-only output and clearly separate:
   - candidate narrative text
   - evidence gaps
   - manual follow-up actions
5. Only call write tools (`pretorin_update_narrative`, `pretorin_create_evidence`, `pretorin_add_control_note`) if the user explicitly wants to persist changes

### No-Hallucination Requirements

- Never claim an implementation detail unless it is directly observed.
- Mark uncertain or missing information as unknown.
- Existing Pretorin narratives, notes, and status values are not by themselves evidence that a gap exists.
- Before writing a narrative update or gap note, inspect the relevant implementation in the workspace and connected MCP systems.
- If observed implementation is stronger than the current platform record, update the narrative to match the observed implementation and note any remaining evidence gap separately.
- Use auditor-friendly markdown with no section headings.
- Narratives must include at least two rich markdown elements and at least one structural element (`code block`, `table`, or `list`).
- Evidence descriptions must include at least one rich markdown element.
- Rich markdown elements include: fenced code blocks, tables, lists, and links.
- Do not include markdown images until platform-side image evidence upload support is available.
- For missing narrative data, insert this exact block:

```text
[[PRETORIN_TODO]]
missing_item: <what is missing>
reason: Not observable from current workspace and connected MCP systems
required_manual_action: <what user must do on platform/integrations>
suggested_evidence_type: <policy_document|configuration|...>
[[/PRETORIN_TODO]]
```

- For each unresolved gap, add one control note in this format:

```text
Gap: <short title>
Observed: <what was verifiably found>
Missing: <what could not be verified>
Why missing: <access/system limitation>
Manual next step: <explicit user/platform action>
```

## Workflows

### Framework Selection
Help users pick the right framework for their situation. See `references/framework-selection-guide.md` for the full decision tree covering federal agencies, contractors, CSPs, and defense industrial base organizations.

### Compliance Gap Analysis
Systematically assess a codebase against a framework's controls. See `references/gap-analysis-workflow.md` for the step-by-step methodology including family prioritization, evidence collection patterns, and status assessment criteria. See `examples/gap-analysis.md` for a sample output.

### Compliance Artifact Generation
Produce structured JSON artifacts documenting how a specific control is implemented. See `references/artifact-schema.md` for the full schema and field guidelines. See `examples/artifact-example.md` for complete examples with good vs weak evidence.

### Cross-Framework Mapping
Map controls across related frameworks using the related controls returned by `pretorin_get_control_references`. See `examples/cross-framework-mapping.md` for a worked example mapping Account Management across four frameworks.

### Document Readiness Assessment
Assess documentation readiness by calling `pretorin_get_document_requirements`, then prioritize: required documents first, then documents referenced by the most controls.

## MCP Resources

Access these via `ReadMcpResourceTool` with `server: "pretorin"`:

| Resource URI | Purpose |
|---|---|
| `analysis://schema` | JSON schema for compliance artifacts |
| `analysis://guide/{framework_id}` | Framework-specific analysis guidance (`fedramp-moderate`, `nist-800-53-r5`, `nist-800-171-r3`) |
| `analysis://control/{framework_id}/{control_id}` | Control-specific analysis guidance with search patterns and evidence examples for one framework scope |
