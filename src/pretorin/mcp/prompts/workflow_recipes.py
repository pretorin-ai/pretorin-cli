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

### Step 2: Answer pending questions
Call `pretorin_get_pending_policy_questions` to see unanswered questions.

For each question:
1. Call `pretorin_get_policy_question_detail` to get guidance
2. Read the guidance tips and example response
3. Draft your answer based on the organization's context
4. Call `pretorin_answer_policy_question` with your answer

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
}


def get_workflow_recipe(recipe_id: str) -> dict[str, str] | None:
    """Get a workflow recipe by ID."""
    return WORKFLOW_RECIPES.get(recipe_id)


def list_workflow_recipes() -> list[dict[str, str]]:
    """List all available workflow recipes."""
    return [
        {"id": rid, "title": r["title"], "description": r["description"]}
        for rid, r in WORKFLOW_RECIPES.items()
    ]
