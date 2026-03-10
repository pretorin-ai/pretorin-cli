# Example: Gap Analysis Report

This example shows a gap analysis for a hypothetical web application assessed against FedRAMP Moderate.

## Gap Analysis: Acme Web Platform — FedRAMP Moderate

### Summary

| Metric | Value |
|--------|-------|
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
- **AC-17 (Remote Access)** — Gap. No VPN or remote access controls documented.

**Recommendations:**
1. Add account expiration and dormant account cleanup (addresses AC-02 gaps)
2. Implement remote access policy and controls for administrative access (addresses AC-17)

---

### Audit & Accountability (AU) — 8 controls assessed

**Status**: 5 implemented, 2 partial, 1 gap

**Key Findings:**
- **AU-02 (Audit Events)** — Implemented. Structured JSON logging for auth events, data access, and admin actions.
- **AU-03 (Content of Audit Records)** — Implemented. Logs include timestamp, user ID, action, outcome, and source IP.
- **AU-06 (Audit Record Review)** — Gap. No automated log review or alerting configured.

**Recommendations:**
1. Configure CloudWatch alarms for security events (addresses AU-06)
2. Add log review procedures and alerting rules

---

### System & Communications Protection (SC) — 10 controls assessed

**Status**: 2 implemented, 4 partial, 2 planned, 2 not applicable

**Key Findings:**
- **SC-07 (Boundary Protection)** — Partial. TLS 1.3 and CORS configured, but security groups allow broad ingress.
- **SC-08 (Transmission Confidentiality)** — Implemented. All traffic encrypted via TLS 1.3 with HSTS.
- **SC-28 (Protection of Information at Rest)** — Planned. Database encryption not yet enabled.

---

### Priority Remediation

| Priority | Control | Gap | Effort |
|----------|---------|-----|--------|
| 1 | SC-28 | Enable RDS encryption at rest | Low — Terraform change |
| 2 | AU-06 | Add CloudWatch alerting for security events | Medium — alerting rules |
| 3 | AC-02 | Account lifecycle management | Medium — new feature |
| 4 | CM-02/CM-06 | Baseline configuration documentation | Medium — documentation |
| 5 | AC-17 | Remote access controls for admin access | High — new infrastructure |
