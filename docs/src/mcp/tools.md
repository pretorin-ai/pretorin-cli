# MCP Tool Reference

The MCP server provides 23 tools organized by category.

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

### pretorin_get_system

Get system metadata including attached frameworks and security impact level.

**Parameters:**
- `system_id` (required) — System ID or name

**Returns:** System metadata.

---

### pretorin_get_compliance_status

Get framework progress and implementation posture for a system.

**Parameters:**
- `system_id` (required)

**Returns:** Framework status summaries and progress metrics.

---

## Evidence Management

### pretorin_search_evidence

Search current evidence items.

**Parameters:**
- `system_id` (optional) — System context
- `control_id` (optional) — Filter by control
- `framework_id` (optional) — Filter by framework

**Returns:** Matching evidence items.

---

### pretorin_create_evidence

Upsert evidence on the platform (find-or-create by default). If `dedupe` is true, exact matching evidence in the active system/framework scope is reused; otherwise a new record is created.

**Parameters:**
- `system_id` (required)
- `name` (required)
- `description` (required) — Must be auditor-ready markdown (no headings, at least one rich element, no images)
- `evidence_type` (optional) — Default: `policy_document`
- `control_id` (optional)
- `framework_id` (optional)
- `dedupe` (optional) — Default: `true`

**Returns:**
- `evidence_id`
- `created` — true if new, false if reused
- `linked` — whether control/system link succeeded
- `match_basis` — `exact_name_desc_type_control_framework` or `none`

---

### pretorin_link_evidence

Link an existing evidence item to a control.

**Parameters:**
- `system_id` (required)
- `evidence_id` (required)
- `control_id` (required)
- `framework_id` (optional)

**Returns:** Link confirmation.

---

### pretorin_get_narrative

Get the current narrative record for a control.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Narrative text, status, and AI confidence metadata.

---

## Implementation Context

### pretorin_get_control_context

Get rich context for a control including AI guidance, statement, objectives, scope status, and current implementation details.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Combined control metadata and implementation details.

---

### pretorin_get_scope

Get system scope and policy information including excluded controls and Q&A responses.

**Parameters:**
- `system_id` (required)

**Returns:** Scope narrative, excluded controls, Q&A responses, and scope status.

---

### pretorin_get_control_implementation

Get implementation details for a control in a system.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)

**Returns:** Current status, narrative, evidence count, and notes metadata.

---

### pretorin_get_control_notes

Get notes for a control implementation.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (optional)

**Returns:** Note list with `total` count.

---

### pretorin_update_narrative

Push a narrative text update for a control implementation.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)
- `narrative` (required) — Must be auditor-ready markdown (no headings, 2+ rich elements, 1+ structural element, no images)
- `is_ai_generated` (optional) — Default: `false`

**Returns:** Update confirmation.

---

### pretorin_add_control_note

Add a note for unresolved gaps or manual follow-up actions.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `framework_id` (required)
- `content` (required)

**Returns:** The created note record.

---

## Compliance Updates

### pretorin_update_control_status

Update the implementation status for a control.

**Parameters:**
- `system_id` (required)
- `control_id` (required)
- `status` (required)
- `framework_id` (optional)

**Returns:** Status update confirmation.

---

### pretorin_push_monitoring_event

Create a monitoring event for a system.

**Parameters:**
- `system_id` (required)
- `title` (required)
- `severity` (optional) — `critical`, `high`, `medium`, `low`, `info`
- `event_type` (optional) — `security_scan`, `configuration_change`, `access_review`, `compliance_check`
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
