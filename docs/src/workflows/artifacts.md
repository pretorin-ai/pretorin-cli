# Artifact Generation

Compliance artifacts are structured JSON documents that describe how a specific control is implemented within a component.

## Generating Artifacts

### Via Agent

```bash
pretorin agent run --skill evidence-collection "Generate artifact for AC-02 in my system"
```

### Via MCP

Use the `pretorin_generate_control_artifacts` tool for read-only AI drafts.

### Submit to Platform

```bash
pretorin frameworks submit-artifact artifact.json
```

## Artifact Schema

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

See [Artifact Schema Reference](../reference/artifact-schema.md) for the full field documentation.

## Implementation Status Values

| Status | Criteria |
|--------|----------|
| `implemented` | Fully implemented and operational. Clear, direct code evidence. |
| `partial` | Some aspects implemented, others pending. |
| `planned` | Not yet implemented but scheduled. Architecture supports it. |
| `not-applicable` | Control doesn't apply to this component. |

## Confidence Levels

| Level | Criteria |
|-------|----------|
| `high` | Clear, direct evidence in code. Specific file paths and line numbers. |
| `medium` | Reasonable evidence with some inference required. |
| `low` | Limited evidence. Significant assumptions made. |

## Evidence Quality

Good evidence shows HOW a control is implemented with specifics. Weak evidence merely shows that relevant code exists.

**Good:**
> User creation requires role assignment and manager approval via the `create_user()` function which validates roles against an allowlist and triggers an approval workflow.

**Weak:**
> Has a User class in the models file.

### Guidelines

- Call `pretorin frameworks control <fw> <ctrl>` first — the AI guidance describes exactly what evidence assessors expect
- Include specific file paths and line numbers
- Keep code snippets brief (under 10 lines)
- Focus on the most relevant evidence, not exhaustive listing
- Describe what the evidence demonstrates in relation to the control requirement

## Example: Good Artifact

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "ac-02",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application with multi-tenant user management",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "ac-02",
        "description": "The application implements account management through a provisioning system that requires role assignment during user creation, enforces manager approval for elevated roles, and automatically disables accounts after 90 days of inactivity.",
        "implementation_status": "implemented",
        "responsible_roles": ["System Administrator", "Security Team", "Team Managers"],
        "evidence": [
          {
            "description": "User creation requires role assignment and manager approval for admin roles",
            "file_path": "src/users/provisioning.py",
            "line_numbers": "45-72",
            "code_snippet": "def create_user(username, role, manager_id):\n    validate_role(role)\n    if role in ELEVATED_ROLES:\n        require_approval(manager_id)\n    user = User.create(username=username, role=role)"
          },
          {
            "description": "Automated dormant account detection and deactivation after 90 days",
            "file_path": "src/users/lifecycle.py",
            "line_numbers": "120-145",
            "code_snippet": "def check_dormant_accounts():\n    threshold = datetime.utcnow() - timedelta(days=90)\n    dormant = User.query.filter(User.last_login < threshold)"
          }
        ],
        "remarks": "Account removal via soft delete to maintain audit trail."
      }
    ]
  },
  "confidence": "high"
}
```

## Example: Partial Implementation

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "sc-07",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application with multi-tenant user management",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "sc-07",
        "description": "TLS 1.3 enforced and CORS restricted to specific origins. However, security group ingress allows broad access from 0.0.0.0/0 on port 443, and no WAF is configured.",
        "implementation_status": "partial",
        "responsible_roles": ["System Administrator", "DevOps Team"],
        "evidence": [
          {
            "description": "CORS restricted to application origins only",
            "file_path": "src/api/middleware.py",
            "line_numbers": "8-15",
            "code_snippet": "app.add_middleware(\n    CORSMiddleware,\n    allow_origins=['https://app.acme.com'])"
          },
          {
            "description": "Security group allows unrestricted ingress — overly permissive",
            "file_path": "terraform/security.tf",
            "line_numbers": "12-25",
            "code_snippet": "ingress {\n    from_port = 443\n    cidr_blocks = [\"0.0.0.0/0\"]\n}"
          }
        ],
        "remarks": "Recommend restricting security group ingress and adding WAF."
      }
    ]
  },
  "confidence": "medium"
}
```
