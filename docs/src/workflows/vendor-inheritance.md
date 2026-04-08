# Vendor Inheritance

Many compliance controls are partially or fully satisfied by external providers (cloud platforms, SaaS tools, managed services). Pretorin tracks these inheritance relationships and keeps inherited narratives in sync with vendor documentation.

## Concepts

- **Vendor** — An external provider or internal shared service (CSP, SaaS, managed service, internal)
- **Responsibility edge** — A link between a control and a vendor indicating the control is inherited or shared
- **Stale edge** — A responsibility edge where the source narrative has changed but the inherited control hasn't been updated

## Workflow

### 1. Create Vendor Entities

```bash
pretorin vendor create "AWS GovCloud" --type csp \
  --description "Primary cloud infrastructure" \
  --authorization-level "FedRAMP High P-ATO"

pretorin vendor create "Okta" --type saas \
  --description "Identity and access management"
```

### 2. Upload Vendor Documentation

```bash
pretorin vendor upload-doc <vendor_id> ./aws-crm.pdf \
  --name "AWS Customer Responsibility Matrix" \
  --attestation-type vendor_provided

pretorin vendor upload-doc <vendor_id> ./okta-soc2.pdf \
  --name "Okta SOC 2 Type II Report" \
  --attestation-type third_party_attestation
```

### 3. Set Control Responsibility

Via MCP tools:

```
pretorin_set_control_responsibility(system_id, control_id, framework_id, vendor_id, responsibility_type)
```

Responsibility types:
- **inherited** — Fully satisfied by the vendor
- **shared** — Partially satisfied; your system handles the remainder

### 4. Generate Inheritance Narratives

```
pretorin_generate_inheritance_narrative(system_id, control_id, framework_id, vendor_id)
```

AI generates a narrative grounded in the vendor's uploaded documentation, explaining how the vendor satisfies the control requirements.

### 5. Monitor Staleness

Over time, vendor documentation or source narratives may be updated. Check for stale inheritance:

```
pretorin_get_stale_edges(system_id, framework_id)
```

Returns controls where the source has changed but the inherited narrative hasn't been refreshed.

### 6. Sync Stale Edges

```
pretorin_sync_stale_edges(system_id, framework_id)
```

Bulk updates inherited controls by regenerating narratives from the latest source.

## Linking Evidence to Vendors

```
pretorin_link_evidence_to_vendor(evidence_id, vendor_id, attestation_type)
```

Attestation types: `self_attested`, `third_party_attestation`, `vendor_provided`
