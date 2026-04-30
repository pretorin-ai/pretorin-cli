---
id: scope-question
version: 0.1.0
name: "Scope Questionnaire"
description: "Walk a system's scope questionnaire and answer items the agent has enough context for. Pick this when the user mentions the scope questionnaire, when scope is the workflow-state blocker, or when there are pending scope questions to clear before any control work can start."
use_when: "The user references the scope questionnaire, a specific scope question, or pretorin's workflow-state surface flags scope as the active blocker. Not for policy questionnaires (use `policy-question`) or control-level work."
produces: answers
iterates_over: scope_questions
recipes_commonly_used:
  - scope-q-answer
---

# Scope Questionnaire

Iterate over pending scope questions for a system and answer them, one at a
time, using the `scope-q-answer` recipe. The recipe handles secret redaction
and audit-metadata stamping; the workflow handles iteration order and
batch boundaries.

## Iteration shape

One question at a time. Don't bulk-answer — each question's answer is its
own audit record and the user often wants to review individual answers
before moving on.

## Step-by-step

1. **Load the pending set.**

   ```
   pretorin_get_pending_scope_questions(system_id)
   ```

   Returns only the unanswered questions. Already-answered questions
   stay alone unless the user explicitly asks to revisit one.

2. **Optionally filter.** If the user named a specific scope question id
   or category, narrow the set before iterating. Don't guess subsets;
   ask if the user's intent is unclear.

3. **For each question, in the order returned:**

   a. **Read the question detail** for any tips/examples the platform
      surfaces:
      ```
      pretorin_get_scope_question_detail(system_id, scope_question_id)
      ```

   b. **Pick the recipe.** `scope-q-answer` is the default. If a more
      specialized community recipe matches the question's category
      (e.g., "data-classification-scope-q-answer"), prefer that.

   c. **Run the recipe.**
      ```
      pretorin_start_recipe("scope-q-answer", "<version>", params)
      pretorin_recipe_scope_q_answer__redact_answer(answer_text)
      pretorin_answer_scope_question(system_id, scope_question_id,
                                     answer=<redacted>,
                                     recipe_context_id=context_id)
      pretorin_end_recipe(context_id, "pass")
      ```

   d. **Show the user the answered question** before moving on if the
      user asked for review-as-you-go. Otherwise, continue.

4. **At the end of a batch**, optionally trigger AI review of the
   answered set if the user wants a coherence check:

   ```
   pretorin_trigger_scope_review(system_id)
   ```

   Then poll `pretorin_get_scope_review_results` until ready.

## What to avoid

- Don't answer a question with platform-record information alone. The
  point of the questionnaire is to capture system-specific context the
  platform doesn't already know.
- Don't skip the redact step. Scope answers routinely include details
  about deployment topology, identity providers, or third-party
  integrations that may carry secrets.
- Don't trigger scope-document generation
  (`pretorin_trigger_scope_generation`) until the user asks. The
  workflow's job is to populate answers; document generation is a
  separate user-driven step.
