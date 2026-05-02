# MCP Tool Reference

The MCP server provides 94 tools organized by category.

## Task Routing

### pretorin_start_task

Route a user prompt to the right workflow. **Call this FIRST** whenever the user references compliance work (a control, system, framework, questionnaire, or campaign). The calling agent extracts entities from the user prompt and supplies them as structured args; pretorin applies deterministic rules to pick a workflow and bundles the platform read-state (workflow_state, compliance_status, pending items) into the response. The agent then reads the selected workflow's body via `pretorin_get_workflow` and follows it.

The one exception is pure reference questions ("show me AC-2", "list frameworks") — those go directly to the read-side tools without `start_task`.

**Parameters:**
- `entities` (required) — Structured entities extracted from the user prompt. Required sub-fields: `intent_verb` (one of `work_on`, `collect_evidence`, `draft_narrative`, `answer`, `campaign`, `inspect_status`) and `raw_prompt` (original verbatim text). Optional: `system_id`, `framework_id`, `control_ids`, `scope_question_ids`, `policy_question_ids`.
- `active_system_id` (optional) — The user's active CLI context system_id, if any. Used to detect cross-system writes.
- `skip_inspect` (optional) — Skip the server-side platform reads when the calling agent already has fresh state. Default: `false`

**Returns:** Selected workflow id, resolved scope (system/framework/items), and a platform-state bundle for the agent to act on.

---

## Framework & Control Reference

These tools are read-only and available to all authenticated users.

### pretorin_list_frameworks

List all available compliance frameworks.

**Parameters:** None

**Returns:** List of frameworks with ID, title, version, tier, and control counts.

---

### pretorin_get_framework

Get detailed metadata about a specific framework including AI context (purpose, target audience, regulatory context).

**Parameters:**
- `framework_id` (required) — e.g., `nist-800-53-r5`, `fedramp-moderate`

**Returns:** Framework details including description, version, OSCAL version, and dates.

---

### pretorin_list_control_families

List control families for a framework with AI context (domain summary, risk context, implementation priority).

**Parameters:**
- `framework_id` (required)

**Returns:** List of control families with ID, title, class, and control count.

---

### pretorin_list_controls

List controls for a framework, optionally filtered by family.

**Parameters:**
- `framework_id` (required)
- `family_id` (optional) — Family IDs are slugs like `access-control`, not short codes. CMMC families include a level suffix (e.g., `access-control-level-2`).

**Returns:** List of controls with ID, title, and family.

---

### pretorin_get_control

Get detailed control information including AI guidance (summary, control intent, evidence expectations, implementation considerations, common failures, complexity).

**Parameters:**
- `framework_id` (required)
- `control_id` (required) — NIST/FedRAMP: zero-padded (`ac-01`). CMMC: dotted (`AC.L2-3.1.1`).

**Returns:** Control details including parameters, parts, and enhancement count.

---

### pretorin_get_controls_batch

Get detailed control data for many controls in one framework-scoped request.

**Parameters:**
- `framework_id` (required)
- `control_ids` (optional) — List of canonical control IDs; omit to retrieve all controls in the framework

**Returns:** Full control detail records for the requested controls.

---

### pretorin_get_control_references

Get reference information including statement, guidance, objectives, and related controls.

**Parameters:**
- `framework_id` (required)
- `control_id` (required)

**Returns:** Statement, guidance, objectives, parameters, and related controls.

---

### pretorin_get_document_requirements

Get document requirements for a framework.

**Parameters:**
- `framework_id` (required)

**Returns:** List of explicit and implicit document requirements with control references.

---

## Systems

### pretorin_list_systems

List systems in the current organization.

**Parameters:** None

**Returns:** System IDs, names, and summary metadata.

---

### pretorin_get_cli_status

Return the local Pretorin CLI version status, including update availability and upgrade guidance for MCP hosts and agents.

**Parameters:**
- `force` (optional) — Bypass local cache and re-check PyPI for the latest version. Default: `false`

**Returns:** Current version, latest version, update available flag, and upgrade instructions.

---

### pretorin_get_source_manifest

Get the resolved source manifest for a system and evaluate it against currently detected sources. Shows which external sources (git, cloud, HRIS, etc.) are required, recommended, or optional, and whether each is currently satisfied.

**Parameters:**
- `system_id` (optional) — System ID or name

**Returns:** Source manifest with per-source satisfaction status. Returns null manifest if none is configured.

---

### pretorin_get_system

Get system metadata including attached frameworks and security impact level.

**Parameters:**
- `system_id` (required) — System ID or name

**Returns:** System metadata.

---

### pretorin_get_compliance_status

Get framework progress and implementation posture for a system.

**Parameters:**
- `system_id` (required) — System ID or friendly system name

**Returns:** Framework status summaries and progress metrics.

---

## Evidence Management

### pretorin_search_evidence

Search current evidence items.

**Parameters:**
- `system_id` (optional) — System ID or friendly system name. When omitted, the active CLI scope is used if available.
- `control_id` (optional) — Filter by control
- `framework_id` (optional) — Filter by framework
- `limit` (optional) — Maximum number of results. Default: `20`

**Returns:** Matching evidence items. The server uses the same compatibility search path as the CLI for deployments that only expose system-scoped evidence routes.

---

### pretorin_create_evidence

Upsert evidence on the platform (find-or-create by default). If `dedupe` is true, exact matching evidence in the active system/framework scope is reused; otherwise a new record is created.

**Parameters:**
- `name` (required)
- `description` (required) — Must be auditor-ready markdown (no headings, at least one rich element, no images)
- `evidence_type` (required) — Must be one of the canonical evidence types
- `system_id` (optional) — Defaults to active scope
- `control_id` (optional)
- `framework_id` (optional)
- `dedupe` (optional) — Default: `true`

**Returns:**
- `evidence_id`
- `created` — true if new, false if reused
- `linked` — whether control/system link succeeded
- `match_basis` — `exact_name_desc_type_control_framework` or `none`

---

### pretorin_create_evidence_batch

Create and link multiple evidence items within one system/framework scope in a single request.

**Parameters:**
- `items` (required) — Array of evidence payloads with `name`, `description`, and `control_id`; may also include `evidence_type` and `relevance_notes`
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** Batch creation summary with per-item results and created evidence IDs.

---

### pretorin_link_evidence

Link an existing evidence item to a control.

**Parameters:**
- `evidence_id` (required)
- `control_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional)

**Returns:** Link confirmation.

---

### pretorin_upload_evidence

Upload a file as evidence to the platform (system-scoped, requires WRITE access).

**Parameters:**
- `file_path` (required) — Absolute path to the file to upload
- `name` (required) — Evidence name
- `system_id` (optional) — Defaults to active scope
- `evidence_type` (optional) — Default: `other`
- `description` (optional) — Evidence description
- `control_id` (optional)
- `framework_id` (optional)

**Returns:** Uploaded evidence record.

---

### pretorin_delete_evidence

Delete an evidence item from the platform (system-scoped, requires WRITE access).

**Parameters:**
- `evidence_id` (required) — The evidence item ID to delete
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** Deletion confirmation.

---

### pretorin_get_narrative

Get the current narrative record for a control.

**Parameters:**
- `control_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** Narrative text, status, and AI confidence metadata.

---

## Implementation Context

### pretorin_get_control_context

Get rich context for a control including AI guidance, statement, objectives, scope status, and current implementation details.

**Parameters:**
- `control_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** Combined control metadata and implementation details.

---

### pretorin_get_scope

Get system scope and policy information including excluded controls and Q&A responses.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Scope narrative, excluded controls, Q&A responses, and scope status.

---

### pretorin_patch_scope_qa

Apply partial scope questionnaire updates for a system/framework.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)
- `updates` (required) — Non-empty list of `{question_id, answer}` objects

**Returns:** Updated scope questionnaire state, including the saved responses.

---

### pretorin_list_org_policies

List organization policies available for questionnaire work.

**Parameters:** None

**Returns:** Policy summaries including `id`, `name`, template linkage, and questionnaire status.

---

### pretorin_get_org_policy_questionnaire

Get the canonical questionnaire state for one organization policy.

**Parameters:**
- `policy_id` (required)

**Returns:** Policy metadata, saved answers, and the merged template/question set when available.

---

### pretorin_patch_org_policy_qa

Apply partial questionnaire updates for one organization policy.

**Parameters:**
- `policy_id` (required)
- `updates` (required) — Non-empty list of `{question_id, answer}` objects

**Returns:** Updated organization policy questionnaire state.

---

### pretorin_get_control_implementation

Get implementation details for a control in a system.

**Parameters:**
- `control_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** Current status, narrative, evidence count, and notes metadata.

---

### pretorin_get_control_notes

Get notes for a control implementation.

**Parameters:**
- `control_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional)

**Returns:** Note list with `total` count.

---

### pretorin_update_narrative

Push a narrative text update for a control implementation.

**Parameters:**
- `control_id` (required)
- `narrative` (required) — Must be auditor-ready markdown (no headings, 2+ rich elements, 1+ structural element, no images)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope
- `is_ai_generated` (optional) — Default: `false`

**Returns:** Update confirmation.

---

### pretorin_add_control_note

Add a note for unresolved gaps or manual follow-up actions. Content is plain text (no markdown validation required).

**Parameters:**
- `control_id` (required)
- `content` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope

**Returns:** The created note record.

---

### pretorin_resolve_control_note

Resolve, unresolve, or update an existing control note. Use this to clear blocking notes so control status can advance.

**Parameters:**
- `control_id` (required)
- `note_id` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope
- `is_resolved` (optional) — Default: `true`
- `content` (optional) — Updated note content
- `is_pinned` (optional)

**Returns:** The updated note record.

---

## Compliance Updates

### pretorin_update_control_status

Update the implementation status for a control.

**Parameters:**
- `control_id` (required)
- `status` (required) — `implemented`, `in_progress`, `inherited`, `not_applicable`, `not_started`, `partially_implemented`, `planned`, `ready_to_approve`
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional)

**Returns:** Status update confirmation.

---

### pretorin_push_monitoring_event

Create a monitoring event for a system.

**Parameters:**
- `title` (required)
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope
- `severity` (optional) — `critical`, `high`, `medium`, `low`, `info`. Default: `medium`
- `event_type` (optional) — `security_scan`, `configuration_change`, `access_review`, `compliance_check`. Default: `security_scan`
- `control_id` (optional)
- `description` (optional)

**Returns:** The created monitoring event.

---

### pretorin_generate_control_artifacts

Generate read-only AI drafts for a control narrative and evidence-gap assessment.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)
- `working_directory` (optional) — Local workspace path for code-aware drafting
- `model` (optional) — Model override

**Returns:** Draft narrative text plus evidence-gap analysis. Does not write to the platform.

Use `pretorin_update_narrative`, `pretorin_create_evidence`, and `pretorin_add_control_note` to persist approved changes.

---

## Workflow State & Analytics

### pretorin_get_workflow_state

Get the lifecycle state for a system+framework, showing which stage needs work next (scope, policies, controls, evidence).

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Current workflow stage, completion percentages, and next recommended action.

---

### pretorin_get_analytics_summary

Get a lightweight system progress snapshot.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Scope completion, policy completion, control coverage, and evidence gaps.

---

### pretorin_get_family_analytics

Get per-family breakdown with narrative coverage, evidence coverage, and status distribution.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Per-family metrics.

---

### pretorin_get_policy_analytics

Get per-policy breakdown with answer completion and review status.

**Parameters:**
- `policy_id` (required)

**Returns:** Per-policy completion metrics.

---

## Family Operations

### pretorin_get_pending_families

Identify which control families need work.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Families with counts of pending vs total controls.

---

### pretorin_get_family_bundle

Get all controls in one family with status, narrative presence, evidence presence, and note counts.

**Parameters:**
- `system_id` (required)
- `family_id` (required)
- `framework_id` (required)

**Returns:** Complete family bundle with per-control details.

---

### pretorin_trigger_family_review

Trigger AI review of all controls in a family. Takes 2-4 minutes for large families.

**Parameters:**
- `system_id` (required)
- `family_id` (required)
- `framework_id` (required)

**Returns:** Review job ID for polling.

---

### pretorin_get_family_review_results

Poll family review results.

**Parameters:**
- `system_id` (required)
- `job_id` (required)

**Returns:** Aggregated findings with severity, affected control IDs, and recommended fixes.

---

## Scope Workflow

### pretorin_get_pending_scope_questions

Get only unanswered scope questions (lightweight).

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** List of unanswered questions with IDs.

---

### pretorin_get_scope_question_detail

Get guidance, tips, and example responses for a specific scope question.

**Parameters:**
- `system_id` (required)
- `question_id` (required)
- `framework_id` (required)

**Returns:** Question text, guidance, tips, and example answers.

---

### pretorin_answer_scope_question

Answer one scope question.

**Parameters:**
- `system_id` (required)
- `question_id` (required)
- `answer` (required)
- `framework_id` (required)

**Returns:** Updated question state.

---

### pretorin_trigger_scope_generation

Trigger AI generation of scope document from answered questions.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Generation job ID for polling.

---

### pretorin_trigger_scope_review

Trigger AI review of scope answers.

**Parameters:**
- `system_id` (required)
- `framework_id` (required)

**Returns:** Review job ID for polling.

---

### pretorin_get_scope_review_results

Poll for structured scope review findings.

**Parameters:**
- `system_id` (required)
- `job_id` (required)

**Returns:** Findings with severity levels and recommended fixes.

---

## Policy Workflow

### pretorin_get_pending_policy_questions

Get only unanswered policy questions.

**Parameters:**
- `policy_id` (required)

**Returns:** List of unanswered questions.

---

### pretorin_get_policy_question_detail

Get guidance, tips, and examples for a specific policy question.

**Parameters:**
- `policy_id` (required)
- `question_id` (required)

**Returns:** Question text, guidance, and example answers.

---

### pretorin_answer_policy_question

Answer one policy question.

**Parameters:**
- `policy_id` (required)
- `question_id` (required)
- `answer` (required)

**Returns:** Updated question state.

---

### pretorin_get_policy_workflow_state

Get per-policy workflow state including completion, generation, and review status.

**Parameters:**
- `policy_id` (required)

**Returns:** Policy workflow state.

---

### pretorin_trigger_policy_generation

Trigger AI generation of policy document from answered questions.

**Parameters:**
- `policy_id` (required)
- `system_id` (optional) — System ID for scope context

**Returns:** Generation job status.

---

### pretorin_trigger_policy_review

Trigger AI review of policy answers/document.

**Parameters:**
- `policy_id` (required)

**Returns:** Review job ID for polling.

---

### pretorin_get_policy_review_results

Poll for structured policy review findings.

**Parameters:**
- `policy_id` (required)
- `job_id` (required)

**Returns:** Findings with severity levels and recommended fixes.

---

## Campaign Operations

Campaigns enable bulk compliance operations with checkpoint persistence and lease-based concurrency.

### pretorin_prepare_campaign

Prepare a workflow-aligned campaign run with a platform state snapshot.

**Parameters:**
- `domain` (required) — `controls`, `policy`, or `scope`
- `mode` (required) — Campaign mode for the selected domain
- `system_id` (optional) — Defaults to active scope
- `framework_id` (optional) — Defaults to active scope
- `family_id` (optional) — Target family for control campaigns
- `control_ids` (optional) — Explicit control IDs to include
- `all_controls` (optional) — Include all controls. Default: `false`
- `artifacts` (optional) — Artifact type: `narratives`, `evidence`, or `both`. Default: `both`
- `review_job` (optional) — Family review job ID for `review-fix` mode
- `policy_ids` (optional) — Explicit policy IDs to include
- `all_incomplete` (optional) — Include all incomplete items. Default: `false`
- `apply` (optional) — Apply proposals immediately. Default: `false`
- `output` (optional) — Output format: `auto`, `live`, `compact`, `json`. Default: `json`
- `checkpoint_path` (optional) — Local checkpoint file path
- `working_directory` (optional) — Working directory for executors
- `concurrency` (optional) — Parallel execution limit. Default: `4`
- `max_retries` (optional) — Retry limit per item. Default: `2`

**Returns:** Campaign checkpoint with item list and metadata.

---

### pretorin_claim_campaign_items

Claim items for drafting with TTL-based leases. Safe for fan-out to multiple agents.

**Parameters:**
- `checkpoint_path` (required) — Local campaign checkpoint path
- `lease_owner` (optional) — Stable identifier for the claiming agent
- `max_items` (optional) — Number of items to claim. Default: `1`
- `lease_ttl_seconds` (optional) — Lease time-to-live. Default: `300`

**Returns:** Claimed items with lease metadata.

---

### pretorin_get_campaign_item_context

Get full item context plus drafting instructions for a claimed item.

**Parameters:**
- `checkpoint_path` (required)
- `item_id` (required)

**Returns:** Control/policy/scope context, current state, and drafting guidance.

---

### pretorin_submit_campaign_proposal

Submit an external agent's proposal without applying it to the platform.

**Parameters:**
- `checkpoint_path` (required)
- `item_id` (required)
- `proposal` (required) — Campaign proposal payload object

**Returns:** Proposal acceptance confirmation.

---

### pretorin_apply_campaign

Push stored proposals to the platform.

**Parameters:**
- `checkpoint_path` (required)
- `item_ids` (optional) — Subset of item IDs to apply; omit to apply all

**Returns:** Apply results with per-item status.

---

### pretorin_get_campaign_status

Get structured campaign status with a stable transcript snapshot.

**Parameters:**
- `checkpoint_path` (required)

**Returns:** Campaign progress, item states, and transcript.

---

## Vendor Management

### pretorin_list_vendors

List all vendor entities in the organization.

**Parameters:** None

**Returns:** Vendor list with IDs, names, types, and authorization levels.

---

### pretorin_create_vendor

Create a new vendor entity.

**Parameters:**
- `name` (required)
- `provider_type` (required) — `csp`, `saas`, `managed_service`, `internal`
- `description` (optional)
- `authorization_level` (optional)

**Returns:** Created vendor record.

---

### pretorin_get_vendor

Get vendor details.

**Parameters:**
- `vendor_id` (required)

**Returns:** Vendor metadata and linked documents.

---

### pretorin_update_vendor

Update vendor fields.

**Parameters:**
- `vendor_id` (required)
- `name` (optional)
- `description` (optional)
- `provider_type` (optional) — `csp`, `saas`, `managed_service`, `internal`
- `authorization_level` (optional)

**Returns:** Updated vendor record.

---

### pretorin_delete_vendor

Delete a vendor entity.

**Parameters:**
- `vendor_id` (required)

**Returns:** Deletion confirmation.

---

### pretorin_upload_vendor_document

Upload vendor evidence documents (SOC 2 reports, CRMs, FedRAMP packages).

**Parameters:**
- `vendor_id` (required)
- `file_path` (required)
- `name` (optional)
- `description` (optional)
- `attestation_type` (optional) — `self_attested`, `third_party_attestation`, `vendor_provided`. Default: `vendor_provided`

**Returns:** Uploaded document record.

---

### pretorin_list_vendor_documents

List documents linked to a vendor.

**Parameters:**
- `vendor_id` (required)

**Returns:** Document list with metadata.

---

### pretorin_link_evidence_to_vendor

Link an evidence item to a vendor with attestation type. Set `vendor_id` to null to unlink.

**Parameters:**
- `evidence_id` (required)
- `vendor_id` (optional) — Vendor ID; null to unlink
- `attestation_type` (optional) — `self_attested`, `third_party_attestation`, `vendor_provided`

**Returns:** Link confirmation.

---

## Inheritance & Responsibility

### pretorin_set_control_responsibility

Create or update an inheritance edge for a control.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)
- `responsibility_mode` (required) — `inherited` or `shared`
- `source_type` (optional) — `provider`, `internal`, or `hybrid`
- `vendor_id` (optional) — Vendor providing the inherited control

**Returns:** Created responsibility edge.

---

### pretorin_get_control_responsibility

Check if a control is inherited and from where.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Responsibility edge details or null.

---

### pretorin_remove_control_responsibility

Convert an inherited control back to system-specific.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Removal confirmation.

---

### pretorin_generate_inheritance_narrative

AI-generate an inheritance narrative grounded in vendor documentation.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Draft inheritance narrative text.

---

### pretorin_get_stale_edges

Identify controls where the source narrative changed but the inherited control hasn't been updated.

**Parameters:**
- `system_id` (required)

**Returns:** List of stale inheritance edges with source change timestamps.

---

### pretorin_sync_stale_edges

Bulk update inherited controls by regenerating narratives from latest source.

**Parameters:**
- `system_id` (required)

**Returns:** Sync results with per-control status.

---

## STIG & CCI

### pretorin_list_stigs

List STIG benchmarks with optional filters.

**Parameters:**
- `technology_area` (optional) — Filter by technology area
- `product` (optional) — Filter by product name
- `limit` (optional) — Default: `100`
- `offset` (optional) — Pagination offset. Default: `0`

**Returns:** STIG benchmark list with IDs, titles, and rule counts.

---

### pretorin_get_stig

Get STIG benchmark detail.

**Parameters:**
- `stig_id` (required)

**Returns:** Benchmark metadata including title, version, release info, and severity breakdown.

---

### pretorin_list_stig_rules

List rules for a STIG benchmark.

**Parameters:**
- `stig_id` (required)
- `severity` (optional) — Filter by severity (`high`, `medium`, `low`)
- `cci_id` (optional) — Filter by CCI identifier
- `limit` (optional) — Default: `100`
- `offset` (optional) — Pagination offset. Default: `0`

**Returns:** Rule list with IDs, titles, severities, and linked CCIs.

---

### pretorin_get_stig_rule

Get full STIG rule detail.

**Parameters:**
- `stig_id` (required)
- `rule_id` (required)

**Returns:** Check text, fix text, discussion, and linked CCIs.

---

### pretorin_list_ccis

List CCIs with optional filters.

**Parameters:**
- `nist_control_id` (optional) — Filter by NIST 800-53 control ID (e.g., `AC-2`)
- `status` (optional)
- `limit` (optional) — Default: `100`
- `offset` (optional) — Pagination offset. Default: `0`

**Returns:** CCI list with definitions and linked controls.

---

### pretorin_get_cci

Get CCI detail with linked SRGs and STIG rules.

**Parameters:**
- `cci_id` (required) — e.g., `CCI-000015`

**Returns:** CCI definition, linked SRGs, and linked STIG rules.

---

### pretorin_get_cci_chain

Get the full traceability chain: Control -> CCIs -> SRGs -> STIG rules.

**Parameters:**
- `nist_control_id` (required) — NIST 800-53 control ID (e.g., `AC-2`)

**Returns:** Complete traceability from control requirements to technical checks.

---

### pretorin_get_cci_status

Get CCI-level compliance rollup for a system.

**Parameters:**
- `system_id` (required)
- `nist_control_id` (optional) — Filter by NIST control ID (e.g., `AC-2`)

**Returns:** Per-CCI pass/fail status.

---

### pretorin_get_stig_applicability

Get which STIGs apply to a system based on its profile.

**Parameters:**
- `system_id` (required)

**Returns:** List of applicable STIG benchmarks.

---

### pretorin_infer_stigs

AI-infer applicable STIGs from the system's profile.

**Parameters:**
- `system_id` (required)

**Returns:** Recommended STIG benchmarks with reasoning.

---

### pretorin_get_test_manifest

Fetch the test manifest (applicable STIGs + rules) for a system.

**Parameters:**
- `system_id` (required)
- `stig_id` (optional) — Scope manifest to a specific STIG benchmark

**Returns:** Test manifest with applicable rules and scanner assignments.

---

### pretorin_submit_test_results

Upload STIG scan results to the platform.

**Parameters:**
- `system_id` (required)
- `cli_run_id` (required) — CLI scan run identifier
- `results` (required) — Array of test result objects
- `cli_version` (optional) — CLI version string

**Returns:** Submission confirmation with per-result status.

---

## Recipes & Workflows

Recipes are markdown playbooks the calling agent reads and executes; workflows describe how to iterate items in a domain and which recipes to pick per item. See [RFC 0001](https://github.com/pretorin/pretorin-cli/blob/master/docs/rfcs/0001-recipes.md) for the contract spec and `docs/src/recipes/` for authoring guides.

### pretorin_list_recipes

List loaded recipes with their summary metadata (id, name, tier, description, use_when, produces). Use this to discover which recipes are available, then call `pretorin_get_recipe(id)` to read the full body.

**Parameters:**
- `tier` (optional) — Filter to one tier: `official`, `partner`, or `community`
- `produces` (optional) — Filter by what the recipe produces: `evidence`, `narrative`, `both`, or `answers`

**Returns:** Recipe summaries with manifest metadata.

---

### pretorin_get_recipe

Return one recipe's full manifest and body. The body is the markdown playbook the calling agent reads to understand the procedure.

**Parameters:**
- `recipe_id` (required) — Recipe id to fetch

**Returns:** Recipe manifest plus the markdown body.

---

### pretorin_start_recipe

Open a recipe execution context. Returns a `context_id` the caller passes on subsequent platform-API write tool calls so audit metadata is stamped with `producer_kind='recipe'` automatically. One recipe per session at a time (nesting forbidden in v1). Contexts auto-expire after 1 hour of inactivity.

**Parameters:**
- `recipe_id` (required) — Recipe id (must be loadable from the registry)
- `recipe_version` (required) — Recipe version the caller intends to run. Cross-checked against the loaded recipe; mismatch is an error.
- `params` (optional) — Inputs the calling agent supplies, validated against the recipe's params schema
- `selection` (optional) — Structured `RecipeSelection` record from the engagement layer, stored on the context for the eventual `RecipeResult`

**Returns:** Context id and the resolved recipe manifest snapshot.

---

### pretorin_end_recipe

Close a recipe execution context and return the `RecipeResult` summary (status, evidence and narrative counts, errors, elapsed time). Must be called once the recipe's work is complete; failure to call leaves the context in place until the 1-hour expiry sweep.

**Parameters:**
- `context_id` (required) — Context id returned by `pretorin_start_recipe`
- `status` (optional) — Caller-supplied disposition: `pass`, `fail`, or `needs_input`. Default: `pass`

**Returns:** `RecipeResult` summary.

---

### pretorin_list_workflows

List loaded workflow playbooks (single-control, scope-question, policy-question, campaign). Each workflow describes how to iterate items in its domain and which recipes to pick per item. Use this before picking a recipe so the agent works at the right granularity.

**Parameters:**
- `iterates_over` (optional) — Filter to one item-iteration shape: `single_control`, `scope_questions`, `policy_questions`, or `campaign_items`

**Returns:** Workflow summaries with manifest metadata.

---

### pretorin_get_workflow

Return one workflow's full manifest and body. The body is the markdown playbook the calling agent reads to know how to iterate items and pick recipes per item in this workflow's domain.

**Parameters:**
- `workflow_id` (required) — Workflow id to fetch

**Returns:** Workflow manifest plus the markdown body.
