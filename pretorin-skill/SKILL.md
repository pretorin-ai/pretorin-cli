---
name: pretorin
description: >
  This skill should be used when the user asks about compliance frameworks,
  security controls, control families, document requirements, FedRAMP, NIST 800-53,
  NIST 800-171, CMMC, or wants to perform a compliance gap analysis, generate
  compliance artifacts, map controls across frameworks, or check what documents
  are needed for certification. Trigger phrases include "list frameworks",
  "show controls", "what documents do I need", "compliance check",
  "control requirements", "gap analysis", and "audit my code".
version: 0.8.6
---

# Pretorin Compliance Skill

Query authoritative compliance framework data via the Pretorin MCP server. Access controls, families, document requirements, and implementation guidance from NIST 800-53, NIST 800-171, FedRAMP, and CMMC.

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

## Narrative + Evidence + Notes Workflow

For any control update, follow this exact sequence:

1. Resolve the target `system_id`, `control_id`, and `framework_id`
2. Read current state first:
   - `pretorin_get_control_context`
   - `pretorin_get_narrative` or `pretorin_get_control_implementation`
   - `pretorin_search_evidence`
   - `pretorin_get_control_notes`
3. Collect only observable facts from the codebase and connected MCP systems
4. Draft updates:
   - Narrative update (include TODO placeholders for unknowns)
   - Evidence upserts
   - Gap notes for unresolved/manual items
5. Push updates:
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
