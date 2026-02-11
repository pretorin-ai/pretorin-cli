# Example: Gap Analysis Output

This example shows a gap analysis for a hypothetical web application assessed against FedRAMP Moderate.

## Gap Analysis: Acme Web Platform — FedRAMP Moderate

### Summary

| Metric | Value |
|---|---|
| Framework | FedRAMP Rev 5 Moderate (`fedramp-moderate`) |
| Component | Acme Web Platform |
| Families Assessed | 5 of 18 (high-priority code-evidenced families) |
| Controls in Scope | 47 |
| Implemented | 18 (38%) |
| Partial | 14 (30%) |
| Planned | 3 (6%) |
| Not Applicable | 4 (9%) |
| Gap | 8 (17%) |

**Overall Posture**: Partial compliance. Strong authentication and logging foundations, but gaps in account lifecycle management, boundary protection, and baseline configuration documentation.

---

### Access Control (AC) — 12 controls assessed

**Status**: 5 implemented, 4 partial, 1 planned, 2 gap

**Key Findings:**
- **AC-02 (Account Management)** — Partial. User creation with role assignment exists in `src/auth/users.py:45-72`, but no account expiration, dormant account handling, or manager approval workflow.
- **AC-03 (Access Enforcement)** — Implemented. RBAC middleware in `src/middleware/auth.py:12-38` enforces role-based access on all API routes.
- **AC-07 (Unsuccessful Logon Attempts)** — Implemented. Account lockout after 5 failed attempts in `src/auth/login.py:89-105`.
- **AC-17 (Remote Access)** — Gap. No VPN or remote access controls documented. All access is over public internet with TLS only.

**Recommendations:**
1. Add account expiration and dormant account cleanup (addresses AC-02 gaps)
2. Implement remote access policy and controls for administrative access (addresses AC-17)

---

### Audit & Accountability (AU) — 8 controls assessed

**Status**: 5 implemented, 2 partial, 1 gap

**Key Findings:**
- **AU-02 (Audit Events)** — Implemented. Structured JSON logging for auth events, data access, and admin actions via `src/logging/audit.py`.
- **AU-03 (Content of Audit Records)** — Implemented. Logs include timestamp, user ID, action, outcome, and source IP.
- **AU-06 (Audit Record Review)** — Gap. No automated log review or alerting configured. Logs ship to CloudWatch but no dashboards or alerts defined.

**Recommendations:**
1. Configure CloudWatch alarms for security events (addresses AU-06)
2. Add log review procedures and alerting rules

---

### Identification & Authentication (IA) — 9 controls assessed

**Status**: 6 implemented, 2 partial, 1 not applicable

**Key Findings:**
- **IA-02 (Identification and Authentication)** — Implemented. Unique user IDs with bcrypt password hashing (cost factor 12) in `src/auth/passwords.py:15-28`.
- **IA-02(1) (MFA for Privileged Accounts)** — Implemented. TOTP-based MFA required for admin roles via `src/auth/mfa.py:45-60`.
- **IA-05 (Authenticator Management)** — Partial. Password complexity enforced but no password expiration or history tracking.

**Recommendations:**
1. Add password history tracking to prevent reuse (addresses IA-05 gap)

---

### System & Communications Protection (SC) — 10 controls assessed

**Status**: 2 implemented, 4 partial, 2 planned, 2 not applicable

**Key Findings:**
- **SC-07 (Boundary Protection)** — Partial. TLS 1.3 enforced and CORS restricted to specific origins, but security groups allow broad ingress on port 443 from `0.0.0.0/0` in `terraform/security.tf:12-35`.
- **SC-08 (Transmission Confidentiality)** — Implemented. All traffic encrypted via TLS 1.3 with HSTS headers.
- **SC-28 (Protection of Information at Rest)** — Planned. Database encryption at rest not yet enabled. RDS encryption configuration in backlog.

**Recommendations:**
1. Restrict security group ingress to known CIDR ranges (addresses SC-07)
2. Enable RDS encryption at rest (addresses SC-28)

---

### Configuration Management (CM) — 8 controls assessed

**Status**: 0 implemented, 4 partial, 2 planned, 2 gap

**Key Findings:**
- **CM-02 (Baseline Configuration)** — Partial. Docker base images versioned and pinned in `Dockerfile:1`, but no documented baseline configuration standard.
- **CM-06 (Configuration Settings)** — Gap. No security configuration checklist or hardening guide. Application settings are functional but not benchmarked against a security baseline.
- **CM-07 (Least Functionality)** — Partial. Docker images use slim base, but no port/service minimization documented.

**Recommendations:**
1. Create a baseline configuration document with security settings (addresses CM-02, CM-06)
2. Document least functionality rationale for enabled services (addresses CM-07)

---

### Priority Remediation

| Priority | Control | Gap | Effort |
|---|---|---|---|
| 1 | SC-28 | Enable RDS encryption at rest | Low — Terraform change |
| 2 | AU-06 | Add CloudWatch alerting for security events | Medium — alerting rules |
| 3 | AC-02 | Account lifecycle management (expiration, dormancy) | Medium — new feature |
| 4 | CM-02/CM-06 | Baseline configuration documentation | Medium — documentation |
| 5 | AC-17 | Remote access controls for admin access | High — new infrastructure |
