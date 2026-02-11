# Compliance Gap Analysis Workflow

A systematic approach to assessing a codebase against a compliance framework's controls.

## Step 1: Scope the Assessment

Determine which framework and which control families to assess.

1. Call `pretorin_list_frameworks` if the framework isn't specified
2. Call `pretorin_list_control_families` for the chosen framework
3. Identify which families are relevant to the codebase being analyzed

Not all families will have code evidence. Prioritize based on the type below.

## Step 2: Prioritize Control Families

### High Priority (Direct Code Evidence)

These families typically have strong evidence in source code:

| Family | What to Search For |
|---|---|
| **Access Control (AC)** | Authentication systems, RBAC/ABAC, session management, user provisioning |
| **Audit & Accountability (AU)** | Logging frameworks, audit trails, log retention, structured logging |
| **Identification & Authentication (IA)** | Login flows, MFA, password hashing, credential storage, OAuth/SAML |
| **System & Communications Protection (SC)** | TLS config, encryption, network boundaries, CORS, API security |
| **Configuration Management (CM)** | Config files, env handling, version pinning, baseline settings, IaC |

### Medium Priority (Mixed Code/Policy)

| Family | What to Search For |
|---|---|
| **System Acquisition (SA)** | Secure development practices, dependency management, SAST/DAST configs |
| **System Integrity (SI)** | Input validation, error handling, malware protection configs |
| **Assessment (CA)** | Security testing configs, vulnerability scanning, CI/CD security gates |

### Lower Priority (Mostly Policy)

These families are primarily documentation-based and unlikely to have code evidence:

- Awareness & Training (AT)
- Planning (PL)
- Personnel Security (PS)
- Physical Protection (PE)
- Program Management (PM)

## Step 3: Collect Evidence

For each high-priority family:

1. Call `pretorin_list_controls` filtered by the family
2. For each relevant control, call `pretorin_get_control_references` to understand requirements
3. Search the codebase using these patterns:

**File patterns:**
```
**/auth/**          **/users/**         **/accounts/**
**/logging/**       **/audit/**         **/security/**
**/config/**        **/settings/**      **/crypto/**
**/identity/**      **/iam/**           **/rbac/**
**/middleware/**     **/terraform/**     **/k8s/**
```

**Keyword patterns:**
```
authenticate, authorize, permission, role, session
log, audit, event, trace, record
encrypt, tls, ssl, https, certificate
config, setting, baseline, default
password, credential, hash, mfa, token
```

4. For each piece of evidence found, note the file path, line numbers, and what it demonstrates

## Step 4: Assess Implementation Status

For each control, assign a status:

| Status | Criteria |
|---|---|
| **Implemented** | Full control requirements met with clear code evidence |
| **Partial** | Some requirements met, others missing or incomplete |
| **Planned** | Architecture supports it but feature not built yet |
| **Not Applicable** | Control doesn't apply to this component |
| **Gap** | Control requirements not addressed at all |

## Step 5: Produce the Report

Structure the gap analysis output as:

### Summary
- Framework assessed and total controls in scope
- Counts by status (implemented, partial, planned, not applicable, gap)
- Overall compliance posture assessment

### Family-by-Family Findings
For each assessed family:
- Family name and total controls
- Status breakdown
- Key findings with evidence references
- Gaps identified with remediation recommendations

### Priority Remediation Items
Rank gaps by:
1. Controls with the highest security impact
2. Controls that are prerequisites for other controls (check related controls)
3. Controls that are easiest to implement (quick wins)

### Evidence Summary
For each assessed control:
- Control ID and title
- Implementation status
- Evidence file paths and descriptions
- Recommendations if partial or gap

## Tips

- Start broad (family level) and drill into specific controls where evidence exists
- Use `pretorin_get_control_references` liberally — the guidance and objectives fields explain what assessors look for
- Check related controls to identify dependencies between controls
- For infrastructure evidence, look at Terraform, CloudFormation, Dockerfiles, Helm charts, and CI/CD configs
- For application evidence, focus on auth, logging, crypto, and configuration code
