# Artifact Schema Reference

Complete field reference for compliance artifact JSON documents.

## Top-Level Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `framework_id` | string | Yes | The compliance framework (e.g., `fedramp-moderate`, `nist-800-53-r5`) |
| `control_id` | string | Yes | The control being addressed (e.g., `ac-02`, `au-02`) |
| `component` | object | Yes | The system component being assessed |
| `confidence` | string | Yes | Confidence in the analysis: `high`, `medium`, or `low` |

## Component Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `component_id` | string | Yes | Source identifier (repository name, package name) |
| `title` | string | Yes | Human-readable component name |
| `description` | string | Yes | Brief description of what the component does |
| `type` | string | Yes | One of: `software`, `hardware`, `service`, `policy`, `process` |
| `control_implementations` | array | Yes | How the control is implemented |

## Control Implementation Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `control_id` | string | Yes | Must match parent `control_id` |
| `description` | string | Yes | 2-3 sentence narrative of HOW the control is implemented |
| `implementation_status` | string | Yes | `implemented`, `partial`, `planned`, or `not-applicable` |
| `responsible_roles` | array | No | Roles responsible (default: `["System Administrator"]`) |
| `evidence` | array | No | Supporting evidence items |
| `remarks` | string | No | Additional notes or caveats |

## Evidence Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Narrative of what this evidence shows |
| `file_path` | string | No | Path to the source file |
| `line_numbers` | string | No | Line range (e.g., `"10-25"`) |
| `code_snippet` | string | No | Relevant code excerpt (keep under 10 lines) |

## Implementation Status Definitions

| Status | Definition |
|--------|------------|
| `implemented` | Control is fully implemented and operational. Clear, direct evidence exists in the codebase. |
| `partial` | Some aspects are implemented, others are pending. Example: user CRUD exists but no account expiration or manager approval. |
| `planned` | Not yet implemented but scheduled. The architecture supports it but the feature isn't built. |
| `not-applicable` | Control doesn't apply to this component. Example: a pure API service with no user accounts doesn't need account management controls. |

## Confidence Levels

| Level | Definition |
|-------|------------|
| `high` | Clear, direct evidence in code. Well-documented implementations with specific file paths and line numbers. |
| `medium` | Reasonable evidence but some inference required. The implementation likely satisfies the control but some aspects aren't explicitly documented. |
| `low` | Limited evidence. Significant assumptions made. The codebase has relevant code but the connection to the control requirement is indirect. |
