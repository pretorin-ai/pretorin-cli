# Compliance Artifact Schema

When analyzing code for compliance, produce a JSON artifact with this structure. Artifacts document how a specific control is implemented within a component.

## Schema

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "ac-02",
  "component": {
    "component_id": "my-application",
    "title": "My Application",
    "description": "A web application that handles user data",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "ac-02",
        "description": "2-3 sentence narrative explaining HOW the control is implemented",
        "implementation_status": "implemented",
        "responsible_roles": ["System Administrator", "Security Team"],
        "evidence": [
          {
            "description": "What this evidence demonstrates",
            "file_path": "src/auth/users.py",
            "line_numbers": "45-72",
            "code_snippet": "def create_user(username, role):\n    ..."
          }
        ],
        "remarks": "Optional additional context"
      }
    ]
  },
  "confidence": "high"
}
```

## Field Guidelines

### Top-Level Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `framework_id` | string | Yes | The compliance framework (e.g., `fedramp-moderate`, `nist-800-53-r5`) |
| `control_id` | string | Yes | The control being addressed (e.g., `ac-02`, `au-02`) |
| `component` | object | Yes | The system component being assessed |
| `confidence` | string | Yes | Confidence in the analysis: `high`, `medium`, or `low` |

### Component Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `component_id` | string | Yes | Source identifier (repository name, package name) |
| `title` | string | Yes | Human-readable component name |
| `description` | string | Yes | Brief description of what the component does |
| `type` | string | Yes | One of: `software`, `hardware`, `service`, `policy`, `process` |
| `control_implementations` | array | Yes | How the control is implemented |

### Control Implementation Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `control_id` | string | Yes | Must match parent `control_id` |
| `description` | string | Yes | 2-3 sentence narrative of HOW the control is implemented |
| `implementation_status` | string | Yes | See status definitions below |
| `responsible_roles` | array | No | Roles responsible (default: `["System Administrator"]`) |
| `evidence` | array | No | Supporting evidence items |
| `remarks` | string | No | Additional notes or caveats |

### Evidence Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `description` | string | Yes | Narrative of what this evidence shows |
| `file_path` | string | No | Path to the source file |
| `line_numbers` | string | No | Line range (e.g., `"10-25"`) |
| `code_snippet` | string | No | Relevant code excerpt (keep under 10 lines) |

## Implementation Status

- **`implemented`** — Control is fully implemented and operational. Clear, direct evidence exists in the codebase.
- **`partial`** — Some aspects are implemented, others are pending. Example: user CRUD exists but no account expiration or manager approval.
- **`planned`** — Not yet implemented but scheduled. The architecture supports it but the feature isn't built.
- **`not-applicable`** — Control doesn't apply to this component. Example: a pure API service with no user accounts doesn't need account management controls.

## Confidence Levels

- **`high`** — Clear, direct evidence in code. Well-documented implementations with specific file paths and line numbers.
- **`medium`** — Reasonable evidence but some inference required. The implementation likely satisfies the control but some aspects aren't explicitly documented.
- **`low`** — Limited evidence. Significant assumptions made. The codebase has some relevant code but the connection to the control requirement is indirect.

## Evidence Quality

Good evidence shows HOW a control is implemented with specifics. Weak evidence merely shows that relevant code exists.

**Good**: "User creation requires role assignment and manager approval via the `create_user()` function which validates roles against an allowlist and triggers an approval workflow."

**Weak**: "Has a User class in the models file."

When collecting evidence:
- Call `pretorin_get_control` first — the `ai_guidance.evidence_expectations` field describes exactly what kinds of evidence assessors expect for each control
- Use `ai_guidance.implementation_considerations` to understand common implementation approaches and what to look for
- Include specific file paths and line numbers
- Keep code snippets brief (under 10 lines)
- Focus on the most relevant evidence, not exhaustive listing
- Describe what the evidence demonstrates in relation to the control requirement
