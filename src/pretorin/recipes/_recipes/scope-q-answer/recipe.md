---
id: scope-q-answer
version: 0.1.0
name: "Scope Question Answer"
description: "Redact secrets in a candidate scope-question answer and return the cleaned text plus a redaction summary. Used by the scope-question workflow to ensure answers don't leak credentials, internal hostnames, or tokens before the answer goes through audit."
use_when: "Answering a scope question through the scope-question workflow and the candidate text may contain secrets (URLs with credentials, AWS keys, JWTs, etc.). Default for that workflow's per-question step."
produces: answers
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: CA-3, framework: nist-800-53-r5 }
scripts:
  redact_answer:
    path: scripts/redact_answer.py
    description: "Run the candidate answer through pretorin.evidence.redact and return cleaned text + counts."
    params:
      answer_text:
        type: string
        description: "The candidate answer text to redact before submission."
        required: true
---

# Scope Question Answer

Light recipe used inside the `scope-question` workflow. The agent has a
candidate answer for one scope question; this recipe redacts secrets
(API keys, JWTs, credential URLs, password assignments) before the
answer is submitted via `pretorin_answer_scope_question`.

The redact step is mandatory because scope answers commonly include
deployment topology details, identity-provider configs, and references
to internal tooling that have leaked secrets through copy-paste in the
past.

## How the agent uses this

1. Open the recipe context with the question id in `params`.
2. Call `redact_answer(answer_text=<candidate>)`. Returns
   `{ "redacted": "...", "redaction_summary": {...} }`.
3. Submit the redacted answer via `pretorin_answer_scope_question`,
   passing `recipe_context_id` so the audit metadata stamps.
4. Close the context with `pretorin_end_recipe`.
