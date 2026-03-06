# System Security Plan (SSP) — CMMC Level 1

**System Name:** pretorin-test
**Framework:** CMMC 2.0 Level 1 (Foundational) Practice Catalog
**System ID:** 16bef439-f98f-4a80-af39-c738746f3a10
**Date Prepared:** 2026-03-06
**Prepared By:** Nico Butera (via Pretorin CLI + MCP)
**Status:** DRAFT — All 17 controls in `planned` status

---

## 1. System Description

**System Name:** Pretorin
**System Type:** AI-native Governance, Risk, and Compliance (GRC) platform
**Deployment Model:** Cloud-hosted on Amazon Web Services (AWS)
**Data Classification:** Federal Contract Information (FCI)
**Target Users:** Defense contractors requiring CMMC Level 1 compliance

### 1.1 System Purpose

Pretorin is a web-based GRC platform that helps defense contractors manage compliance with CMMC, NIST 800-53, FedRAMP, and other security frameworks. The platform processes, stores, and transmits Federal Contract Information (FCI) on behalf of its customers.

### 1.2 System Architecture

| Component | Technology | Subnet/Zone |
|-----------|-----------|-------------|
| CDN / WAF | AWS CloudFront + AWS WAF | AWS Edge |
| Load Balancer | Application Load Balancer (ALB) | Public subnet |
| Web Application | Next.js on ECS Fargate | Private application subnet |
| API Service | FastAPI (Python) on ECS Fargate | Private application subnet |
| Auth Service | FastAPI (Python) on ECS Fargate | Private application subnet |
| Database | Amazon RDS PostgreSQL | Private data subnet |
| Cache | Amazon ElastiCache | Private data subnet |
| Secrets | AWS Secrets Manager | AWS managed (VPC endpoint) |
| Object Storage | Amazon S3 (encrypted) | AWS managed (VPC endpoint) |
| Monitoring | CloudWatch, CloudTrail, GuardDuty | AWS managed |
| Admin Access | AWS Systems Manager Session Manager | No public ports |

### 1.3 Network Architecture

- **VPC** with public, private application, and private data subnets across multiple AZs
- **Public subnet:** ALB only (accepts traffic from CloudFront managed prefix list)
- **Private application subnet:** ECS Fargate tasks (no public IPs)
- **Private data subnet:** RDS, ElastiCache (accessible only from application subnet SGs)
- **NAT Gateway** for controlled outbound access from private subnets
- **VPC Endpoints** for S3, Secrets Manager, SQS, ECR, CloudWatch (avoids internet traversal)
- **Default-deny** security groups on all resources; NACLs as secondary boundary

### 1.4 System Boundary

The authorization boundary includes:
- All AWS resources within the production VPC
- CloudFront distributions serving the platform
- CI/CD pipeline (GitHub Actions) that deploys to production
- Corporate endpoints (managed laptops) used to access AWS and the platform
- Corporate office space where employees work with FCI

Inherited controls from AWS (physical security, media handling for cloud infrastructure) are documented per control where applicable.

---

## 2. Information Types and Data Flow

**Federal Contract Information (FCI)** enters the system via:
1. User browser (HTTPS) -> CloudFront -> ALB -> API/Auth services -> RDS/S3
2. CI/CD pipeline (GitHub Actions) -> ECR -> ECS Fargate deployment

FCI resides in:
- RDS PostgreSQL (encrypted at rest with AES-256, in transit with TLS)
- S3 buckets (SSE-S3/SSE-KMS encryption, Block Public Access enabled)
- ElastiCache (encryption at rest and in transit)
- Temporarily in ECS task memory during processing

FCI does NOT reside on:
- Public subnets
- CloudFront edge caches (dynamic API responses not cached)
- Any publicly accessible system

---

## 3. Roles and Responsibilities

| Role | Responsibility |
|------|---------------|
| System Owner | Overall accountability for system security and CMMC compliance |
| Security Lead | Policy development, risk management, incident response |
| Infrastructure Lead | AWS architecture, network security, patching |
| Engineering Lead | Application security, code reviews, dependency management |
| IT Admin | Endpoint management, MDM, user provisioning |
| Facilities Manager | Physical access controls, visitor management, badge administration |

---

## 4. Control Implementation Statements

### 4.1 Access Control (AC)

#### AC.L1-3.1.1 — Authorized Access Control

**Requirement:** Limit information system access to authorized users, processes acting on behalf of authorized users, or devices (including other information systems).

**Implementation:**

Access to the Pretorin platform is restricted at multiple layers:

- **Identity & Authentication:** All users authenticate via centralized identity provider (SSO/SAML 2.0). Unique user accounts enforced; shared/generic accounts prohibited. Default-deny: new users receive no access until assigned to an approved role.
- **Application Authorization:** Client-side RoleGuard checks roles/permissions before rendering routes. Five roles defined: owner, admin, member, viewer, auditor. Role permission matrix explicitly defines capabilities per role in code (`apps/web/src/data/organizations.ts`). Organization membership model stores per-org role (`apps/auth/app/models/organization_membership.py`).
- **Network Access:** VPC security groups enforce default-deny inbound. Only HTTPS (443) via CloudFront/ALB is publicly accessible. Administrative access via AWS Systems Manager Session Manager (IAM-authenticated, CloudTrail-logged). No SSH/RDP exposed to the internet.
- **Service-to-Service:** Dedicated IAM roles per ECS task/Lambda with least-privilege permissions. CI/CD uses GitHub Actions OIDC federation (no stored secrets). API keys/service credentials managed via AWS Secrets Manager with rotation.

**Evidence:** 6 items (RBAC configuration, role permission matrix, organization membership model, VPC security group configuration, auth service code, CloudFront/WAF configuration)

**Gaps:**
- Backend API authorization middleware evidence (server-side JWT validation) needs to be attached
- Active account inventory export from identity provider
- Device authorization controls (MDM inventory, VPN configuration)

---

#### AC.L1-3.1.2 — Transaction and Function Control

**Requirement:** Limit information system access to the types of transactions and functions that authorized users are permitted to execute.

**Implementation:**

The platform enforces function-level access control through a defined role-permission matrix:

| Role | Create/Edit | Manage Controls | Upload Evidence | Export Data | Manage Users |
|------|------------|----------------|-----------------|-------------|--------------|
| owner | Yes | Yes | Yes | Yes | Yes |
| admin | Yes | Yes | Yes | Yes | Yes |
| member | Yes | Yes | Yes | No | No |
| viewer | No | No | No | No | No |
| auditor | No | No | No | Read-only | No |

- Destructive actions (delete system, remove evidence, change roles) restricted to owner/admin only
- AWS IAM policies follow least privilege: developers get read-only logs access; only CI/CD can deploy
- No long-lived IAM access keys for human users; all console access via SSO
- Quarterly review of role assignments to detect privilege creep

**Evidence:** 3 items (role permission matrix, RoleGuard code, IAM policy documentation)

**Gaps:**
- Server-side API middleware enforcing role checks on mutating endpoints
- User-to-role assignment export from identity provider
- Privileged function audit logs showing denied attempts

---

#### AC.L1-3.1.20 — External Connection Control

**Requirement:** Verify and control/limit connections to and use of external information systems.

**Implementation:**

- **Inbound:** Only HTTPS (443) via CloudFront/ALB. All other inbound ports blocked at VPC security groups and NACLs.
- **Administrative:** No SSH/RDP exposed. All admin access via AWS Systems Manager Session Manager (IAM-authenticated, CloudTrail-logged) or VPN with SSO + MFA.
- **Vendor/Partner:** Dedicated VPN profiles with least-privilege network access, time-bound sessions, full logging. No persistent vendor accounts.
- **Outbound (Egress):** Default-deny from application subnets. NAT gateway routes outbound; security groups limit to HTTPS (443) and specific AWS service endpoints.
- **External Devices:** BYOD restricted. Personal devices cannot access AWS environment without MDM enrollment. USB/removable media blocked via MDM policy.
- **Approved Integrations:** Registry maintained for all external connections (IdP, GitHub, AWS Bedrock, package registries, CDN). Reviewed quarterly.

**Evidence:** 3 items (VPC/security group configuration, approved integrations registry, network architecture documentation)

**Gaps:**
- Firewall/security group export (`aws ec2 describe-security-groups`)
- VPN authentication logs showing SSO + MFA verification
- Vendor access approval records and session logs

---

#### AC.L1-3.1.22 — Public Information Control

**Requirement:** Control information posted or processed on publicly accessible information systems.

**Implementation:**

- **Public Systems Inventory:** Corporate website, GitHub public repos, social media, PyPI/npm registries
- **Designated Publishers:** Only marketing lead, CTO, and engineering lead have publishing rights. Unique accounts with MFA; no shared credentials.
- **Pre-Publication Review:** FCI Public Posting Checklist required before any public posting. Content reviewed for contract numbers, delivery schedules, pricing, SOW excerpts, customer POCs, internal system details.
- **AWS S3:** Block Public Access enabled at account level. No public buckets in production. AWS Config rules `s3-bucket-public-read-prohibited` and `s3-bucket-public-write-prohibited` active with auto-remediation.
- **GitHub:** Branch protection requires PR review. Secret scanning enabled on all public repos. Push access restricted to repo admins.
- **Package Publishing:** Automated via CI/CD only; no manual publishes from developer machines.
- **Periodic Audit:** Quarterly review of public content for inadvertent FCI exposure. Rapid takedown within 1 hour if FCI found publicly exposed.

**Evidence:** 3 items (S3 Block Public Access configuration, GitHub repo settings, public systems inventory)

**Gaps:**
- S3 Block Public Access screenshots/CLI output
- GitHub branch protection and access configuration export
- Sample pre-publication approval records (completed FCI checklists)

---

### 4.2 Identification and Authentication (IA)

#### IA.L1-3.5.1 — Identification

**Requirement:** Identify information system users, processes acting on behalf of users, or devices.

**Implementation:**

- **User Identification:** Every user assigned a globally unique UUID v4 at registration (`apps/auth/app/models/user.py:48`). Email serves as human-readable unique identifier with database-level `unique=True` constraint. No shared accounts; duplicate check enforced at registration.
- **Service/Process Identification:** Dedicated IAM roles per service (ECS task role, CI/CD role, inference role), each uniquely named and scoped. CI/CD uses GitHub Actions OIDC federation with unique per-workflow-run identity.
- **Device Identification:** Managed endpoints tracked via MDM with unique device identifiers (serial number, MDM device ID). Session model captures device info and IP for each login (`user.py:187-188`).
- **Logging:** All authentication events logged with user UUID, email, IP address, and device info. AWS CloudTrail logs include IAM principal ARN for every API call.

**Evidence:** 1 item (user model code showing UUID and unique email constraint)

**Gaps:**
- MDM device inventory export with serial numbers mapped to employees
- Service account/IAM role inventory with owners
- Sample audit logs showing unique identifiers in action

---

#### IA.L1-3.5.2 — Authentication

**Requirement:** Authenticate (or verify) the identities of those users, processes, or devices, as a prerequisite to allowing access to organizational information systems.

**Implementation:**

- **Password Authentication:** Argon2id hashing (OWASP recommended parameters: `time_cost=3`, `memory_cost=65536`, `parallelism=4`). NIST 800-63B password validation (min 12 chars, max 128, common password check). Timing-safe comparison. Automatic rehashing on parameter upgrade.
- **Account Lockout:** Failed attempts tracked per user. Account locked after configurable max failures for defined duration. Constant-time dummy hash on invalid email prevents enumeration.
- **Multi-Factor Authentication:** TOTP 2FA with encrypted secrets (AES via CryptoService). QR code provisioning. Hashed backup codes. JWT `mfa_verified` claim for critical actions. Rate limiting on MFA endpoints.
- **Session Management:** JWT access tokens (HS256/RS256) with configurable expiration. Refresh token rotation with SHA-256 hash storage. HTTP-only, Secure, SameSite=Lax cookies. Logout revokes all sessions.
- **SSO/OAuth:** Google, Microsoft, Okta, GitHub supported. Unique constraint on provider + provider_user_id. SSO-only users have null password_hash.
- **Non-Human Auth:** AWS IAM roles with temporary STS credentials. GitHub OIDC federation for CI/CD. Database credentials via Secrets Manager with rotation.

**Evidence:** 1 item (Argon2id password service code with OWASP parameters)

**Gaps:**
- IdP/SSO configuration screenshots
- Authentication event logs (successful/failed attempts)
- MFA enrollment report

---

### 4.3 Media Protection (MP)

#### MP.L1-3.8.3 — Media Disposal

**Requirement:** Sanitize or destroy information system media containing Federal Contract Information before disposal or release for reuse.

**Implementation:**

- **Sanitization Methods by Media Type:**
  - Employee laptops (SSD): Cryptographic erase (FileVault/BitLocker key destruction) or MDM secure erase
  - Mobile devices: MDM-initiated factory reset + wipe verification
  - USB/removable drives: Secure erase tool or physical destruction
  - Paper documents: Cross-cut shredding
  - AWS EBS/S3: Inherited from AWS (NIST 800-88 per AWS SOC 2)
- **Workflow:** Identify -> Classify -> Sanitize -> Verify -> Document -> Dispose/Reuse
- **Laptop Reuse:** Full reimage via MDM before reassignment. Previous user data removed. Reimage confirmation logged.
- **Third-Party Disposal:** E-waste vendor vetted for NIST 800-88 compliance. Chain-of-custody maintained. Certificate of destruction obtained per batch. Certificates retained for contract period + 3 years.
- **Full-Disk Encryption:** All company laptops have FDE enabled (FileVault/BitLocker). MDM enforces encryption policy.

**Evidence:** 1 item (media disposal SOP documentation)

**Gaps:**
- Recent media disposal log samples
- Vendor certificates of destruction
- MDM wipe confirmation for a decommissioned device

---

### 4.4 Physical and Environmental Protection (PE)

#### PE.L1-3.10.1 — Physical Access Limitation

**Requirement:** Limit physical access to organizational information systems, equipment, and the respective operating environments to authorized individuals.

**Implementation:**

- **Cloud Infrastructure (Inherited):** AWS provides physical security for all data centers — biometric access, 24/7 security staff, video surveillance, mantrap entry, environmental controls. Documented in AWS SOC 2 Type II and FedRAMP authorization.
- **Corporate Office:** Badge-controlled entry during and after business hours. IT equipment room has separate badge access limited to IT staff and facilities manager (3-4 people). Locked cabinets for spare hardware and media. Reception separates public lobby from workspace.
- **Remote/Telework:** Employees must prevent household members from accessing company devices. Company laptops secured when unattended. Privacy screens in public spaces. No FCI on removable media at home. Requirements documented in acceptable use policy.

**Evidence:** 1 item (physical security policy documentation)

**Gaps:**
- Badge system access logs for IT equipment room
- AWS SOC 2 / FedRAMP inherited control attestation
- Signed remote work security acknowledgments

---

#### PE.L1-3.10.3 — Visitor Access and Escort

**Requirement:** Escort visitors and monitor visitor activity.

**Implementation:**

- **Visitor Definition:** Vendors, customers, delivery personnel, interview candidates, technicians, building maintenance, and any non-badged individuals.
- **Check-In Process:** Government-issued ID verified at reception. Visitor log entry created (name, org, purpose, host, date, time in). Visually distinct dated visitor badge issued.
- **Escort:** Named host provides continuous line-of-sight escort in all areas beyond lobby. Visitors may not access systems or plug devices into network ports. Third-party service visits scheduled in advance; IT staff escorts.
- **Challenge Policy:** Employees trained to challenge unknown/unbadged individuals and escort to reception.
- **AWS Data Centers:** AWS manages all visitor access per FedRAMP controls. No Pretorin employees visit AWS data centers.

**Evidence:** 1 item (visitor management procedure documentation)

**Gaps:**
- Sample visitor log entries
- Visitor badge format documentation/photos
- Employee training records for visitor escort policy

---

#### PE.L1-3.10.4 — Physical Access Audit Logs

**Requirement:** Maintain audit logs of physical access.

**Implementation:**

- **Badge System:** Captures employee name/ID, door/location, date/time, granted/denied status. Logs retained 1 year.
- **Visitor Log:** Captures visitor name, organization, purpose, host/escort, check-in/out times, areas visited. Retained 1 year (paper logs scanned monthly).
- **CCTV:** Cameras at office entrance, reception, IT equipment room hallway. Footage retained 30 days minimum.
- **Log Protection:** Stored in access-controlled locations. Only IT admin and facilities manager can modify/export.
- **AWS:** CloudTrail provides audit logs for all AWS console/API access. AWS maintains physical access audit logs for data centers per SOC 2/FedRAMP.

**Evidence:** 1 item (physical access logging procedure documentation)

**Gaps:**
- Badge system 30-day log export for IT equipment room
- Completed visitor log samples
- CCTV retention configuration documentation

---

#### PE.L1-3.10.5 — Physical Access Device Control

**Requirement:** Control and manage physical access devices.

**Implementation:**

- **Device Inventory:** Employee proximity badges (1 per employee), visitor badges (pool of 10, dated), mechanical keys (2 master sets), after-hours keypad code.
- **Lifecycle:** Onboarding ticket triggers badge issuance with unique ID and access group assignment. Employee signs responsibility acknowledgment. Offboarding requires badge return on last day; badge disabled within 24 hours (same-day for terminations). Lost badges immediately disabled and replaced.
- **Reconciliation:** Quarterly badge audit — active badges compared against employee roster. Dormant badges (no tap in 90 days) flagged and disabled.
- **Mechanical Keys:** Stored in locked cabinet in IT equipment room. Issuance logged. Duplication restricted to facilities manager. Unreturned keys trigger rekeying assessment.
- **Keypad Code:** Changed quarterly and after any personnel departure.

**Evidence:** 1 item (physical access device management procedure)

**Gaps:**
- Badge inventory export (active/inactive mapped to employees)
- Onboarding/offboarding ticket samples showing badge issuance/return
- Most recent quarterly badge reconciliation record

---

### 4.5 System and Communications Protection (SC)

#### SC.L1-3.13.1 — Boundary Protection

**Requirement:** Monitor, control, and protect organizational communications at the external boundaries and key internal boundaries of the information systems.

**Implementation:**

- **External Boundary:** All traffic enters via CloudFront -> ALB (HTTPS 443 only). WAF filters malicious requests. Outbound via NAT gateway to specific destinations only. No SSH/RDP exposed.
- **Internal Boundaries:** Public subnet (ALB only) -> Private application subnet (ECS tasks) -> Private data subnet (RDS, ElastiCache). East-west traffic restricted by security groups.
- **Default-Deny:** All security groups start deny-all inbound with explicit allow rules. NACLs as secondary boundary. No "any/any" rules.
- **Boundary Logging:** VPC Flow Logs on all subnets (CloudWatch Logs). ALB access logs (S3). WAF logs (CloudWatch). CloudTrail for all API calls. NTP synced for log correlation.

**Evidence:** 1 item (network boundary architecture documentation)

**Gaps:**
- Current VPC architecture diagram
- Security group exports (`aws ec2 describe-security-groups`)
- VPC Flow Logs configuration and sample entries

---

#### SC.L1-3.13.5 — Public-Access System Separation

**Requirement:** Implement subnetworks for publicly accessible system components that are physically or logically separated from internal networks.

**Implementation:**

- **Public Components:** CloudFront distribution (`platform.pretorin.com`) and ALB in public subnet. All other components in private subnets with no public IPs.
- **Subnet Separation:** Public subnet has ALB only (accepts CloudFront traffic via managed prefix list). Private application subnet has ECS Fargate tasks. Private data subnet has RDS and ElastiCache.
- **Route Tables:** Public subnet routes to internet gateway; private subnets route to NAT gateway only.
- **Enforcement:** Security groups enforce default-deny between subnets. No direct path from public to data subnet — traffic must flow through ALB -> application -> data. CloudFront Origin Access Identity ensures ALB only accepts CloudFront requests.
- **VPC Endpoints:** S3, Secrets Manager, SQS, ECR, CloudWatch endpoints keep internal traffic off the internet.

**Evidence:** 1 item (subnet separation architecture documentation)

**Gaps:**
- VPC subnet diagram with route tables
- Route table exports (`aws ec2 describe-route-tables`)
- Security group rules showing default-deny between DMZ and internal

---

### 4.6 System and Information Integrity (SI)

#### SI.L1-3.14.1 — Flaw Remediation

**Requirement:** Identify, report, and correct information and information system flaws in a timely manner.

**Implementation:**

- **Flaw Identification:** CI pipeline runs `npm audit --audit-level=high` and `pip-audit` on every push/PR (`.github/workflows/ci.yml`). GitHub Dependabot alerts enabled. CISA KEV catalog monitored. AWS Health Dashboard and Security Hub findings.
- **Remediation Timelines:** Critical/Active Exploit: 48 hours. High: 14 days. Medium: 30 days. Low: 90 days.
- **Patching:** Application dependencies via Dependabot PRs. Container base images updated in Dockerfiles. AWS managed services patched by AWS. Endpoints patched via MDM.
- **Exceptions:** Documented with CVE ID, compensating control, and review date. Examples: CVE-2024-23342 (no upstream fix), CVE-2026-1703 (waiting for pip 26.0 stable).
- **Build Gate:** Security job fails the CI build if high/critical vulnerabilities are found.

**Evidence:** 1 item (CI pipeline security job configuration)

**Gaps:**
- Recent `npm audit` and `pip-audit` output
- Patching tickets showing flaw-to-fix lifecycle
- Dependabot alert dashboard screenshot

---

#### SI.L1-3.14.2 — Malicious Code Protection

**Requirement:** Provide protection from malicious code at appropriate locations within organizational information systems.

**Implementation:**

- **Endpoints:** Enterprise EDR with real-time scanning, automatic quarantine, tamper protection. USB scanned on insertion.
- **Email:** Cloud-managed email security with attachment scanning and phishing detection.
- **Web:** DNS filtering via Route 53 Resolver DNS Firewall blocking known-malicious domains.
- **Containers:** Image scanning in CI/CD before deployment for vulnerabilities and malware.
- **AWS Workloads:** Amazon GuardDuty for runtime threat detection (EC2/ECS/S3/IAM). Findings routed to SNS for immediate notification.
- **Code:** GitHub code scanning (SAST) and secret scanning on every PR.

**Evidence:** 1 item (malicious code protection architecture documentation)

**Gaps:**
- EDR deployment report showing endpoint coverage and real-time scanning status
- GuardDuty configuration showing enabled detectors
- Email security anti-malware policy configuration

---

#### SI.L1-3.14.4 — Update Malicious Code Protection

**Requirement:** Update malicious code protection mechanisms when new releases are available.

**Implementation:**

- **Endpoint EDR:** Auto-update enabled for signatures, engine, and sensor via cloud console. Checks multiple times per day.
- **GuardDuty:** AWS-managed; threat intelligence updated automatically.
- **DNS Filtering:** Route 53 Resolver DNS Firewall rule groups updated automatically by AWS Managed Domain Lists.
- **Email:** Cloud-managed email security updates automatically.
- **Monitoring:** EDR console dashboard reviewed daily. Devices >48 hours out of date flagged. Stale agents (>72 hours) trigger automated alert.
- **Remote Devices:** EDR agents update directly from vendor CDN; no VPN dependency.

**Evidence:** 1 item (update management procedure documentation)

**Gaps:**
- EDR console update compliance report (signature/engine versions across fleet)
- GuardDuty detector status (AWS CLI output)
- Sample endpoint update logs

---

#### SI.L1-3.14.5 — System and File Scanning

**Requirement:** Perform periodic scans of the information system and real-time scans of files from external sources as files are downloaded, opened, or executed.

**Implementation:**

- **Real-Time:** On-access scanning for all file operations (download, open, execute, copy). Browser downloads, email attachments, removable media, and network shares all scanned.
- **Scheduled Scans:** Quick scan daily (common malware locations, running processes). Full scan weekly (all files on disk).
- **CI/CD Scanning:** `npm audit` and `pip-audit` on every push/PR. Build fails on high/critical findings.
- **Container Scanning:** Docker images scanned before deployment.
- **Monitoring:** Scan completion tracked in EDR console. Missed scans flagged. Quarantine enabled with user notification.

**Evidence:** 1 item (scanning configuration documentation)

**Gaps:**
- EDR scan policy configuration export
- Recent scan completion report (last scan dates per endpoint)
- CI security job output (GitHub Actions run showing audit results)

---

## 5. Inherited Controls

The following controls are partially or fully inherited from AWS:

| Control | Inherited Component | AWS Evidence |
|---------|-------------------|--------------|
| PE.L1-3.10.1 | Data center physical security | AWS SOC 2 Type II, FedRAMP authorization |
| PE.L1-3.10.3 | Data center visitor management | AWS SOC 2 Type II |
| PE.L1-3.10.4 | Data center access logs | AWS SOC 2 Type II |
| PE.L1-3.10.5 | Data center access devices | AWS SOC 2 Type II |
| MP.L1-3.8.3 | Cloud media sanitization (EBS/S3) | AWS NIST 800-88 compliance per SOC 2 |
| SC.L1-3.13.1 | Cloud network infrastructure | VPC, Security Groups, NACLs |
| SC.L1-3.13.5 | Cloud subnet architecture | VPC subnet separation |

---

## 6. Document Revision History

| Version | Date | Author | Description |
|---------|------|--------|-------------|
| 0.1 (DRAFT) | 2026-03-06 | Nico Butera | Initial SSP generated from Pretorin platform data |
