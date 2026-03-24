# Example: Compliance Artifacts

Examples of well-structured compliance artifacts with good evidence, contrasted with weak examples.

## Good Artifact: AC-02 (Account Management)

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "ac-02",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application providing project management capabilities with multi-tenant user management",
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
            "code_snippet": "def check_dormant_accounts():\n    threshold = datetime.utcnow() - timedelta(days=90)\n    dormant = User.query.filter(\n        User.last_login < threshold,\n        User.is_active == True\n    )\n    for user in dormant:\n        user.deactivate(reason='dormant')"
          },
          {
            "description": "Role definitions with four distinct account types",
            "file_path": "src/auth/roles.py",
            "line_numbers": "8-22",
            "code_snippet": "class UserRole(Enum):\n    ADMIN = 'admin'\n    MANAGER = 'manager'\n    USER = 'user'\n    SERVICE = 'service'"
          }
        ],
        "remarks": "Account removal is handled via deactivation (soft delete) rather than hard delete to maintain audit trail integrity."
      }
    ]
  },
  "confidence": "high"
}
```

**Why this is good:**
- Description explains HOW the control is implemented in 2-3 sentences
- Three evidence items covering different aspects (creation, lifecycle, roles)
- Specific file paths and line numbers
- Code snippets are concise and relevant
- Remarks explain a design decision relevant to the control
- High confidence because evidence is direct and clear

---

## Weak Artifact: AC-02 (Account Management)

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "ac-02",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "ac-02",
        "description": "The application has user management.",
        "implementation_status": "implemented",
        "responsible_roles": ["System Administrator"],
        "evidence": [
          {
            "description": "Has a User class",
            "file_path": "src/models.py",
            "code_snippet": "class User:\n    pass"
          }
        ]
      }
    ]
  },
  "confidence": "high"
}
```

**Why this is weak:**
- Description is vague — doesn't explain how account management works
- Only one evidence item showing a bare class definition
- No line numbers
- "Has a User class" doesn't demonstrate any control implementation
- Claims high confidence despite minimal evidence
- Missing remarks that could explain gaps

---

## Good Artifact: AU-02 (Audit Events)

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "au-02",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application providing project management capabilities with multi-tenant user management",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "au-02",
        "description": "The application implements comprehensive audit logging using structured JSON format. All authentication events, authorization decisions, data access operations, and administrative actions are logged with user attribution, timestamps, and outcome indicators.",
        "implementation_status": "implemented",
        "responsible_roles": ["System Administrator", "Security Team"],
        "evidence": [
          {
            "description": "Authentication events logged with user ID, timestamp, action type, and success/failure outcome",
            "file_path": "src/auth/logging.py",
            "line_numbers": "23-45",
            "code_snippet": "def log_auth_event(user_id, action, success):\n    audit_logger.info({\n        'event': 'authentication',\n        'user_id': user_id,\n        'action': action,\n        'success': success,\n        'timestamp': datetime.utcnow().isoformat(),\n        'source_ip': request.remote_addr\n    })"
          },
          {
            "description": "Centralized log shipping to CloudWatch with 365-day retention",
            "file_path": "terraform/logging.tf",
            "line_numbers": "15-30",
            "code_snippet": "resource \"aws_cloudwatch_log_group\" \"audit\" {\n  name              = \"/app/audit\"\n  retention_in_days = 365\n}"
          }
        ],
        "remarks": "Log format follows CEF (Common Event Format) conventions for SIEM compatibility."
      }
    ]
  },
  "confidence": "high"
}
```

---

## Partial Implementation Example: SC-07 (Boundary Protection)

```json
{
  "framework_id": "fedramp-moderate",
  "control_id": "sc-07",
  "component": {
    "component_id": "acme-web-platform",
    "title": "Acme Web Platform",
    "description": "A web application providing project management capabilities with multi-tenant user management",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "sc-07",
        "description": "The application enforces TLS 1.3 for all communications and restricts CORS to specific origins. However, security group ingress rules allow broad access from 0.0.0.0/0 on port 443, and no WAF or API gateway rate limiting is configured.",
        "implementation_status": "partial",
        "responsible_roles": ["System Administrator", "DevOps Team"],
        "evidence": [
          {
            "description": "CORS restricted to specific application origins only",
            "file_path": "src/api/middleware.py",
            "line_numbers": "8-15",
            "code_snippet": "app.add_middleware(\n    CORSMiddleware,\n    allow_origins=['https://app.acme.com'],\n    allow_methods=['GET', 'POST']\n)"
          },
          {
            "description": "Security group allows unrestricted ingress on port 443 — overly permissive",
            "file_path": "terraform/security.tf",
            "line_numbers": "12-25",
            "code_snippet": "resource \"aws_security_group\" \"web\" {\n  ingress {\n    from_port   = 443\n    to_port     = 443\n    cidr_blocks = [\"0.0.0.0/0\"]\n  }\n}"
          }
        ],
        "remarks": "TLS and CORS are properly configured, but network boundary controls need tightening. Recommend restricting security group ingress and adding WAF."
      }
    ]
  },
  "confidence": "medium"
}
```

**Why this works as a partial:**
- Description honestly states what IS and what ISN'T implemented
- Evidence includes both positive (CORS) and negative (permissive SG) findings
- Status correctly set to `partial` rather than claiming `implemented`
- Confidence set to `medium` because some inference was needed
- Remarks include specific remediation guidance
