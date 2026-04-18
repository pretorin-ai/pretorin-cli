"""Coverage tests for src/pretorin/mcp/handlers/workflow.py.

Tests workflow state, scope questions, policy questions, family tools,
and analytics handler functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult

from pretorin.mcp.handlers.workflow import (
    handle_answer_policy_question,
    handle_answer_scope_question,
    handle_get_analytics_summary,
    handle_get_campaign_status,
    handle_get_family_analytics,
    handle_get_family_bundle,
    handle_get_family_review_results,
    handle_get_pending_families,
    handle_get_pending_policy_questions,
    handle_get_pending_scope_questions,
    handle_get_policy_analytics,
    handle_get_policy_question_detail,
    handle_get_policy_review_results,
    handle_get_policy_workflow_state,
    handle_get_scope_question_detail,
    handle_get_scope_review_results,
    handle_get_workflow_state,
    handle_trigger_family_review,
    handle_trigger_policy_generation,
    handle_trigger_policy_review,
    handle_trigger_scope_generation,
    handle_trigger_scope_review,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**overrides) -> AsyncMock:
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _is_error(result) -> bool:
    return isinstance(result, CallToolResult) and result.isError is True


# ---------------------------------------------------------------------------
# Workflow State
# ---------------------------------------------------------------------------


class TestHandleGetWorkflowState:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_workflow_state={"state": "in_progress"})
        result = await handle_get_workflow_state(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.get_workflow_state.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        result = await handle_get_workflow_state(client, {"framework_id": "fw-1"})
        assert _is_error(result)

    @pytest.mark.anyio
    async def test_missing_framework_id(self):
        client = _make_client()
        result = await handle_get_workflow_state(client, {"system_id": "sys-1"})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Scope Questions
# ---------------------------------------------------------------------------


class TestHandleGetPendingScopeQuestions:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_pending_scope_questions={"questions": []})
        result = await handle_get_pending_scope_questions(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.get_pending_scope_questions.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_pending_scope_questions(client, {})
        assert _is_error(result)


class TestHandleGetScopeQuestionDetail:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_scope_question_detail={"question": "test?"})
        result = await handle_get_scope_question_detail(client, {
            "system_id": "sys-1", "question_id": "q-1", "framework_id": "fw-1",
        })
        client.get_scope_question_detail.assert_awaited_once_with("sys-1", "q-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_scope_question_detail(client, {"system_id": "sys-1"})
        assert _is_error(result)


class TestHandleAnswerScopeQuestion:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(answer_scope_question={"status": "answered"})
        result = await handle_answer_scope_question(client, {
            "system_id": "sys-1", "question_id": "q-1",
            "answer": "Yes", "framework_id": "fw-1",
        })
        client.answer_scope_question.assert_awaited_once_with("sys-1", "q-1", "Yes", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_answer_scope_question(client, {
            "system_id": "sys-1", "question_id": "q-1",
        })
        assert _is_error(result)


class TestHandleTriggerScopeGeneration:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(trigger_scope_generation={"job_id": "j-1"})
        result = await handle_trigger_scope_generation(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.trigger_scope_generation.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_trigger_scope_generation(client, {})
        assert _is_error(result)


class TestHandleTriggerScopeReview:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(trigger_scope_review={"job_id": "j-1"})
        result = await handle_trigger_scope_review(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.trigger_scope_review.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_trigger_scope_review(client, {})
        assert _is_error(result)


class TestHandleGetScopeReviewResults:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_scope_review_results={"results": []})
        result = await handle_get_scope_review_results(client, {
            "system_id": "sys-1", "job_id": "j-1",
        })
        client.get_scope_review_results.assert_awaited_once_with("sys-1", "j-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_scope_review_results(client, {"system_id": "sys-1"})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Policy Questions
# ---------------------------------------------------------------------------


class TestHandleGetPendingPolicyQuestions:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_pending_policy_questions={"questions": []})
        result = await handle_get_pending_policy_questions(client, {"policy_id": "p-1"})
        client.get_pending_policy_questions.assert_awaited_once_with("p-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_policy_id(self):
        client = _make_client()
        result = await handle_get_pending_policy_questions(client, {})
        assert _is_error(result)


class TestHandleGetPolicyQuestionDetail:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_policy_question_detail={"question": "what?"})
        result = await handle_get_policy_question_detail(client, {
            "policy_id": "p-1", "question_id": "q-1",
        })
        client.get_policy_question_detail.assert_awaited_once_with("p-1", "q-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_policy_question_detail(client, {})
        assert _is_error(result)


class TestHandleAnswerPolicyQuestion:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(answer_policy_question={"status": "ok"})
        result = await handle_answer_policy_question(client, {
            "policy_id": "p-1", "question_id": "q-1", "answer": "No",
        })
        client.answer_policy_question.assert_awaited_once_with("p-1", "q-1", "No")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_answer_policy_question(client, {"policy_id": "p-1"})
        assert _is_error(result)


class TestHandleTriggerPolicyGeneration:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(trigger_policy_generation={"job_id": "j-1"})
        result = await handle_trigger_policy_generation(client, {"policy_id": "p-1"})
        client.trigger_policy_generation.assert_awaited_once_with("p-1", system_id=None)
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_system_id(self):
        client = _make_client(trigger_policy_generation={"job_id": "j-1"})
        result = await handle_trigger_policy_generation(client, {
            "policy_id": "p-1", "system_id": "sys-1",
        })
        client.trigger_policy_generation.assert_awaited_once_with("p-1", system_id="sys-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_policy_id(self):
        client = _make_client()
        result = await handle_trigger_policy_generation(client, {})
        assert _is_error(result)


class TestHandleTriggerPolicyReview:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(trigger_policy_review={"job_id": "j-1"})
        result = await handle_trigger_policy_review(client, {"policy_id": "p-1"})
        client.trigger_policy_review.assert_awaited_once_with("p-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_policy_id(self):
        client = _make_client()
        result = await handle_trigger_policy_review(client, {})
        assert _is_error(result)


class TestHandleGetPolicyReviewResults:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_policy_review_results={"results": []})
        result = await handle_get_policy_review_results(client, {
            "policy_id": "p-1", "job_id": "j-1",
        })
        client.get_policy_review_results.assert_awaited_once_with("p-1", "j-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_policy_review_results(client, {})
        assert _is_error(result)


class TestHandleGetPolicyWorkflowState:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_policy_workflow_state={"state": "draft"})
        result = await handle_get_policy_workflow_state(client, {"policy_id": "p-1"})
        client.get_policy_workflow_state.assert_awaited_once_with("p-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_policy_id(self):
        client = _make_client()
        result = await handle_get_policy_workflow_state(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Family Tools
# ---------------------------------------------------------------------------


class TestHandleGetPendingFamilies:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_pending_families={"families": []})
        result = await handle_get_pending_families(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.get_pending_families.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_pending_families(client, {})
        assert _is_error(result)


class TestHandleGetFamilyBundle:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_family_bundle={"bundle": {}})
        result = await handle_get_family_bundle(client, {
            "system_id": "sys-1", "family_id": "AC", "framework_id": "fw-1",
        })
        client.get_family_bundle.assert_awaited_once_with("sys-1", "AC", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_family_bundle(client, {"system_id": "sys-1"})
        assert _is_error(result)


class TestHandleTriggerFamilyReview:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(trigger_family_review={"job_id": "j-1"})
        result = await handle_trigger_family_review(client, {
            "system_id": "sys-1", "family_id": "AC", "framework_id": "fw-1",
        })
        client.trigger_family_review.assert_awaited_once_with("sys-1", "AC", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_trigger_family_review(client, {})
        assert _is_error(result)


class TestHandleGetFamilyReviewResults:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_family_review_results={"results": []})
        result = await handle_get_family_review_results(client, {
            "system_id": "sys-1", "job_id": "j-1",
        })
        client.get_family_review_results.assert_awaited_once_with("sys-1", "j-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_family_review_results(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestHandleGetAnalyticsSummary:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_analytics_summary={"total": 100})
        result = await handle_get_analytics_summary(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.get_analytics_summary.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_analytics_summary(client, {})
        assert _is_error(result)


class TestHandleGetFamilyAnalytics:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_family_analytics={"data": []})
        result = await handle_get_family_analytics(client, {
            "system_id": "sys-1", "framework_id": "fw-1",
        })
        client.get_family_analytics.assert_awaited_once_with("sys-1", "fw-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_family_analytics(client, {})
        assert _is_error(result)


class TestHandleGetPolicyAnalytics:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_policy_analytics={"data": []})
        result = await handle_get_policy_analytics(client, {"policy_id": "p-1"})
        client.get_policy_analytics.assert_awaited_once_with("p-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_policy_id(self):
        client = _make_client()
        result = await handle_get_policy_analytics(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Campaign status (no-client tool)
# ---------------------------------------------------------------------------


class TestHandleGetCampaignStatus:
    @pytest.mark.anyio
    async def test_missing_checkpoint_path(self):
        client = _make_client()
        result = await handle_get_campaign_status(client, {})
        assert _is_error(result)
