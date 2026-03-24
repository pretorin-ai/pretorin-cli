# Framework Selection Guide

Use this decision tree to help users identify the right compliance framework for their situation.

## Using AI Context for Selection

Call `pretorin_get_framework` with a candidate framework ID to get the `ai_context` field, which includes purpose, target audience, regulatory context, scope, and key concepts. This helps confirm whether a framework is the right fit for the user's situation.

## Decision Tree

### 1. Federal Agency (US Government)

**Use: NIST 800-53 Rev 5** (`nist-800-53-r5`)

The foundational catalog for federal information systems. All other US government frameworks derive from it. Contains 324 controls across 20 families. Use this when the organization IS a federal agency and needs the full control catalog.

### 2. Federal Contractor Handling CUI

**Use: NIST 800-171 Rev 3** (`nist-800-171-r3`)

Protects Controlled Unclassified Information (CUI) in non-federal systems. A focused subset of 800-53 with 130 requirements. Use this when the organization is a contractor, university, or other non-federal entity that handles CUI under DFARS 252.204-7012 or similar requirements.

### 3. Cloud Service Provider to Government

**Use: FedRAMP** (`fedramp-low`, `fedramp-moderate`, `fedramp-high`)

Based on NIST 800-53 with additional cloud-specific requirements. Required for cloud services used by federal agencies.

**Choosing the impact level:**

| Level | Framework ID | Controls | Use When |
|---|---|---|---|
| **Low** | `fedramp-low` | 135 | Public, non-sensitive data. Loss would have limited adverse effect. |
| **Moderate** | `fedramp-moderate` | 181 | CUI, PII, sensitive but not critical data. Loss would have serious adverse effect. Most common level. |
| **High** | `fedramp-high` | 191 | Life-safety, financial, law enforcement, or emergency services data. Loss would have severe or catastrophic effect. |

When unsure, **FedRAMP Moderate** is the most common starting point for cloud services handling government data.

### 4. Defense Industrial Base (DIB)

**Use: CMMC** (`cmmc-l1`, `cmmc-l2`, `cmmc-l3`)

Cybersecurity Maturity Model Certification for defense contractors. Required by DoD contracts.

**Choosing the level:**

| Level | Framework ID | Controls | Use When |
|---|---|---|---|
| **Level 1** | `cmmc-l1` | 17 | Handles only Federal Contract Information (FCI). Basic cyber hygiene. |
| **Level 2** | `cmmc-l2` | 110 | Handles CUI. Aligns with NIST 800-171. Most defense contractors need this level. |
| **Level 3** | `cmmc-l3` | 24 | Highest sensitivity CUI. Advanced/progressive security practices on top of Level 2. |

Note: CMMC Level 3 controls are **in addition to** Level 2. An organization at Level 3 must also satisfy all Level 2 controls.

## Framework Relationships

Understanding how frameworks relate helps with cross-compliance:

```
NIST 800-53 Rev 5 (full catalog, 324 controls)
├── FedRAMP Low/Moderate/High (800-53 subset + cloud requirements)
├── NIST 800-171 Rev 3 (800-53 subset for CUI in non-federal systems)
│   └── CMMC Level 2 (maps to 800-171 requirements)
└── CMMC Level 3 (advanced controls beyond 800-171)
```

If an organization is already compliant with a parent framework, many child framework controls are already satisfied. Use `pretorin_get_control_references` to find related controls across frameworks.

## Quick Reference

| Situation | Framework | Typical ID |
|---|---|---|
| "We're a federal agency" | NIST 800-53 | `nist-800-53-r5` |
| "We handle CUI as a contractor" | NIST 800-171 | `nist-800-171-r3` |
| "We're a cloud service for government" | FedRAMP | `fedramp-moderate` |
| "We have a DoD contract" | CMMC | `cmmc-l2` |
| "We need to handle both CUI and cloud" | FedRAMP + 800-171 | Start with `fedramp-moderate` |
| "We're not sure yet" | Start with NIST 800-53 | `nist-800-53-r5` |
