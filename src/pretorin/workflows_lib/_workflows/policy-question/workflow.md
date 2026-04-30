---
id: policy-question
version: 0.1.0
name: "Policy Questionnaire"
description: "Walk a system's policy questionnaires and answer items the agent has enough context for. Pick this when the user mentions org policy work, a specific policy questionnaire, or when policy is the workflow-state blocker before control work can proceed."
use_when: "The user references an org policy questionnaire (information security policy, access control policy, incident response policy, etc.), a specific policy question, or pretorin's workflow-state surface flags policy as the active blocker. Not for scope or control work."
produces: answers
iterates_over: policy_questions
recipes_commonly_used:
  - policy-q-answer
---

# Policy Questionnaire

Iterate over pending policy questions for an org policy and answer them
one at a time using the `policy-q-answer` recipe. Same shape as
`scope-question` but scoped to a specific policy questionnaire (info-sec,
access-control, incident-response, etc.).

## Iteration shape

One question at a time, scoped to one policy. If the user is working
through multiple policies, run this workflow once per policy.

## Step-by-step

1. **Identify which policy.** If the user named the policy explicitly,
   use that id. Otherwise:

   ```
   pretorin_list_org_policies()
   ```

   and ask the user to pick one. Don't guess.

2. **Load the pending question set for that policy.**

   ```
   pretorin_get_pending_policy_questions(org_policy_id)
   ```

3. **For each question, in order:**

   a. **Read detail** for guidance:
      ```
      pretorin_get_policy_question_detail(org_policy_id, policy_question_id)
      ```

   b. **Pick the recipe.** `policy-q-answer` is the default. A
      specialized community recipe may exist for specific policy
      domains (e.g., a HIPAA-specific recipe for access-control
      policy questions); prefer it when its `use_when` matches.

   c. **Run the recipe.**
      ```
      pretorin_start_recipe("policy-q-answer", "<version>", params)
      pretorin_recipe_policy_q_answer__redact_answer(answer_text)
      pretorin_answer_policy_question(org_policy_id, policy_question_id,
                                      answer=<redacted>,
                                      recipe_context_id=context_id)
      pretorin_end_recipe(context_id, "pass")
      ```

   d. **Stop and ask** if the question references something the agent
      can't observe (e.g., "what is the policy review cadence?" with
      no documented cadence in the workspace). Don't fabricate.

4. **Optionally trigger review** when the user wants a coherence check
   across the answered set:

   ```
   pretorin_trigger_policy_review(org_policy_id)
   ```

   then poll `pretorin_get_policy_review_results`.

## What to avoid

- Don't generate the policy document
  (`pretorin_trigger_policy_generation`) until answers are complete and
  the user asks. The workflow ends with answers populated; document
  generation is the next step.
- Don't conflate scope and policy questions. They're separate
  questionnaires with separate answer endpoints; mixing them produces
  garbage in both.
- Don't skip the redact step on policy answers. Policies routinely
  reference contractual details, vendor names, or internal tooling
  that need redaction before audit.
