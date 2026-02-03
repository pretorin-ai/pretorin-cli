"""Analysis prompts and templates for compliance control analysis.

This module contains the analysis guidance for the 5 core controls used in demos:
- ac-2: Access Control - Account Management
- au-2: Audit & Accountability - Audit Events
- ia-2: Identification & Authentication
- sc-7: System & Communications Protection - Boundary Protection
- cm-2: Configuration Management - Baseline Configuration
"""

from __future__ import annotations

# =============================================================================
# Artifact Schema
# =============================================================================

ARTIFACT_SCHEMA = {
    "framework_id": {
        "type": "string",
        "required": True,
        "description": "The compliance framework ID (e.g., fedramp-moderate, nist-800-53-r5)",
    },
    "control_id": {
        "type": "string",
        "required": True,
        "description": "The control ID being addressed (e.g., ac-2, au-2)",
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
  "control_id": "ac-2",
  "component": {
    "component_id": "my-application",
    "title": "My Application",
    "description": "A web application that handles user data",
    "type": "software",
    "control_implementations": [
      {
        "control_id": "ac-2",
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

# =============================================================================
# Framework Analysis Guide
# =============================================================================

FRAMEWORK_GUIDES: dict[str, str] = {
    "fedramp-moderate": """
# FedRAMP Moderate Analysis Guide

FedRAMP Moderate is based on NIST 800-53 and designed for systems handling
Controlled Unclassified Information (CUI). It has ~325 controls.

## Key Focus Areas for Code Analysis

### Access Control (AC)
- Look for: Authentication systems, RBAC/ABAC implementations, session management
- File patterns: `auth/`, `users/`, `permissions/`, `roles/`
- Keywords: `authenticate`, `authorize`, `permission`, `role`, `session`

### Audit & Accountability (AU)
- Look for: Logging frameworks, audit trails, log retention settings
- File patterns: `logging/`, `audit/`, `events/`
- Keywords: `log`, `audit`, `event`, `trace`, `record`

### Identification & Authentication (IA)
- Look for: Login flows, MFA implementation, credential storage
- File patterns: `identity/`, `auth/`, `login/`
- Keywords: `identity`, `credential`, `password`, `mfa`, `2fa`, `token`

### System & Communications Protection (SC)
- Look for: TLS configuration, encryption, network boundaries
- File patterns: `security/`, `crypto/`, `network/`
- Keywords: `encrypt`, `tls`, `ssl`, `https`, `firewall`, `boundary`

### Configuration Management (CM)
- Look for: Config files, environment handling, baseline settings
- File patterns: `config/`, `settings/`, `.env`
- Keywords: `config`, `setting`, `baseline`, `default`

## Common Evidence Locations

1. **Infrastructure as Code**: Terraform, CloudFormation, Pulumi files
2. **CI/CD Pipelines**: GitHub Actions, GitLab CI, Jenkins files
3. **Docker/Kubernetes**: Dockerfiles, Helm charts, manifests
4. **Application Config**: `.env`, `config.yaml`, settings files
5. **Authentication**: OAuth configs, SAML settings, JWT handling
""",
    "nist-800-53-r5": """
# NIST 800-53 Rev 5 Analysis Guide

NIST 800-53 is the foundational security control catalog used by US federal
agencies. It contains 1000+ controls across 20 families.

## Control Family Priorities for Code Analysis

### High Priority (Direct Code Evidence)
- **AC (Access Control)**: How access is managed programmatically
- **AU (Audit)**: What gets logged and how
- **IA (Identification & Auth)**: How users are identified
- **SC (System Protection)**: Encryption and boundary protection
- **CM (Configuration Mgmt)**: How settings are managed

### Medium Priority (Mixed Code/Policy)
- **SA (System Acquisition)**: Secure development practices
- **SI (System Integrity)**: Input validation, malware protection
- **CA (Assessment)**: Security testing, vulnerability scanning

### Lower Priority (Mostly Policy)
- **AT (Awareness Training)**: Hard to evidence in code
- **PL (Planning)**: Documentation-focused
- **PS (Personnel Security)**: HR-focused

## Analysis Approach

1. Start with high-priority families where code evidence is strongest
2. Look for security-related comments and documentation
3. Check for security frameworks/libraries in use
4. Review configuration for security settings
5. Examine test files for security testing
""",
    "nist-800-171-r3": """
# NIST 800-171 Rev 3 Analysis Guide

NIST 800-171 protects Controlled Unclassified Information (CUI) in
non-federal systems. It's a subset of 800-53 with ~110 requirements.

## Focus Areas

800-171 maps to specific 800-53 controls. Key areas for code analysis:

### Access Control (3.1)
- Account management and access enforcement
- Remote access controls
- Least privilege implementation

### Audit & Accountability (3.3)
- Audit logging requirements
- Audit record retention
- Audit review and analysis

### Identification & Authentication (3.5)
- User identification
- Authentication mechanisms
- Multi-factor authentication

### System & Communications Protection (3.13)
- Boundary protection
- Cryptographic protection
- Network communication protection

### Configuration Management (3.4)
- Baseline configurations
- Configuration change control
- Security settings enforcement
""",
}

# =============================================================================
# Control-Specific Analysis Prompts
# =============================================================================

CONTROL_ANALYSIS_PROMPTS: dict[str, dict[str, str]] = {
    # -------------------------------------------------------------------------
    # AC-2: Account Management
    # -------------------------------------------------------------------------
    "ac-2": {
        "title": "Account Management",
        "family": "Access Control",
        "summary": """
AC-2 requires organizations to manage system accounts including identifying
account types, assigning account managers, establishing conditions for group
membership, specifying authorized users, and maintaining ongoing account
administration.
""",
        "what_to_look_for": """
## What to Look For

### Account Creation & Provisioning
- User registration/signup flows
- Admin user creation interfaces
- Account provisioning automation
- Role assignment during account creation
- Default account configurations

### Account Types & Roles
- Role definitions (admin, user, guest, service)
- Role-based access control (RBAC) implementation
- Group membership management
- Service account handling

### Account Lifecycle
- Account activation/deactivation logic
- Account expiration settings
- Dormant account handling
- Account removal/cleanup processes

### File Patterns to Search
```
**/auth/**
**/users/**
**/accounts/**
**/identity/**
**/iam/**
**/rbac/**
**/*user*.py
**/*account*.py
**/*role*.py
```

### Keywords to Search
- `create_user`, `delete_user`, `disable_user`
- `assign_role`, `revoke_role`
- `account`, `user`, `role`, `permission`
- `provision`, `deprovision`
- `activate`, `deactivate`, `suspend`
""",
        "evidence_examples": """
## Evidence Examples

### Good Evidence
```json
{
  "description": "User creation requires role assignment and manager approval",
  "file_path": "src/users/provisioning.py",
  "line_numbers": "45-72",
  "code_snippet": "def create_user(username, role, manager_id):\\n    validate_role(role)\\n    require_approval(manager_id)..."
}
```

### Weak Evidence
```json
{
  "description": "Has a User class",
  "file_path": "src/models.py",
  "code_snippet": "class User:\\n    pass"
}
```

The difference: Good evidence shows HOW the control is implemented,
not just that relevant code exists.
""",
        "implementation_status_guidance": """
## Status Guidance

- **implemented**: Full account lifecycle management with role assignment,
  approval workflows, and automated deprovisioning
- **partial**: Basic user CRUD but missing some elements (e.g., no expiration,
  no manager approval, limited role management)
- **planned**: User model exists but account management features not built
- **not-applicable**: Component doesn't manage user accounts
""",
    },
    # -------------------------------------------------------------------------
    # AU-2: Audit Events
    # -------------------------------------------------------------------------
    "au-2": {
        "title": "Audit Events",
        "family": "Audit and Accountability",
        "summary": """
AU-2 requires identifying events that need to be audited, coordinating the
audit function with other organizational entities, and determining which
events require auditing based on risk assessments.
""",
        "what_to_look_for": """
## What to Look For

### Logging Configuration
- Logging framework setup (Python logging, log4j, winston, etc.)
- Log level configuration
- Structured logging implementation
- Log format specifications

### Auditable Events
- Authentication events (login success/failure)
- Authorization decisions (access granted/denied)
- Data access events (read, create, update, delete)
- Administrative actions
- Security-relevant events

### Audit Infrastructure
- Log aggregation setup
- Log shipping configuration
- Centralized logging (ELK, Splunk, CloudWatch)
- Log retention settings

### File Patterns to Search
```
**/logging/**
**/audit/**
**/logger/**
**/*log*.py
**/*audit*.py
**/middleware/**
logging.conf
log4j*.xml
```

### Keywords to Search
- `logger`, `logging`, `log`
- `audit`, `audit_log`, `audit_trail`
- `event`, `record`, `trace`
- `info`, `warning`, `error`, `critical`
""",
        "evidence_examples": """
## Evidence Examples

### Good Evidence
```json
{
  "description": "Authentication events logged with user ID, timestamp, and outcome",
  "file_path": "src/auth/logging.py",
  "line_numbers": "23-45",
  "code_snippet": "def log_auth_event(user_id, action, success):\\n    audit_logger.info({\\n        'event': 'authentication',\\n        'user_id': user_id,\\n        'action': action,\\n        'success': success,\\n        'timestamp': datetime.utcnow()\\n    })"
}
```

### Weak Evidence
```json
{
  "description": "Uses Python logging module",
  "file_path": "src/main.py",
  "code_snippet": "import logging"
}
```
""",
        "implementation_status_guidance": """
## Status Guidance

- **implemented**: Comprehensive audit logging for security events with
  structured format, timestamps, and user attribution
- **partial**: Basic logging exists but missing security events or
  proper attribution
- **planned**: Logging infrastructure set up but audit events not defined
- **not-applicable**: Rare - almost all systems need some audit capability
""",
    },
    # -------------------------------------------------------------------------
    # IA-2: Identification and Authentication
    # -------------------------------------------------------------------------
    "ia-2": {
        "title": "Identification and Authentication (Organizational Users)",
        "family": "Identification and Authentication",
        "summary": """
IA-2 requires uniquely identifying and authenticating organizational users
(or processes acting on behalf of users). This includes implementing
multi-factor authentication for various access types.
""",
        "what_to_look_for": """
## What to Look For

### User Identification
- Unique user ID generation/assignment
- Username/email uniqueness enforcement
- User identity verification

### Authentication Mechanisms
- Password authentication implementation
- Password hashing (bcrypt, argon2, scrypt)
- Password policies (complexity, length, expiration)
- Session token generation

### Multi-Factor Authentication (MFA)
- TOTP implementation
- SMS/Email verification
- Hardware token support
- MFA enrollment flows

### Authentication Infrastructure
- OAuth/OIDC integration
- SAML/SSO configuration
- API key authentication
- JWT token handling

### File Patterns to Search
```
**/auth/**
**/identity/**
**/login/**
**/mfa/**
**/sso/**
**/*password*.py
**/*token*.py
**/*session*.py
```

### Keywords to Search
- `authenticate`, `login`, `verify`
- `password`, `credential`, `hash`
- `mfa`, `2fa`, `totp`, `otp`
- `token`, `jwt`, `session`
- `oauth`, `oidc`, `saml`
""",
        "evidence_examples": """
## Evidence Examples

### Good Evidence
```json
{
  "description": "Password hashing using bcrypt with cost factor 12",
  "file_path": "src/auth/passwords.py",
  "line_numbers": "15-28",
  "code_snippet": "def hash_password(password: str) -> str:\\n    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))"
}
```

```json
{
  "description": "MFA verification required for privileged actions",
  "file_path": "src/auth/mfa.py",
  "line_numbers": "45-60",
  "code_snippet": "def verify_mfa(user, code):\\n    totp = pyotp.TOTP(user.mfa_secret)\\n    return totp.verify(code)"
}
```
""",
        "implementation_status_guidance": """
## Status Guidance

- **implemented**: Unique user identification with strong authentication
  (proper password hashing) and MFA for privileged access
- **partial**: Basic authentication but weak hashing, no MFA, or
  missing for some user types
- **planned**: User model exists but authentication not implemented
- **not-applicable**: System has no user authentication (pure API, etc.)
""",
    },
    # -------------------------------------------------------------------------
    # SC-7: Boundary Protection
    # -------------------------------------------------------------------------
    "sc-7": {
        "title": "Boundary Protection",
        "family": "System and Communications Protection",
        "summary": """
SC-7 requires monitoring and controlling communications at external and
key internal boundaries of the system. This includes implementing managed
interfaces with traffic control and enforcing network segmentation.
""",
        "what_to_look_for": """
## What to Look For

### Network Configuration
- Firewall rules (iptables, security groups)
- Network segmentation
- DMZ configuration
- VPC/subnet definitions

### API Security
- API gateway configuration
- Rate limiting implementation
- CORS settings
- Input validation at boundaries

### TLS/Encryption
- TLS configuration
- Certificate management
- HTTPS enforcement
- Encryption in transit

### Infrastructure as Code
- Terraform security groups
- CloudFormation network resources
- Kubernetes network policies
- Docker network configuration

### File Patterns to Search
```
**/terraform/**
**/cloudformation/**
**/k8s/**
**/kubernetes/**
**/*.tf
**/security-group*
**/firewall*
**/nginx.conf
**/network*
```

### Keywords to Search
- `firewall`, `security_group`, `ingress`, `egress`
- `tls`, `ssl`, `https`, `certificate`
- `cors`, `origin`, `allow_origin`
- `rate_limit`, `throttle`
- `network_policy`, `segmentation`
""",
        "evidence_examples": """
## Evidence Examples

### Good Evidence
```json
{
  "description": "Security group restricts ingress to ports 443 and 22 from specific CIDRs",
  "file_path": "terraform/security.tf",
  "line_numbers": "12-35",
  "code_snippet": "resource \\"aws_security_group\\" \\"web\\" {\\n  ingress {\\n    from_port = 443\\n    to_port = 443\\n    cidr_blocks = [\\"10.0.0.0/8\\"]\\n  }\\n}"
}
```

```json
{
  "description": "CORS configured to allow only specific origins",
  "file_path": "src/api/middleware.py",
  "line_numbers": "8-15",
  "code_snippet": "app.add_middleware(\\n    CORSMiddleware,\\n    allow_origins=['https://app.example.com'],\\n    allow_methods=['GET', 'POST']\\n)"
}
```
""",
        "implementation_status_guidance": """
## Status Guidance

- **implemented**: Clear network boundaries with firewall rules, TLS
  enforcement, and controlled ingress/egress
- **partial**: Some boundary controls but gaps (e.g., TLS but no firewall,
  or firewall but overly permissive)
- **planned**: Infrastructure exists but security controls not configured
- **not-applicable**: Serverless/fully managed with no network control
""",
    },
    # -------------------------------------------------------------------------
    # CM-2: Baseline Configuration
    # -------------------------------------------------------------------------
    "cm-2": {
        "title": "Baseline Configuration",
        "family": "Configuration Management",
        "summary": """
CM-2 requires developing, documenting, and maintaining a current baseline
configuration of the system. This includes configuration settings, software
versions, and security configurations.
""",
        "what_to_look_for": """
## What to Look For

### Configuration Management
- Configuration files (YAML, JSON, TOML)
- Environment variable handling
- Configuration validation
- Default configuration values

### Infrastructure Baselines
- Terraform/IaC definitions
- Docker base images
- Kubernetes manifests
- CI/CD pipeline definitions

### Version Management
- Dependency lock files (requirements.txt, package-lock.json)
- Version pinning
- Base image versioning

### Security Configuration
- Security headers configuration
- Secure defaults
- Hardening configurations
- Secret management

### File Patterns to Search
```
**/config/**
**/settings/**
*.yaml
*.yml
*.json
*.toml
.env.example
requirements*.txt
package*.json
Dockerfile
docker-compose*.yml
```

### Keywords to Search
- `config`, `configuration`, `settings`
- `baseline`, `default`, `standard`
- `version`, `pin`
- `environment`, `env`
""",
        "evidence_examples": """
## Evidence Examples

### Good Evidence
```json
{
  "description": "Configuration schema with validation and documented defaults",
  "file_path": "src/config/schema.py",
  "line_numbers": "10-45",
  "code_snippet": "class AppConfig(BaseModel):\\n    database_url: str\\n    log_level: str = 'INFO'\\n    session_timeout: int = Field(default=3600, ge=300)"
}
```

```json
{
  "description": "Pinned dependencies with hash verification",
  "file_path": "requirements.txt",
  "code_snippet": "django==4.2.7 --hash=sha256:..."
}
```

```json
{
  "description": "Hardened Docker base image with specific version",
  "file_path": "Dockerfile",
  "line_numbers": "1-5",
  "code_snippet": "FROM python:3.11-slim-bookworm@sha256:abc123..."
}
```
""",
        "implementation_status_guidance": """
## Status Guidance

- **implemented**: Documented baseline configuration with version control,
  validated settings, and pinned dependencies
- **partial**: Configuration exists but not documented, or versions not
  pinned, or missing validation
- **planned**: Configuration structure exists but baselines not established
- **not-applicable**: Rare - all systems have configuration
""",
    },
}


def get_artifact_schema() -> str:
    """Return the artifact schema as formatted text."""
    return ARTIFACT_SCHEMA_TEXT


def get_framework_guide(framework_id: str) -> str | None:
    """Return the analysis guide for a framework."""
    # Normalize framework ID and check for matches
    framework_id_lower = framework_id.lower()

    # Direct match
    if framework_id_lower in FRAMEWORK_GUIDES:
        return FRAMEWORK_GUIDES[framework_id_lower]

    # Partial matches
    for key, guide in FRAMEWORK_GUIDES.items():
        if key in framework_id_lower or framework_id_lower in key:
            return guide

    return None


def get_control_prompt(control_id: str) -> dict[str, str] | None:
    """Return the analysis prompt for a control."""
    control_id_lower = control_id.lower()
    return CONTROL_ANALYSIS_PROMPTS.get(control_id_lower)


def format_control_analysis_prompt(framework_id: str, control_id: str) -> str:
    """Format a complete analysis prompt for a control."""
    prompt_data = get_control_prompt(control_id)

    if not prompt_data:
        return f"""
# Control Analysis: {control_id.upper()}

No specific analysis guidance available for this control.

## General Approach

1. Review the control requirements using `pretorin_get_control_references`
2. Search the codebase for relevant implementations
3. Document evidence with file paths and line numbers
4. Assess implementation status based on findings
5. Submit artifact using `pretorin_submit_artifact`

## Output Format

Use the schema from `analysis://schema` to format your artifact.
"""

    return f"""
# Control Analysis: {control_id.upper()} - {prompt_data["title"]}

**Family:** {prompt_data["family"]}

## Overview
{prompt_data["summary"]}

{prompt_data["what_to_look_for"]}

{prompt_data["evidence_examples"]}

{prompt_data["implementation_status_guidance"]}

## Output Format

Produce a JSON artifact following the schema from `analysis://schema`.
Set the framework_id to `{framework_id}` and control_id to `{control_id}`.

After analysis, validate with `pretorin_validate_artifact` and submit
with `pretorin_submit_artifact`.
"""


def get_available_controls() -> list[str]:
    """Return list of controls with analysis prompts."""
    return list(CONTROL_ANALYSIS_PROMPTS.keys())


def get_control_summary(control_id: str) -> str | None:
    """Return a brief summary for a control."""
    prompt_data = get_control_prompt(control_id)
    if prompt_data:
        return f"{prompt_data['title']} - {prompt_data['family']}"
    return None
