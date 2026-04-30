"""Deterministic workflow-selection rules.

Pure function over (entities, inspect_summary). No agent reasoning, no
LLM, no I/O — same inputs always produce the same output. The rule that
fires is recorded on ``EngagementSelection.rule_matched`` so the audit
trail captures *why* the router picked what it picked.

Per the design WS0 §2c, the rule cascade in priority order:

1. ``intent_verb == "inspect_status"`` → no workflow, just inspect.
2. ``intent_verb == "campaign"`` → campaign.
3. scope question ids OR (intent=answer AND pending scope) → scope-question.
4. policy question ids OR (intent=answer AND pending policy) → policy-question.
5. exactly one control id → single-control.
6. multiple control ids → campaign with control filter.
7. zero control ids + framework set → campaign over the framework.
8. else → ambiguous; ask the user.
"""

from __future__ import annotations

from typing import Any

from pretorin.engagement.entities import EngagementEntities
from pretorin.engagement.selection import EngagementSelection, SelectedWorkflow


def _has_pending_scope(inspect_summary: dict[str, Any]) -> bool:
    pending = inspect_summary.get("pending_scope_questions") or []
    return bool(pending)


def _has_pending_policy(inspect_summary: dict[str, Any]) -> bool:
    pending = inspect_summary.get("pending_policy_questions") or []
    return bool(pending)


def select_workflow(
    entities: EngagementEntities,
    inspect_summary: dict[str, Any],
) -> EngagementSelection:
    """Apply the rule cascade and return an ``EngagementSelection``.

    This is the single source of truth for routing. Tests target this
    function with synthetic entities + inspect dicts; no MCP, no client.
    """
    # Rule 1: inspect-only — no workflow runs.
    if entities.intent_verb == "inspect_status":
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow=None,
            rule_matched='intent_verb == "inspect_status"',
            ambiguous=False,
        )

    # Rule 2: campaign verb — bulk work.
    if entities.intent_verb == "campaign":
        params: dict[str, Any] = {}
        if entities.control_ids:
            params["control_filter"] = list(entities.control_ids)
        if entities.framework_id:
            params["framework_id"] = entities.framework_id
        if entities.system_id:
            params["system_id"] = entities.system_id
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="campaign",
            workflow_params=params,
            rule_matched='intent_verb == "campaign"',
        )

    # Rule 3: scope questionnaire.
    if entities.scope_question_ids or (entities.intent_verb == "answer" and _has_pending_scope(inspect_summary)):
        params = {}
        if entities.system_id:
            params["system_id"] = entities.system_id
        if entities.scope_question_ids:
            params["scope_question_ids"] = list(entities.scope_question_ids)
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="scope-question",
            workflow_params=params,
            rule_matched=(
                "scope_question_ids set"
                if entities.scope_question_ids
                else 'intent_verb == "answer" and pending scope questions'
            ),
        )

    # Rule 4: policy questionnaire.
    if entities.policy_question_ids or (entities.intent_verb == "answer" and _has_pending_policy(inspect_summary)):
        params = {}
        if entities.system_id:
            params["system_id"] = entities.system_id
        if entities.policy_question_ids:
            params["policy_question_ids"] = list(entities.policy_question_ids)
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="policy-question",
            workflow_params=params,
            rule_matched=(
                "policy_question_ids set"
                if entities.policy_question_ids
                else 'intent_verb == "answer" and pending policy questions'
            ),
        )

    # Rule 5: exactly one control id → single-control.
    if len(entities.control_ids) == 1:
        params = {
            "control_id": entities.control_ids[0],
        }
        if entities.system_id:
            params["system_id"] = entities.system_id
        if entities.framework_id:
            params["framework_id"] = entities.framework_id
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="single-control",
            workflow_params=params,
            rule_matched="len(control_ids) == 1",
        )

    # Rule 6: many control ids → campaign with control filter.
    if len(entities.control_ids) > 1:
        params = {
            "control_filter": list(entities.control_ids),
        }
        if entities.system_id:
            params["system_id"] = entities.system_id
        if entities.framework_id:
            params["framework_id"] = entities.framework_id
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="campaign",
            workflow_params=params,
            rule_matched="len(control_ids) > 1",
        )

    # Rule 7: framework named, no controls → campaign over the framework.
    if entities.framework_id is not None:
        params = {
            "framework_id": entities.framework_id,
        }
        if entities.system_id:
            params["system_id"] = entities.system_id
        return EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow="campaign",
            workflow_params=params,
            rule_matched="framework_id set, no control_ids",
        )

    # Rule 8: ambiguous — fall through.
    reasons = []
    if not entities.system_id:
        reasons.append("no system named")
    if not entities.framework_id:
        reasons.append("no framework named")
    if not entities.control_ids:
        reasons.append("no controls named")
    reason = (
        "Could not pick a workflow: "
        + (", ".join(reasons) or "no actionable entities")
        + ". Ask the user which control(s), framework, or questionnaire they want to work on."
    )
    return EngagementSelection(
        entities=entities,
        inspect_summary=inspect_summary,
        selected_workflow=None,
        rule_matched="",
        ambiguous=True,
        ambiguity_reason=reason,
    )


__all__ = ["SelectedWorkflow", "select_workflow"]
