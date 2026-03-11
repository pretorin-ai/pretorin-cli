"""Control-specific analysis prompts for the 5 core demo controls."""

from __future__ import annotations

CONTROL_ANALYSIS_PROMPTS: dict[str, dict[str, str]] = {
    # -------------------------------------------------------------------------
    # AC-02: Account Management
    # -------------------------------------------------------------------------
    "ac-02": {
        "title": "Account Management",
        "family": "Access Control",
        "summary": """
AC-02 requires organizations to manage system accounts including identifying
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
    # AU-02: Audit Events
    # -------------------------------------------------------------------------
    "au-02": {
        "title": "Audit Events",
        "family": "Audit and Accountability",
        "summary": """
AU-02 requires identifying events that need to be audited, coordinating the
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
    # IA-02: Identification and Authentication
    # -------------------------------------------------------------------------
    "ia-02": {
        "title": "Identification and Authentication (Organizational Users)",
        "family": "Identification and Authentication",
        "summary": """
IA-02 requires uniquely identifying and authenticating organizational users
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
    # SC-07: Boundary Protection
    # -------------------------------------------------------------------------
    "sc-07": {
        "title": "Boundary Protection",
        "family": "System and Communications Protection",
        "summary": """
SC-07 requires monitoring and controlling communications at external and
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
    # CM-02: Baseline Configuration
    # -------------------------------------------------------------------------
    "cm-02": {
        "title": "Baseline Configuration",
        "family": "Configuration Management",
        "summary": """
CM-02 requires developing, documenting, and maintaining a current baseline
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
