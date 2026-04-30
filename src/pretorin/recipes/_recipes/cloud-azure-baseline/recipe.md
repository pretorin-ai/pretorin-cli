---
id: cloud-azure-baseline
version: 0.1.0
name: "Azure Cloud Baseline Scan"
description: "Run Azure-cloud STIG checks against the configured tenant/subscription and produce one summary evidence record per scan run."
use_when: "The auditor needs evidence that Azure-cloud-baseline STIG controls have been evaluated. You have Azure credentials (az CLI logged in or service-principal env vars) and a STIG id targeting Azure controls."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CM-6, framework: nist-800-53-r5 }
requires:
  cli:
    - { name: az, probe: "az --version" }
params:
  stig_id:
    type: string
    description: "STIG benchmark id targeting Azure-cloud controls"
    required: true
  subscription:
    type: string
    description: "Optional subscription id (defaults to az CLI default)"
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Pull the manifest, run Azure-cloud checks, return per-run summary + rule-level details."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id targeting Azure-cloud controls"
        required: true
      subscription:
        type: string
        description: "Optional subscription id (defaults to az CLI default)"
---

# Azure Cloud Baseline Scan

Wraps `pretorin.scanners.cloud_azure` against an authenticated Azure context. Pattern identical to `inspec-baseline`.
