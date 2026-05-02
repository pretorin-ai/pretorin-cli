# Supported Frameworks

Pretorin provides access to 30+ compliance frameworks and profiles spanning federal, contractor, defense industrial base, and related compliance requirements.

## Representative Frameworks

The table below highlights a representative subset of commonly used frameworks in Pretorin. Always call `pretorin frameworks list` to get the current catalog from the API for your environment.

| ID | Title | Version | Tier | Families | Controls |
|----|-------|---------|------|----------|----------|
| `nist-800-53-r5` | NIST SP 800-53 Rev 5 | 5.2.0 | foundational | 20 | 324 |
| `nist-800-171-r3` | NIST SP 800-171 Revision 3 | 1.0.0 | foundational | 17 | 130 |
| `fedramp-low` | FedRAMP Rev 5 Low Baseline | fedramp2.1.0 | operational | 18 | 135 |
| `fedramp-moderate` | FedRAMP Rev 5 Moderate Baseline | fedramp2.1.0 | operational | 18 | 181 |
| `fedramp-high` | FedRAMP Rev 5 High Baseline | fedramp2.1.0 | operational | 18 | 191 |
| `cmmc-l1` | CMMC 2.0 Level 1 (Foundational) | 2.0 | operational | 6 | 17 |
| `cmmc-l2` | CMMC 2.0 Level 2 (Advanced) | 2.0 | operational | 14 | 110 |
| `cmmc-l3` | CMMC 2.0 Level 3 (Expert) | 2.0 | strategic | 10 | 24 |

### Framework Tiers

Each framework has a **tier** classification displayed in the `pretorin frameworks list` output:

| Tier | Description |
|------|-------------|
| **foundational** | Base catalogs that other frameworks derive from (e.g., NIST 800-53, 800-171) |
| **operational** | Baselines and profiles used for day-to-day compliance (e.g., FedRAMP, CMMC L1/L2) |
| **strategic** | Advanced or specialized frameworks for high-assurance environments (e.g., CMMC L3) |

## Framework Relationships

Understanding how frameworks relate helps with cross-compliance:

```
NIST 800-53 Rev 5 (full catalog, 324 controls)
├── FedRAMP Low/Moderate/High (800-53 subset + cloud requirements)
├── NIST 800-171 Rev 3 (800-53 subset for CUI in non-federal systems)
│   └── CMMC Level 2 (maps to 800-171 requirements)
└── CMMC Level 3 (advanced controls beyond 800-171)
```

If an organization is already compliant with a parent framework, many child framework controls are already satisfied.

## NIST SP 800-53 Rev 5

The foundational catalog for federal information systems. Contains 324 controls across 20 families covering all aspects of information security. All other US government frameworks derive from it.

**Target audience:** Federal agencies

## NIST SP 800-171 Rev 3

Protects Controlled Unclassified Information (CUI) in non-federal systems. A focused subset of 800-53 with 130 requirements.

**Target audience:** Federal contractors, universities, and other non-federal entities handling CUI under DFARS 252.204-7012 or similar requirements.

## FedRAMP

Based on NIST 800-53 with additional cloud-specific requirements. Required for cloud services used by federal agencies.

**Impact levels:**

| Level | ID | Controls | Use When |
|-------|-----|----------|----------|
| Low | `fedramp-low` | 135 | Public, non-sensitive data. Limited adverse effect from loss. |
| Moderate | `fedramp-moderate` | 181 | CUI, PII, sensitive data. Serious adverse effect from loss. Most common level. |
| High | `fedramp-high` | 191 | Life-safety, financial, law enforcement data. Severe/catastrophic effect from loss. |

**Target audience:** Cloud service providers to government

## CMMC 2.0

Cybersecurity Maturity Model Certification for defense contractors. Required by DoD contracts.

| Level | ID | Controls | Use When |
|-------|-----|----------|----------|
| Level 1 | `cmmc-l1` | 17 | Handles only Federal Contract Information (FCI). Basic cyber hygiene. |
| Level 2 | `cmmc-l2` | 110 | Handles CUI. Aligns with NIST 800-171. Most defense contractors need this. |
| Level 3 | `cmmc-l3` | 24 | Highest sensitivity CUI. Advanced practices **on top of** Level 2. |

**Target audience:** Defense industrial base organizations

> **Note:** CMMC Level 3 controls are in addition to Level 2. An organization at Level 3 must also satisfy all Level 2 controls.

## Custom and Forked Frameworks

If your organization needs to track a framework that isn't in the built-in catalog (e.g., an internal control set, a tailored ISO/SOC 2 mapping, an industry-specific regulation), you can author one yourself or fork an existing Pretorin-managed framework. The `pretorin frameworks` group exposes the full revision lifecycle:

- **Author from scratch** — `init-custom`, `validate-custom`, `upload-custom`
- **Convert from OSCAL or 12 known custom catalog shapes** — `build-custom`
- **Fork an existing framework** — `fork-framework`, `rebase-fork`
- **Inspect drafts** — `revisions`
- **Round-trip back to OSCAL** — `export-oscal`

See the [Custom Frameworks](./custom.md) guide for the end-to-end workflow.

See [Framework Selection Guide](./selection.md) for help choosing the right framework.
