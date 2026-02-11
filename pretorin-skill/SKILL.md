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
version: 0.1.0
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
- **`pretorin_get_framework`** — Get framework metadata (description, version, dates). Pass `framework_id`.
- **`pretorin_list_control_families`** — List control families within a framework. Pass `framework_id`. Returns family IDs, titles, and control counts.

### Querying Controls
- **`pretorin_list_controls`** — List controls for a framework. Pass `framework_id` and optionally `family_id` to filter by family.
- **`pretorin_get_control`** — Get full control details (parameters, parts, enhancements). Pass `framework_id` and `control_id`.
- **`pretorin_get_control_references`** — Get implementation guidance, objectives, and related controls. Pass `framework_id` and `control_id`. This is the most detailed view — use it to understand how to implement a control.

### Documentation
- **`pretorin_get_document_requirements`** — Get required and implied documents for a framework. Pass `framework_id`. Returns explicit (required) and implicit (control-implied) documents with their control references.

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
| `analysis://control/{control_id}` | Control-specific analysis guidance with search patterns and evidence examples |
