"""Artifact schema definitions for compliance control analysis."""

from __future__ import annotations

ARTIFACT_SCHEMA = {
    "framework_id": {
        "type": "string",
        "required": True,
        "description": "The compliance framework ID (e.g., fedramp-moderate, nist-800-53-r5)",
    },
    "control_id": {
        "type": "string",
        "required": True,
        "description": "The control ID being addressed (e.g., ac-02, au-02)",
    },
    "component": {
        "type": "object",
        "required": True,
        "properties": {
            "component_id": {
                "type": "string",
                "required": True,
                "description": "Source identifier (e.g., repository name, package name)",
            },
            "title": {
                "type": "string",
                "required": True,
                "description": "Human-readable component name",
            },
            "description": {
                "type": "string",
                "required": True,
                "description": "Brief description of what this component does",
            },
            "type": {
                "type": "string",
                "enum": ["software", "hardware", "service", "policy", "process"],
                "default": "software",
                "description": "Type of component",
            },
            "control_implementations": {
                "type": "array",
                "items": {
                    "control_id": {
                        "type": "string",
                        "required": True,
                        "description": "Control ID (must match parent control_id)",
                    },
                    "description": {
                        "type": "string",
                        "required": True,
                        "description": "2-3 sentence narrative explaining HOW the control is implemented",
                    },
                    "implementation_status": {
                        "type": "string",
                        "enum": ["implemented", "partial", "planned", "not-applicable"],
                        "required": True,
                        "description": "Current implementation status",
                    },
                    "responsible_roles": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["System Administrator"],
                        "description": "Roles responsible for maintaining this control",
                    },
                    "evidence": {
                        "type": "array",
                        "items": {
                            "description": {
                                "type": "string",
                                "required": True,
                                "description": "Narrative statement about what this evidence shows",
                            },
                            "file_path": {
                                "type": "string",
                                "description": "Path to the file (optional)",
                            },
                            "line_numbers": {
                                "type": "string",
                                "description": "Line range, e.g., '10-25' (optional)",
                            },
                            "code_snippet": {
                                "type": "string",
                                "description": "Relevant code excerpt (optional, keep brief)",
                            },
                        },
                    },
                    "remarks": {
                        "type": "string",
                        "description": "Additional notes or caveats (optional)",
                    },
                },
            },
        },
    },
    "confidence": {
        "type": "string",
        "enum": ["high", "medium", "low"],
        "default": "medium",
        "description": "Your confidence in this analysis",
    },
}

ARTIFACT_SCHEMA_TEXT = """
# Compliance Artifact Schema

When analyzing code for compliance, produce a JSON artifact with this structure:

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
        "description": "The application implements account management through...",
        "implementation_status": "implemented",
        "responsible_roles": ["System Administrator", "Security Team"],
        "evidence": [
          {
            "description": "User account creation with role assignment",
            "file_path": "src/auth/users.py",
            "line_numbers": "45-72",
            "code_snippet": "def create_user(username, role):\\n    ..."
          }
        ],
        "remarks": "MFA is handled by external identity provider"
      }
    ]
  },
  "confidence": "high"
}
```

## Field Guidelines

### implementation_status
- **implemented**: Control is fully implemented and operational
- **partial**: Some aspects implemented, others pending
- **planned**: Not yet implemented but scheduled
- **not-applicable**: Control doesn't apply to this component

### confidence
- **high**: Clear, direct evidence in code; well-documented
- **medium**: Reasonable evidence but some inference required
- **low**: Limited evidence; significant assumptions made

### evidence
- Include specific file paths and line numbers when possible
- Keep code_snippet brief (under 10 lines ideally)
- Focus on the most relevant evidence, not exhaustive listing
"""
