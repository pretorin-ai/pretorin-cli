"""Framework-specific analysis guides for compliance code review."""

from __future__ import annotations

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
