# Vendor Management

The `vendor` command group manages vendor entities and their evidence documents. Vendors represent external providers (CSPs, SaaS, managed services) or internal teams whose controls your system inherits.

## List Vendors

```bash
pretorin vendor list
```

## Create a Vendor

```bash
pretorin vendor create "AWS" --type csp --description "Primary cloud provider" \
  --authorization-level "FedRAMP High P-ATO"
```

### Vendor Types

| Type | Description |
|------|-------------|
| `csp` | Cloud Service Provider |
| `saas` | Software as a Service |
| `managed_service` | Managed service provider |
| `internal` | Internal team or shared service |

## Get Vendor Details

```bash
pretorin vendor get <vendor_id>
```

## Update a Vendor

```bash
pretorin vendor update <vendor_id> --name "AWS GovCloud" --authorization-level "FedRAMP High"
```

## Delete a Vendor

```bash
pretorin vendor delete <vendor_id>
pretorin vendor delete <vendor_id> --force  # skip confirmation
```

## Upload Vendor Documents

Upload SOC 2 reports, Customer Responsibility Matrices (CRMs), FedRAMP packages, or other vendor evidence:

```bash
pretorin vendor upload-doc <vendor_id> ./aws-soc2-report.pdf \
  --name "AWS SOC 2 Type II" \
  --description "Annual SOC 2 report covering 2025" \
  --attestation-type third_party_attestation
```

### Attestation Types

| Type | Description |
|------|-------------|
| `self_attested` | Vendor's own assertion |
| `third_party_attestation` | Independent auditor report (SOC 2, FedRAMP) |
| `vendor_provided` | Documentation provided by vendor |

## List Vendor Documents

```bash
pretorin vendor list-docs <vendor_id>
```

## Related: Control Inheritance

Once vendors are created and documents uploaded, use the MCP tools or platform to set control responsibility edges:

- `pretorin_set_control_responsibility` — Mark controls as inherited/shared
- `pretorin_generate_inheritance_narrative` — AI-draft inheritance narratives from vendor docs
- `pretorin_get_stale_edges` / `pretorin_sync_stale_edges` — Monitor and sync inheritance
