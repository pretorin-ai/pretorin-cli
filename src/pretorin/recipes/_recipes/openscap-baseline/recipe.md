---
id: openscap-baseline
version: 0.1.0
name: "OpenSCAP STIG Baseline Scan"
description: "Run an OpenSCAP STIG datastream against the local host and produce one summary evidence record per scan run, with per-rule pass/fail data carried in the body."
use_when: "The auditor needs OpenSCAP-driven STIG evaluation evidence on a Linux host. You have a STIG id and OpenSCAP installed (oscap binary)."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CM-6, framework: nist-800-53-r5 }
requires:
  cli:
    - { name: oscap, probe: "oscap --version" }
params:
  stig_id:
    type: string
    description: "STIG benchmark id to evaluate"
    required: true
  datastream:
    type: string
    description: "Optional path to the SCAP datastream file (auto-detected from /usr/share/xml/scap/ssg if omitted)"
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Pull the test manifest, run OpenSCAP against the local host, and return per-run summary + rule-level details."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id"
        required: true
      datastream:
        type: string
        description: "Optional datastream path"
---

# OpenSCAP STIG Baseline Scan

Same shape as `inspec-baseline`: one summary evidence record per scan run, OpenSCAP-driven.

## Procedure

1. `pretorin_recipe_openscap_baseline__run_scan(stig_id=...)` returns `{summary, rules, ...}`.
2. Compose the evidence description from the summary.
3. Push via `pretorin_create_evidence` with `recipe_context_id`.
