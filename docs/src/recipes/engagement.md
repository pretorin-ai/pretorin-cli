# Engagement Layer

The engagement layer is pretorin's **routing boundary**. When the user
says "draft AC-2 for system X" or "answer my scope questionnaire" or
"work through the AC family", the calling agent's first move is
`pretorin_start_task`. Pretorin picks the workflow; the agent then
loads the workflow body and follows it.

This is the third layer in the routing model:

```
engagement      ← pretorin_start_task (deterministic Python rules)
  workflow      ← pretorin_get_workflow(selected) → markdown playbook
    recipe      ← pretorin_list_recipes / pretorin_start_recipe
```

Recipes are the leaf — what to do per item. Workflows are the trunk —
how to iterate items. Engagement is the root — what *kind* of work
we're doing in the first place.

## Why a Routing Layer

Without engagement, the calling agent guesses. Pattern-matching on
nouns sends the agent into evidence/narrative write tools the moment
the user says "AC-2", which produces wrong-framework writes when the
user wasn't explicit and silently-cross-system writes when the active
context shifted. The audit chain breaks.

The engagement layer fixes this with **deterministic rules** that run
in pretorin (no LLM here). The calling agent extracts entities; the
rules pick a workflow; the response carries the platform read-state
the workflow needs. One round-trip, one routing decision, no drift.

## What `pretorin_start_task` Does

Three things:

1. **Validates the entities** the calling agent extracted. Hallucinated
   control ids, unknown frameworks, unresolvable system names — these
   fail loud as MCP errors. The calling agent surfaces the error and
   asks the user to clarify.
2. **Cross-checks coherence**. If the named control exists in some
   framework but not the one the user named, that's an ambiguity. If
   the resolved system doesn't match the active CLI context, that's
   ambiguity too. The response is `ambiguous: true` with a reason —
   the calling agent surfaces it before any writes.
3. **Picks a workflow**. The rule cascade (in priority order):
   - `intent_verb == "inspect_status"` → no workflow, just inspect output.
   - `intent_verb == "campaign"` → campaign.
   - scope question ids OR (intent=answer AND pending scope) → scope-question.
   - policy question ids OR (intent=answer AND pending policy) → policy-question.
   - exactly one control id → single-control.
   - multiple control ids → campaign with control filter.
   - framework set, no controls → campaign over the framework.
   - else → ambiguous; ask the user.

The `rule_matched` field on the response records *which* rule fired so
the audit trail captures the routing decision.

## Entity Shape

The calling agent's LLM extracts:

```python
{
    "intent_verb": "work_on" | "collect_evidence" | "draft_narrative"
                 | "answer" | "campaign" | "inspect_status",
    "raw_prompt": "<user's verbatim prompt>",
    "system_id": "<id or name, or None>",
    "framework_id": "<id, or None>",
    "control_ids": ["ac-2", "ac-3"],
    "scope_question_ids": [],
    "policy_question_ids": [],
}
```

`raw_prompt` is audit-only — pretorin doesn't parse it. Everything
else either resolves cleanly or fails the cross-check.

## Inspect Bundle

When the call succeeds, the response carries a bundled snapshot of the
platform state the workflow will need:

- `workflow_state` (per-system stage rollup)
- `compliance_status` (overall posture)
- `pending_families` (controls that still need work)
- `pending_scope_questions` / `pending_policy_questions`
- `org_policies`

The calling agent doesn't have to issue separate reads for each — one
round-trip yields the routing decision plus the context the workflow
will reference.

Inspect is best-effort: if any one platform call fails, that section
carries an `error` field but the rest of the payload still populates.
Pass `skip_inspect: true` when you already have fresh state.

## Three Response Shapes

1. **MCP error** — entity validation or cross-check hard failure.
   The calling agent shows the error and stops.
2. **`selected_workflow` set, `ambiguous: false`** — routed.
   Calling agent reads the workflow body and follows it.
3. **`ambiguous: true` with `ambiguity_reason`** — coherence problem.
   Calling agent surfaces the reason to the user, gets clarification,
   and retries with disambiguated entities.

There's no fourth shape. The router never produces a confidence score
or alternatives — the rule either matched or didn't.

## Active System Context

Pass `active_system_id` (the user's CLI context system) so the cross-
check catches cross-system writes. When the resolved system doesn't
match, the response is ambiguous regardless of what the rules would
say. This is the small extra friction that eliminates the silent
wrong-system-write class of error.

## Where the Code Lives

- `src/pretorin/engagement/entities.py` — `EngagementEntities` pydantic model.
- `src/pretorin/engagement/selection.py` — `EngagementSelection` response model.
- `src/pretorin/engagement/rules.py` — pure-function rule cascade.
- `src/pretorin/engagement/cross_check.py` — platform-state coherence checks.
- `src/pretorin/engagement/inspect.py` — bundles platform reads into the response.
- `src/pretorin/mcp/handlers/engagement.py` — the `pretorin_start_task` MCP handler.

The rule cascade is testable in pure isolation — same inputs always
produce the same output. Drift impossible by construction.
