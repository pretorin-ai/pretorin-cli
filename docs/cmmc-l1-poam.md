# Plan of Action and Milestones (POA&M) — CMMC Level 1

**System Name:** pretorin-test
**Framework:** CMMC 2.0 Level 1 (Foundational) Practice Catalog
**System ID:** 16bef439-f98f-4a80-af39-c738746f3a10
**Date Prepared:** 2026-03-06
**Prepared By:** Nico Butera (via Pretorin CLI + MCP)

---

## Summary

| Metric | Count |
|--------|-------|
| Total CMMC L1 Controls | 17 |
| Controls Fully Implemented | 0 |
| Controls In Progress (Planned) | 17 |
| Total POA&M Items | 51 |
| High Priority Items | 12 |
| Medium Priority Items | 24 |
| Low Priority Items | 15 |

---

## POA&M Items

### AC.L1-3.1.1 — Authorized Access Control

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| AC-1.1 | Backend API authorization middleware not evidenced — server-side JWT validation and role enforcement on API routes needs to be documented and attached | High | Attach API auth middleware code (JWT validation, role guards) as evidence in Pretorin | 2026-04-15 | Engineering Lead | Open |
| AC-1.2 | No current account inventory — active users and their roles in the production identity system are not exported or documented | High | Export active user/role list from IdP; establish quarterly account review process | 2026-04-15 | IT Admin | Open |
| AC-1.3 | Device and system-to-system authorization controls not documented — no MDM inventory, approved integrations list, or network access restriction evidence | Medium | Export MDM device inventory; document approved integrations registry; attach VPN/firewall configs | 2026-05-15 | IT Admin, Infrastructure Lead | Open |

---

### AC.L1-3.1.2 — Transaction and Function Control

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| AC-2.1 | Server-side role enforcement not evidenced — API middleware must enforce role-permission checks on all mutating endpoints (POST/PUT/DELETE) | High | Implement and attach server-side authorization middleware; demonstrate HTTP 403 on unauthorized requests | 2026-04-15 | Engineering Lead | Open |
| AC-2.2 | User-to-role assignment records not available — no export of who holds each role in the identity provider | Medium | Export IdP group membership; map users to application roles | 2026-04-30 | IT Admin | Open |
| AC-2.3 | No privileged function audit logs — cannot demonstrate denied attempts when under-privileged users try restricted actions | Medium | Enable and attach API audit logs showing access denied events for restricted operations | 2026-05-15 | Engineering Lead | Open |

---

### AC.L1-3.1.20 — External Connection Control

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| AC-20.1 | Firewall/security group configuration not exported — no `aws ec2 describe-security-groups` output attached | Medium | Export and attach all VPC security group and NACL rules | 2026-04-15 | Infrastructure Lead | Open |
| AC-20.2 | VPN authentication logs not provided — no sample showing SSO + MFA verification for remote connections | Medium | Export sample VPN auth logs demonstrating identity verification | 2026-04-30 | Infrastructure Lead | Open |
| AC-20.3 | Vendor access records missing — no time-bound approval documents or session logs for third-party access | Medium | Establish vendor access request workflow; attach sample approval and session log | 2026-05-15 | Security Lead | Open |

---

### AC.L1-3.1.22 — Public Information Control

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| AC-22.1 | S3 Block Public Access not evidenced — no console screenshots or CLI output showing account-level settings | Medium | Attach `aws s3control get-public-access-block` output and AWS Config rule compliance | 2026-04-15 | Infrastructure Lead | Open |
| AC-22.2 | GitHub public repo access configuration not exported — branch protection rules and push access restrictions not documented | Low | Export GitHub branch protection settings and org-level repo access permissions | 2026-05-15 | Engineering Lead | Open |
| AC-22.3 | No sample pre-publication approval records — FCI checklist completion not evidenced | Medium | Complete FCI Public Posting Checklist for next public content release; retain as evidence | 2026-05-15 | Security Lead, Marketing | Open |

---

### IA.L1-3.5.1 — Identification

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| IA-1.1 | No device inventory export — managed endpoints not documented with serial numbers mapped to employees | Medium | Export MDM device list with unique identifiers and employee assignments | 2026-04-30 | IT Admin | Open |
| IA-1.2 | Service account inventory missing — IAM roles and service accounts not documented with owners | Medium | Create IAM role/service account inventory with ownership and purpose | 2026-04-30 | Infrastructure Lead | Open |
| IA-1.3 | Sample audit logs not attached — no application or CloudTrail logs showing unique identifiers in action | Low | Attach sample CloudTrail and application auth logs showing user UUID and IAM ARN | 2026-05-15 | Infrastructure Lead | Open |

---

### IA.L1-3.5.2 — Authentication

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| IA-2.1 | IdP/SSO configuration not evidenced — no screenshots or exports of the SSO provider setup | High | Attach IdP configuration showing SAML federation, MFA policy, and conditional access rules | 2026-04-15 | IT Admin | Open |
| IA-2.2 | Authentication event logs not provided — no sign-in logs showing successful/failed attempts with user IDs | Medium | Export sample 30-day sign-in logs from IdP and application auth service | 2026-04-30 | Security Lead | Open |
| IA-2.3 | MFA enrollment report missing — cannot demonstrate which users have MFA enabled | High | Export MFA enrollment status from IdP; establish policy for mandatory MFA enrollment | 2026-04-15 | IT Admin | Open |

---

### MP.L1-3.8.3 — Media Disposal

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| MP-3.1 | No recent media disposal log samples — sanitization/destruction events not documented | Medium | Create media disposal log template; record next disposal event with all required fields | 2026-05-15 | IT Admin | Open |
| MP-3.2 | No vendor certificates of destruction — third-party e-waste disposal not evidenced | Medium | Obtain certificates of destruction from e-waste vendor for most recent batch | 2026-05-15 | Facilities Manager | Open |
| MP-3.3 | No MDM wipe confirmation — device sanitization for reuse/disposal not evidenced | Low | Attach MDM wipe confirmation for next device decommissioned or reassigned | 2026-06-15 | IT Admin | Open |

---

### PE.L1-3.10.1 — Physical Access Limitation

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| PE-1.1 | Badge system access logs not attached — no sample reports for IT equipment room access | Low | Export 30-day badge reader report for IT equipment room | 2026-05-15 | Facilities Manager | Open |
| PE-1.2 | AWS inherited control attestation missing — no SOC 2 / FedRAMP report linked | Medium | Obtain and link AWS SOC 2 Type II report via AWS Artifact | 2026-04-30 | Security Lead | Open |
| PE-1.3 | Remote work security acknowledgments not on file — no signed employee agreements | Medium | Distribute remote work security acknowledgment; collect signatures from all employees | 2026-05-15 | Security Lead, HR | Open |

---

### PE.L1-3.10.3 — Visitor Access and Escort

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| PE-3.1 | No sample visitor log entries on file — cannot demonstrate visitor management is operational | Low | Retain next 5 visitor log entries as evidence samples | 2026-05-15 | Facilities Manager | Open |
| PE-3.2 | Visitor badge format not documented — no photos or descriptions of distinct visitor badges | Low | Photograph visitor badge and document format (color, dating method) | 2026-05-15 | Facilities Manager | Open |
| PE-3.3 | Employee training records for visitor escort policy not attached | Low | Attach training completion records or signed acknowledgments for visitor policy | 2026-06-15 | Security Lead, HR | Open |

---

### PE.L1-3.10.4 — Physical Access Audit Logs

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| PE-4.1 | Badge system log export not provided — no 30-day access report for restricted areas | Low | Export and attach sample badge system report for IT equipment room | 2026-05-15 | Facilities Manager | Open |
| PE-4.2 | Completed visitor log samples not attached | Low | Scan and attach recent completed visitor log pages | 2026-05-15 | Facilities Manager | Open |
| PE-4.3 | CCTV retention configuration not documented — camera coverage and settings not evidenced | Low | Document camera locations, coverage areas, and retention settings | 2026-05-15 | Facilities Manager | Open |

---

### PE.L1-3.10.5 — Physical Access Device Control

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| PE-5.1 | Badge inventory export not provided — no current list of active/inactive badges mapped to employees | Medium | Export badge inventory from access control system with status and assignment | 2026-04-30 | Facilities Manager | Open |
| PE-5.2 | No onboarding/offboarding ticket samples showing badge issuance and return | Low | Attach sample tickets from last 3 onboarding and offboarding events | 2026-05-15 | IT Admin, HR | Open |
| PE-5.3 | Quarterly badge reconciliation record not on file | Medium | Perform and document next quarterly badge audit; compare against employee roster | 2026-04-30 | Facilities Manager | Open |

---

### SC.L1-3.13.1 — Boundary Protection

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SC-1.1 | No current VPC architecture diagram — network boundaries not visually documented | High | Create and attach VPC network diagram showing all subnets, security groups, and boundary devices | 2026-04-15 | Infrastructure Lead | Open |
| SC-1.2 | Security group exports missing — no `aws ec2 describe-security-groups` output | High | Export all VPC security group rules and attach as configuration evidence | 2026-04-15 | Infrastructure Lead | Open |
| SC-1.3 | VPC Flow Logs configuration not evidenced — no CloudWatch log group settings or sample entries | Medium | Attach VPC Flow Log configuration and sample 24-hour flow log entries | 2026-04-30 | Infrastructure Lead | Open |

---

### SC.L1-3.13.5 — Public-Access System Separation

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SC-5.1 | No VPC subnet diagram showing public/private separation with route tables | High | Create and attach subnet architecture diagram with route table flows | 2026-04-15 | Infrastructure Lead | Open |
| SC-5.2 | Route table exports missing — no `aws ec2 describe-route-tables` output | Medium | Export and attach route table configurations showing subnet separation | 2026-04-30 | Infrastructure Lead | Open |
| SC-5.3 | Security group rules between DMZ and internal not explicitly documented | Medium | Attach security group rules showing default-deny between public and private subnets | 2026-04-30 | Infrastructure Lead | Open |

---

### SI.L1-3.14.1 — Flaw Remediation

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SI-1.1 | No recent vulnerability scan output — `npm audit` and `pip-audit` results not attached | Medium | Run and attach latest `npm audit` and `pip-audit` outputs from CI | 2026-04-15 | Engineering Lead | Open |
| SI-1.2 | No patching tickets showing flaw-to-fix lifecycle — end-to-end remediation not evidenced | Medium | Attach sample Dependabot PR showing detection -> fix -> merge -> deploy lifecycle | 2026-04-30 | Engineering Lead | Open |
| SI-1.3 | Dependabot alert dashboard not captured — open/closed vulnerability alerts not evidenced | Low | Screenshot GitHub Security tab showing Dependabot alerts and resolution status | 2026-04-30 | Engineering Lead | Open |

---

### SI.L1-3.14.2 — Malicious Code Protection

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SI-2.1 | EDR deployment report not provided — no console export showing endpoint coverage and protection status | High | Export EDR console deployment report showing all endpoints with real-time scanning enabled | 2026-04-15 | IT Admin | Open |
| SI-2.2 | GuardDuty configuration not evidenced — no screenshot of enabled detectors and finding types | Medium | Attach `aws guardduty list-detectors` and detector configuration output | 2026-04-15 | Infrastructure Lead | Open |
| SI-2.3 | Email security anti-malware configuration not attached | Medium | Export email security policy showing attachment scanning and phishing detection settings | 2026-04-30 | IT Admin | Open |

---

### SI.L1-3.14.4 — Update Malicious Code Protection

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SI-4.1 | EDR update compliance report missing — no dashboard showing signature/engine versions across fleet | Medium | Export EDR console update compliance report | 2026-04-15 | IT Admin | Open |
| SI-4.2 | GuardDuty detector status not verified — no AWS CLI output confirming detector is active and updating | Low | Attach `aws guardduty get-detector` output showing status and update behavior | 2026-04-30 | Infrastructure Lead | Open |
| SI-4.3 | Sample endpoint update logs not provided — no local EDR client status from a representative device | Low | Screenshot EDR client status from a sample endpoint showing last update time and versions | 2026-05-15 | IT Admin | Open |

---

### SI.L1-3.14.5 — System and File Scanning

| # | Weakness / Gap | Priority | Milestone | Scheduled Completion | Resources | Status |
|---|---------------|----------|-----------|---------------------|-----------|--------|
| SI-5.1 | EDR scan policy configuration not exported — no console export showing scheduled scan settings | Medium | Export EDR console scan policy configuration | 2026-04-15 | IT Admin | Open |
| SI-5.2 | No recent scan completion report — last scan dates per endpoint not evidenced | Medium | Export EDR console report showing scan completion status across fleet | 2026-04-30 | IT Admin | Open |
| SI-5.3 | CI security job output not captured — no GitHub Actions run showing npm audit and pip-audit results | Low | Attach screenshot or log export of recent CI security job run | 2026-04-30 | Engineering Lead | Open |

---

## Priority Distribution

### High Priority (12 items) — Target: 2026-04-15

These items represent foundational gaps that must be closed before an assessment:

| ID | Control | Gap Summary | Owner |
|----|---------|------------|-------|
| AC-1.1 | AC.L1-3.1.1 | Backend API auth middleware evidence | Engineering Lead |
| AC-1.2 | AC.L1-3.1.1 | Active account inventory from IdP | IT Admin |
| AC-2.1 | AC.L1-3.1.2 | Server-side role enforcement on API | Engineering Lead |
| IA-2.1 | IA.L1-3.5.2 | IdP/SSO configuration evidence | IT Admin |
| IA-2.3 | IA.L1-3.5.2 | MFA enrollment report | IT Admin |
| SC-1.1 | SC.L1-3.13.1 | VPC architecture diagram | Infrastructure Lead |
| SC-1.2 | SC.L1-3.13.1 | Security group exports | Infrastructure Lead |
| SC-5.1 | SC.L1-3.13.5 | Subnet separation diagram | Infrastructure Lead |
| SI-2.1 | SI.L1-3.14.2 | EDR deployment coverage report | IT Admin |

> Note: Items AC-1.1 and AC-2.1 may require code changes (implementing server-side auth middleware), not just evidence collection.

### Medium Priority (24 items) — Target: 2026-04-30 to 2026-05-15

Configuration exports, log samples, procedural documentation, and vendor attestations.

### Low Priority (15 items) — Target: 2026-05-15 to 2026-06-15

Sample logs, training records, photographs, and supplementary evidence that strengthen existing controls.

---

## Milestone Timeline

```
2026-04-15  High priority items complete (API auth, IdP config, network diagrams, EDR coverage)
2026-04-30  Medium priority batch 1 (log exports, account inventories, vendor attestations)
2026-05-15  Medium priority batch 2 + Low priority batch 1 (physical security evidence, policy docs)
2026-06-15  All remaining low priority items (training records, supplementary evidence)
2026-06-30  Target: All 17 controls moved to "implemented" status
```

---

## Document Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 (DRAFT) | 2026-03-06 | Nico Butera | Initial POA&M generated from Pretorin platform data |
