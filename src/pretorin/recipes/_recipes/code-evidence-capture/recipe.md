---
id: code-evidence-capture
version: 0.1.0
name: "Code Evidence Capture"
description: "Capture a redacted source-code excerpt as compliance evidence with a verifiable provenance footer (file path, line range, commit hash, redaction summary)."
use_when: "The auditor needs to see a specific code or config block as evidence. You have a file path (and optionally a line range and commit hash). You want secret-shaped values redacted before the snippet ships to the platform."
produces: evidence
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: AC-2, framework: nist-800-53-r5 }
  - { control: AU-2, framework: nist-800-53-r5 }
params:
  source_path:
    type: string
    description: "Repository-relative path to the source file the snippet comes from"
    required: true
  line_range:
    type: string
    description: "Optional line range in 'N-M' form (e.g., '42-67') for the footer"
  commit_hash:
    type: string
    description: "Optional git commit hash; truncated to 7 chars in the footer"
scripts:
  redact_secrets:
    path: scripts/redact_secrets.py
    description: "Run pretorin's secret redactor over the supplied text and return the redacted body plus per-kind counts."
    params:
      text:
        type: string
        description: "Raw text to scan and redact (typically a file's contents or an excerpt)"
        required: true
  compose_snippet:
    path: scripts/compose_snippet.py
    description: "Compose the auditor-facing markdown body: prose preamble + fenced snippet + horizontal rule + italic provenance footer."
    params:
      snippet:
        type: string
        description: "The snippet to embed (already redacted by the redact_secrets tool)"
        required: true
      language:
        type: string
        description: "Fence language tag (python, yaml, json, etc.). Empty string is fine."
      source_path:
        type: string
        description: "Path or URL the snippet came from; required for the provenance footer to render"
        required: true
      line_range:
        type: string
        description: "Optional line range in 'N-M' form"
      commit_hash:
        type: string
        description: "Optional git commit hash"
      is_uncommitted:
        type: boolean
        description: "True when the snippet reflects working-tree state ahead of the commit"
        default: false
      user_prose:
        type: string
        description: "Optional preamble paragraph rendered above the code fence"
      secrets_redacted:
        type: integer
        description: "Count of secrets the redactor removed (from the redact_secrets tool's secrets_count field). Drives the footer's redaction summary."
        default: 0
---

# Code Evidence Capture

This recipe produces one piece of compliance evidence from a code or config
snippet. The auditor sees a fenced code block plus a one-line italic footer
documenting where the snippet came from, when it was captured, and whether
any secrets were redacted before submission.

## Procedure

1. **Read the source file** the auditor needs to see. Use whichever file-read
   capability your agent has (Claude Code's `Read` tool, your shell's `cat`,
   etc.) to obtain the raw text. If the auditor only needs a specific region,
   slice it down to the relevant lines yourself before calling the redactor —
   smaller snippets are more readable.

2. **Redact secrets** by calling `pretorin_recipe_code_evidence_capture__redact_secrets(text=<raw>)`.
   The redactor catches API keys (AWS, GitHub, Slack, Stripe, Google, JWTs),
   PEM private keys, credential-bearing URLs, and password-shaped assignments
   (`password = "…"`, `api_key: "…"`). Each match is replaced with
   `[REDACTED:<kind>]`. The tool returns `{redacted_text, secrets_count,
   details}`.

3. **Compose the markdown body** by calling
   `pretorin_recipe_code_evidence_capture__compose_snippet(...)`. Pass the
   redacted text from step 2, the language tag (`python`, `yaml`, `json`,
   …), the source path, optional line range and commit hash, and the
   `secrets_redacted` count from step 2. The tool returns `{body}`.

4. **Push the evidence** by calling `pretorin_create_evidence(name=...,
   description=<body>, evidence_type="code_snippet",
   control_id=<the control>, code_file_path=<source_path>,
   recipe_context_id=<the active context>)`. Audit metadata stamping is
   automatic when the active context is supplied — the platform will record
   `producer_kind="recipe"` with this recipe's id and version.

## Output

One evidence record on the platform with:

- A description that contains the redacted snippet plus the italic footer.
- `producer_kind="recipe"`, `producer_id="code-evidence-capture"`,
  `producer_version="0.1.0"` stamped in the audit metadata.
- A `redaction_summary` carrying the secret counts.
- Source provenance fields populated from the supplied path / lines / commit.
