---
id: policy-q-answer
version: 0.1.0
name: "Policy Question Answer"
description: "Redact secrets in a candidate policy-question answer and return the cleaned text plus a redaction summary. Used by the policy-question workflow to ensure answers about internal policies, vendor relationships, or compliance procedures don't leak credentials before the answer is recorded."
use_when: "Answering an org-policy question through the policy-question workflow and the candidate text may carry secrets or internal references that need redaction. Default for that workflow's per-question step."
produces: answers
author: "Pretorin Core Team"
license: Apache-2.0
attests:
  - { control: PM-1, framework: nist-800-53-r5 }
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

# Policy Question Answer

Light recipe used inside the `policy-question` workflow. The agent has a
candidate answer for one org-policy question; this recipe redacts secrets
before the answer is submitted via `pretorin_answer_policy_question`.

Same mechanism as `scope-q-answer` but scoped to policy-questionnaire work.
The two recipes are kept separate so the audit trail records which
questionnaire surface the answer came from — `producer_id` carries that
disambiguation.

## How the agent uses this

1. Open the recipe context with the policy + question ids in `params`.
2. Call `redact_answer(answer_text=<candidate>)`.
3. Submit via `pretorin_answer_policy_question` with `recipe_context_id`.
4. Close the context.
