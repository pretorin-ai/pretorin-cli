# Gap Analysis Workflow

A systematic approach to assessing a codebase against a compliance framework's controls.

## Step 1: Scope the Assessment

Determine which framework and control families to assess.

```bash
# List frameworks if not specified
pretorin frameworks list

# List control families for the chosen framework
pretorin frameworks families fedramp-moderate
```

Not all families will have code evidence. Prioritize based on evidence likelihood.

## Step 2: Prioritize Control Families

### High Priority (Direct Code Evidence)

These families typically have strong evidence in source code:

| Family | What to Search For |
|--------|-------------------|
| **Access Control (AC)** | Authentication systems, RBAC/ABAC, session management, user provisioning |
| **Audit & Accountability (AU)** | Logging frameworks, audit trails, log retention, structured logging |
| **Identification & Authentication (IA)** | Login flows, MFA, password hashing, credential storage, OAuth/SAML |
| **System & Communications Protection (SC)** | TLS config, encryption, network boundaries, CORS, API security |
| **Configuration Management (CM)** | Config files, env handling, version pinning, baseline settings, IaC |

### Medium Priority (Mixed Code/Policy)

| Family | What to Search For |
|--------|-------------------|
| **System Acquisition (SA)** | Secure development practices, dependency management, SAST/DAST configs |
| **System Integrity (SI)** | Input validation, error handling, malware protection configs |
| **Assessment (CA)** | Security testing configs, vulnerability scanning, CI/CD security gates |

### Lower Priority (Mostly Policy)

Primarily documentation-based, unlikely to have code evidence:

- Awareness & Training (AT)
- Planning (PL)
- Personnel Security (PS)
- Physical Protection (PE)
- Program Management (PM)

## Step 3: Collect Evidence

For each high-priority family:

1. List controls filtered by family:
   ```bash
   pretorin frameworks controls fedramp-moderate --family access-control
   ```

2. For each relevant control, get AI guidance:
   ```bash
   pretorin frameworks control fedramp-moderate ac-02
   ```
   References and AI guidance are shown by default. The `ai_guidance` field provides evidence expectations, implementation considerations, and common failures. Use `--brief` to show only the basic info panel.

3. Search the codebase using guidance-informed patterns:

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

4. For each piece of evidence, note the file path, line numbers, and what it demonstrates.

## Step 4: Assess Implementation Status

For each control, assign a status:

| Status | Criteria |
|--------|----------|
| **Implemented** | Full requirements met with clear code evidence |
| **Partial** | Some requirements met, others missing or incomplete |
| **Planned** | Architecture supports it but feature not built yet |
| **Not Applicable** | Control doesn't apply to this component |
| **Gap** | Control requirements not addressed at all |

Use `ai_guidance.common_failures` to calibrate your assessment — if the codebase exhibits a known failure pattern, it's likely a gap or partial implementation.

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
- Gaps with remediation recommendations

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

## Example Output

See the [example gap analysis](./gap-analysis-example.md) for a complete sample report.

## Tips

- Start broad (family level) and drill into specific controls where evidence exists
- Use `pretorin frameworks control <fw> <ctrl>` for AI guidance — it provides the richest context (references are included by default; use `--brief` to skip them)
- Check related controls to identify dependencies
- For infrastructure evidence, look at Terraform, CloudFormation, Dockerfiles, Helm charts, and CI/CD configs
- For application evidence, focus on auth, logging, crypto, and configuration code
