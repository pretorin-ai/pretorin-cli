"""Workflow recipe prompts for agent-guided compliance workflows.

These recipes guide AI agents through the correct sequence of API calls
for common compliance tasks. They're served as MCP resources so agents
can load the recipe and follow it step by step.
"""

from __future__ import annotations

WORKFLOW_RECIPES: dict[str, dict[str, str]] = {
    "complete-one-policy": {
        "title": "Complete One Policy (Answer → Generate → Review → Fix)",
        "description": (
            "Walk through the full lifecycle for a single organization policy. "
            "This recipe handles question answering, document generation, AI review, "
            "and iterative fix cycles."
        ),
        "content": """# Recipe: Complete One Policy

## Prerequisites
- You need a `policy_id` (get it from `pretorin_list_org_policies`)
- The policy should be a template-based policy (not custom)

## Steps

### Step 1: Check current state
Call `pretorin_get_policy_workflow_state` with the policy_id.
Look at `next_action` to see what needs doing.

### Step 2: Research the workspace FIRST
Before answering any questions, research the local codebase and documentation:
- Read existing policy documents (privacy policy pages, terms of service, etc.)
- Read infrastructure config (Helm charts, Terraform, Dockerfiles, CI/CD workflows)
- Read security documentation (docs/security/, docs/pentest/, etc.)
- Read auth/signup flows for consent mechanisms and user data collection
- Read API models for what PII is stored and how data flows
- Note what actually exists vs what is aspirational

### Step 3: Answer pending questions
Call `pretorin_get_pending_policy_questions` to see unanswered questions.

For each question:
1. Call `pretorin_get_policy_question_detail` to get guidance
2. Read the guidance tips and example response
3. Draft your answer grounded in observable workspace facts from Step 2
4. Do NOT invent organizational facts, role titles, URLs, or procedures
5. If something cannot be confirmed from workspace evidence, state what you know and flag what needs manual input
6. Call `pretorin_answer_policy_question` with your answer

### Step 3: Generate the policy document
Once all questions are answered:
Call `pretorin_trigger_policy_generation` (optionally with system_id for scope context)

Poll `pretorin_get_policy_review_results` every 2-3 seconds until status is "succeeded".

### Step 4: Review the policy
Call `pretorin_trigger_policy_review`

Poll `pretorin_get_policy_review_results` until status is "succeeded".

### Step 5: Fix review findings
Look at the findings in the review results. For each finding:
1. Note the `target_ref` (question_id) and `recommended_fix`
2. Call `pretorin_get_policy_question_detail` with that question_id
3. Update the answer: `pretorin_answer_policy_question`

### Step 6: Re-review (optional)
If you fixed findings, trigger another review to verify.
Repeat steps 4-5 until the review comes back clean.

### Step 7: Verify completion
Call `pretorin_get_policy_analytics` to confirm:
- `completion_pct` should be 100
- `document_generated` should be true
- `last_review.status` should be "passed"
""",
    },
    "fix-control-family": {
        "title": "Fix All Issues in a Control Family",
        "description": (
            "Review all controls in a family (e.g., Access Control), get AI findings, "
            "and fix each issue. Good for focused compliance sprints."
        ),
        "content": """# Recipe: Fix All Issues in a Control Family

## Prerequisites
- You need a `system_id` and `framework_id`
- Pick a family to work on (e.g., "AC" for Access Control)

## Steps

### Step 1: Choose a family
Call `pretorin_get_pending_families` to see which families need work.
Pick the one with the most pending controls, or the one specified by the user.

### Step 2: Understand the family state
Call `pretorin_get_family_bundle` with the family_id.
Review each control's status:
- `has_narrative`: does it have implementation text?
- `has_evidence`: is evidence linked?
- `notes_count`: are there open notes to address?

### Step 3: Trigger family review
Call `pretorin_trigger_family_review` with system_id, family_id, framework_id.

Poll `pretorin_get_family_review_results` every 3 seconds.
NOTE: Large families (20+ controls) may take 2-4 minutes.

### Step 4: Address findings
For each finding in the review results:
1. Note the `target_ref` (control_id) and `severity`
2. Read the `issue` and `recommended_fix`
3. Use `pretorin_get_control_context` for full control details
4. Update the narrative: `pretorin_update_narrative`
5. Add evidence if needed: `pretorin_create_evidence` + `pretorin_link_evidence`
6. Add a note documenting what you did: `pretorin_add_control_note`

### Step 5: Re-review
Trigger another family review to verify fixes.
Repeat until findings are resolved.

### Step 6: Check analytics
Call `pretorin_get_family_analytics` to see the updated family stats.
""",
    },
    "full-compliance-pass": {
        "title": "Full System Compliance Pass",
        "description": (
            "Run through the entire compliance lifecycle: scope, policies, controls, "
            "and evidence. Use for initial system setup or periodic compliance sprints."
        ),
        "content": """# Recipe: Full System Compliance Pass

## Prerequisites
- You need a `system_id` and `framework_id`
- The system should have a framework configured

## Steps

### Step 1: Get the big picture
Call `pretorin_get_workflow_state` to see where you are.
Call `pretorin_get_analytics_summary` for detailed progress.
The `lifecycle_stage` tells you what to work on first.

### Step 2: Complete scope (if not done)
If scope status is not "complete":
1. `pretorin_get_pending_scope_questions` — see what needs answering
2. For each question: get detail, answer it
3. `pretorin_trigger_scope_generation` — generate scope document
4. `pretorin_trigger_scope_review` — review answers
5. Fix any findings and re-review

### Step 3: Complete policies (if not done)
If policies status is not "complete":
1. `pretorin_list_org_policies` — get all policies
2. For each incomplete policy, follow the "Complete One Policy" recipe
3. Prioritize policies the workflow state flags as `needs_attention`

### Step 4: Work through control families
If controls status is not "complete":
1. `pretorin_get_pending_families` — see which families need work
2. `pretorin_get_family_analytics` — prioritize by coverage gaps
3. For each family, follow the "Fix Control Family" recipe
4. Focus on writing narratives for controls without them
5. Link evidence to controls that need it

### Step 5: Fill evidence gaps
If evidence shows controls_missing_evidence > 0:
1. Use `pretorin_get_analytics_summary` to see gap count
2. Use `pretorin_get_family_analytics` to find which families have gaps
3. Create evidence: `pretorin_create_evidence`
4. Link to controls: `pretorin_link_evidence`

### Step 6: Final review
1. `pretorin_get_workflow_state` — verify all stages complete
2. `pretorin_get_analytics_summary` — final numbers
3. Report the results to the user
""",
    },
    "external-campaign-controls": {
        "title": "External Agent Campaign for Controls",
        "description": (
            "Prepare a controls campaign, claim work items, draft proposals with your own agent, "
            "submit them, and apply them through Pretorin."
        ),
        "content": """# Recipe: External Controls Campaign

## Goal
Use your current agent session and token budget to execute a Pretorin controls
campaign without using Pretorin's builtin agent.

## Steps

### Step 1: Prepare the campaign
Call `pretorin_prepare_campaign` with:
- `domain="controls"`
- the desired `mode`
- scope selectors like `system_id`, `framework_id`, `family_id`

The response returns a `checkpoint_path`.

### Step 2: Claim a batch
Call `pretorin_claim_campaign_items` with:
- `checkpoint_path`
- `max_items`
- `lease_owner`

### Step 3: Draft each item
For each claimed item:
1. Call `pretorin_get_campaign_item_context`
2. Read the instructions and platform context
3. Draft a JSON proposal in the required controls shape
4. Call `pretorin_submit_campaign_proposal`

### Step 4: Monitor progress
Call `pretorin_get_campaign_status` any time to get:
- counts
- recent events
- failures
- a stable text snapshot for transcript output

### Step 5: Apply
When proposals look ready:
Call `pretorin_apply_campaign` with the same `checkpoint_path`.

### Step 6: Verify
Call `pretorin_get_campaign_status` again and confirm the remaining pending/failed counts.
""",
    },
    "external-campaign-questionnaires": {
        "title": "External Agent Campaign for Policy or Scope",
        "description": (
            "Use Pretorin campaign orchestration with your own Codex, Claude, or MCP-capable agent "
            "to draft questionnaire proposals and apply them safely."
        ),
        "content": """# Recipe: External Questionnaire Campaign

## Goal
Use Pretorin to prepare and apply questionnaire work while your current agent session does the drafting.

## Steps

### Step 1: Prepare
Call `pretorin_prepare_campaign` with:
- `domain="policy"` or `domain="scope"`
- the desired `mode`
- selectors such as `policy_ids` or `system_id` + `framework_id`

### Step 2: Claim
Call `pretorin_claim_campaign_items` with a `lease_owner`.

### Step 3: Draft from item context
For each claimed item:
1. Call `pretorin_get_campaign_item_context`
2. Follow the instructions in the response
3. Return JSON in the questionnaire proposal shape
4. Persist it with `pretorin_submit_campaign_proposal`

### Step 4: Apply
Call `pretorin_apply_campaign` once proposals are ready.

### Step 5: Report
Use `pretorin_get_campaign_status` to summarize progress and any remaining failures.
""",
    },
}


def get_workflow_recipe(recipe_id: str) -> dict[str, str] | None:
    """Get a workflow recipe by ID."""
    return WORKFLOW_RECIPES.get(recipe_id)


def list_workflow_recipes() -> list[dict[str, str]]:
    """List all available workflow recipes."""
    return [{"id": rid, "title": r["title"], "description": r["description"]} for rid, r in WORKFLOW_RECIPES.items()]
