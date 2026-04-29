---
id: cloud-aws-baseline
version: 0.1.0
name: "AWS Cloud Baseline Scan"
description: "Run AWS-cloud STIG checks (IAM, CloudTrail, S3 encryption, etc.) against the configured account/region and produce one summary evidence record per scan run."
use_when: "The auditor needs evidence that AWS-cloud-baseline STIG controls have been evaluated. You have AWS credentials configured (aws CLI configured profile, env vars, or instance role) and a STIG id targeting AWS controls."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CM-6, framework: nist-800-53-r5 }
requires:
  cli:
    - { name: aws, probe: "aws --version" }
  env:
    - AWS_REGION
params:
  stig_id:
    type: string
    description: "STIG benchmark id targeting AWS-cloud controls"
    required: true
  region:
    type: string
    description: "Optional AWS region (defaults to AWS_REGION env or aws-cli default)"
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Pull the manifest, run AWS-cloud checks, return per-run summary + rule-level details."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id targeting AWS-cloud controls"
        required: true
      region:
        type: string
        description: "Optional AWS region (defaults to AWS_REGION env / aws-cli default)"
---

# AWS Cloud Baseline Scan

Wraps `pretorin.scanners.cloud_aws` against an authenticated AWS context. Pattern identical to `inspec-baseline`.
