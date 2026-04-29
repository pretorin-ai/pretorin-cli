---
id: manual-attestation
version: 0.1.0
name: "Manual Attestation Scan"
description: "Capture human attestations against a STIG's manual-review rules and produce one summary evidence record. Use when no automated scanner covers the rules and the auditor needs explicit human sign-off."
use_when: "The auditor needs evidence that a STIG's manual rules have been reviewed and answered. You have a STIG id whose rules are manual-review (no automated scanner applicable). The agent prompts the user for pass/fail per rule."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CA-2, framework: nist-800-53-r5 }
params:
  stig_id:
    type: string
    description: "STIG benchmark id whose manual rules will be attested"
    required: true
  attestations:
    type: array
    items: { type: object }
    description: "List of {rule_id, status, note} attestations the calling agent has gathered. Status is one of pass / fail / not_applicable / not_reviewed."
    default: []
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Apply the supplied per-rule attestations against the manifest, return per-run summary + rule-level details."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id whose manual rules will be attested"
        required: true
      attestations:
        type: array
        items: { type: object }
        description: "List of {rule_id, status, note} attestations the calling agent has gathered"
---

# Manual Attestation Scan

Pattern: same shape as the other scanner recipes, but the "scan" is the
agent collecting human attestations rather than running an external tool.
The `attestations` param is a list of `{rule_id, status, note}` entries the
calling agent has gathered (typically by interview).
