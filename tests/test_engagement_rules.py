"""Pure-function tests for the engagement-layer routing rules.

The rule cascade is intentionally branch-heavy (8 paths) so each branch
gets explicit coverage. Drift tests live next to this file: any change
to the rule cascade must be reflected here.
"""

from __future__ import annotations

import pytest

from pretorin.engagement.entities import EngagementEntities
from pretorin.engagement.rules import select_workflow


def _e(**kw):
    """Build EngagementEntities with sensible defaults."""
    kw.setdefault("intent_verb", "work_on")
    kw.setdefault("raw_prompt", "test prompt")
    return EngagementEntities(**kw)


# =============================================================================
# Rule 1 — inspect_status
# =============================================================================


def test_inspect_status_returns_no_workflow() -> None:
    sel = select_workflow(_e(intent_verb="inspect_status"), {})
    assert sel.selected_workflow is None
    assert sel.ambiguous is False
    assert "inspect_status" in sel.rule_matched


# =============================================================================
# Rule 2 — campaign verb
# =============================================================================


def test_campaign_verb_routes_to_campaign() -> None:
    sel = select_workflow(_e(intent_verb="campaign", framework_id="nist-800-53-r5"), {})
    assert sel.selected_workflow == "campaign"
    assert sel.workflow_params["framework_id"] == "nist-800-53-r5"
    assert "intent_verb" in sel.rule_matched


def test_campaign_verb_with_control_filter() -> None:
    sel = select_workflow(
        _e(intent_verb="campaign", control_ids=["ac-2", "ac-3"], system_id="sys-1"),
        {},
    )
    assert sel.selected_workflow == "campaign"
    assert sel.workflow_params["control_filter"] == ["ac-2", "ac-3"]
    assert sel.workflow_params["system_id"] == "sys-1"


# =============================================================================
# Rule 3 — scope question
# =============================================================================


def test_explicit_scope_question_id_routes_to_scope_question() -> None:
    sel = select_workflow(_e(scope_question_ids=["sq-1"], system_id="sys-1"), {})
    assert sel.selected_workflow == "scope-question"
    assert sel.workflow_params["scope_question_ids"] == ["sq-1"]


def test_answer_intent_with_pending_scope_routes_to_scope_question() -> None:
    sel = select_workflow(
        _e(intent_verb="answer", system_id="sys-1"),
        {"pending_scope_questions": [{"id": "sq-1"}]},
    )
    assert sel.selected_workflow == "scope-question"


# =============================================================================
# Rule 4 — policy question
# =============================================================================


def test_explicit_policy_question_id_routes_to_policy_question() -> None:
    sel = select_workflow(_e(policy_question_ids=["pq-1"], system_id="sys-1"), {})
    assert sel.selected_workflow == "policy-question"
    assert sel.workflow_params["policy_question_ids"] == ["pq-1"]


def test_answer_intent_with_pending_policy_routes_to_policy_question() -> None:
    sel = select_workflow(
        _e(intent_verb="answer", system_id="sys-1"),
        {"pending_policy_questions": [{"id": "pq-1"}]},
    )
    assert sel.selected_workflow == "policy-question"


def test_scope_takes_precedence_over_policy_when_both_pending() -> None:
    """Scope is checked first in the cascade."""
    sel = select_workflow(
        _e(intent_verb="answer"),
        {
            "pending_scope_questions": [{"id": "sq-1"}],
            "pending_policy_questions": [{"id": "pq-1"}],
        },
    )
    assert sel.selected_workflow == "scope-question"


# =============================================================================
# Rule 5 — exactly one control id
# =============================================================================


def test_single_control_id_routes_to_single_control() -> None:
    sel = select_workflow(
        _e(control_ids=["ac-2"], system_id="sys-1", framework_id="nist-800-53-r5"),
        {},
    )
    assert sel.selected_workflow == "single-control"
    assert sel.workflow_params["control_id"] == "ac-2"
    assert sel.workflow_params["system_id"] == "sys-1"
    assert sel.workflow_params["framework_id"] == "nist-800-53-r5"


# =============================================================================
# Rule 6 — multiple control ids
# =============================================================================


def test_multiple_control_ids_routes_to_campaign() -> None:
    sel = select_workflow(_e(control_ids=["ac-2", "ac-3", "ac-4"]), {})
    assert sel.selected_workflow == "campaign"
    assert sel.workflow_params["control_filter"] == ["ac-2", "ac-3", "ac-4"]
    assert "len(control_ids) > 1" in sel.rule_matched


# =============================================================================
# Rule 7 — framework only, no controls
# =============================================================================


def test_framework_only_routes_to_campaign() -> None:
    sel = select_workflow(_e(framework_id="nist-800-53-r5", system_id="sys-1"), {})
    assert sel.selected_workflow == "campaign"
    assert sel.workflow_params["framework_id"] == "nist-800-53-r5"


# =============================================================================
# Rule 8 — ambiguous
# =============================================================================


def test_no_actionable_entities_returns_ambiguous() -> None:
    sel = select_workflow(_e(), {})
    assert sel.selected_workflow is None
    assert sel.ambiguous is True
    assert sel.ambiguity_reason is not None
    assert "no system named" in sel.ambiguity_reason


def test_ambiguous_carries_inspect_summary() -> None:
    """Even ambiguous responses include the inspect summary so the agent
    can show useful state to the user when asking for clarification."""
    inspect = {"workflow_state": {"stage": "scope"}}
    sel = select_workflow(_e(), inspect)
    assert sel.ambiguous is True
    assert sel.inspect_summary == inspect


# =============================================================================
# Determinism
# =============================================================================


@pytest.mark.parametrize(
    "entities,inspect",
    [
        (_e(intent_verb="inspect_status"), {}),
        (_e(intent_verb="campaign", framework_id="nist-800-53-r5"), {}),
        (_e(control_ids=["ac-2"], system_id="sys-1"), {}),
        (_e(), {}),
    ],
)
def test_select_workflow_is_deterministic(entities, inspect) -> None:
    """Same inputs → same outputs. The rule cascade has no randomness."""
    a = select_workflow(entities, inspect)
    b = select_workflow(entities, inspect)
    assert a.model_dump() == b.model_dump()
