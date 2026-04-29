---
id: inspec-baseline
version: 0.1.0
name: "InSpec STIG Baseline Scan"
description: "Run a Chef InSpec STIG profile against a target system and produce one summary evidence record per scan run, with per-rule pass/fail data carried in the body."
use_when: "The auditor needs evidence that a STIG-aligned configuration baseline (RHEL 9 STIG, Ubuntu STIG, etc.) has been evaluated. You have a STIG id and a target the InSpec scanner can reach (local host, SSH, etc.)."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CM-6, framework: nist-800-53-r5 }
requires:
  cli:
    - { name: inspec, probe: "inspec --version" }
params:
  stig_id:
    type: string
    description: "STIG benchmark id to evaluate (e.g., RHEL_9_STIG)"
    required: true
  target:
    type: string
    description: "InSpec target string ('local' or 'ssh://user@host'). Defaults to 'local'."
    default: "local"
scripts:
  run_scan:
    path: scripts/run_scan.py
    description: "Pull the test manifest for the requested STIG, run the InSpec scanner against the target, and return a per-run summary with rule-level pass/fail details."
    params:
      stig_id:
        type: string
        description: "STIG benchmark id (matches the recipe-level param)"
        required: true
      target:
        type: string
        description: "InSpec target string"
        default: "local"
---

# InSpec STIG Baseline Scan

This recipe runs one Chef InSpec STIG profile against a target system and
produces a single summary evidence record covering the whole scan run.

## Procedure

1. Call `pretorin_recipe_inspec_baseline__run_scan(stig_id="<id>", target="<target>")`.
   The script pulls the test manifest from the platform, filters to the
   requested STIG's rules, runs `pretorin.scanners.inspec` against the
   target, and returns `{summary: {total, passed, failed, ...}, rules:
   [...]}`.

2. Compose the evidence description from the summary. Auditors care about the
   pass/fail counts, the STIG id, and the target. Per-rule detail belongs in
   the body for the worst offenders (failed/errored rules); skip the long
   tail of NOT_APPLICABLEs.

3. Push via `pretorin_create_evidence(name="<STIG> scan", evidence_type=
   "scan_result", control_id=<the control>, description=<your composed body>,
   recipe_context_id=<active context>)`. Audit metadata stamps automatically.

## Output

One evidence record with `producer_kind="recipe"`, `producer_id="inspec-baseline"`,
`source_type="scan_result"`. The `redaction_summary` field stays null
(scanner output isn't redacted in v1).
