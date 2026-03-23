"""Tests for the questionnaire population workflow."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from pretorin.client.models import OrgPolicyQuestionnaireResponse, ScopeResponse
from pretorin.workflows.questionnaire_population import (
    _build_task,
    _extract_json_object,
    _strip_json_fence,
    draft_policy_questionnaire,
    draft_scope_questionnaire,
)


class TestQuestionnaireParsingHelpers:
    def test_strip_json_fence_removes_markdown_wrapper(self) -> None:
        assert _strip_json_fence('```json\n{"ok": true}\n```') == '{"ok": true}'

    def test_extract_json_object_reads_embedded_payload(self) -> None:
        text = 'Model output:\n{"questions": [], "summary": "done"}\nThanks.'
        assert _extract_json_object(text) == {"questions": [], "summary": "done"}


class TestBuildTask:
    def test_build_task_includes_stateful_and_handoff_instructions(self) -> None:
        task = _build_task(
            workflow_name="scope",
            subject_label="Primary / fedramp-moderate",
            handoff_message="the user should return to the platform.",
            state_payload={"existing_answers": {"questions": []}, "persisted_review": {"readiness": "needs_work"}},
        )

        assert "Start from the existing saved answers" in task
        assert "return to the platform" in task
        assert '"persisted_review"' in task
        assert '"existing_answers"' in task


@pytest.mark.asyncio
async def test_draft_scope_questionnaire_success_uses_existing_answers_and_review() -> None:
    raw_response = (
        '{"questions": [{"question_id": "sd-1", "proposed_answer": "Updated answer", '
        '"confidence": "high", "evidence_summary": "Observed README", '
        '"needs_manual_input": false, "manual_input_reason": null}], '
        '"summary": "Filled one answer"}'
    )

    with patch("pretorin.workflows.questionnaire_population.CodexAgent") as mock_agent_ctor:
        mock_agent = mock_agent_ctor.return_value
        mock_agent.run = AsyncMock(return_value=SimpleNamespace(response=raw_response))

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary System"))
        client.get_scope = AsyncMock(
            return_value=ScopeResponse(
                scope_status="in_progress",
                scope_qa_responses={
                    "questions": [
                        {
                            "id": "sd-1",
                            "question": "What does the system do?",
                            "answer": "Existing answer",
                            "section": "system_description",
                        }
                    ]
                },
                scope_questions=[
                    {
                        "id": "sd-1",
                        "question": "What does the system do?",
                        "section": "system_description",
                        "section_title": "System Description",
                        "order": 1,
                        "guidance": {"tips": ["Explain the mission."]},
                    }
                ],
                scope_review={
                    "readiness": "needs_work",
                    "gaps": [{"area": "boundary", "severity": "medium", "description": "Clarify inherited services."}],
                },
                scope_reviewed_at="2026-03-02T00:00:00+00:00",
            )
        )

        result = await draft_scope_questionnaire(
            client,
            system_id="sys-1",
            framework_id="fedramp-moderate",
        )

    assert result["parse_status"] == "json"
    assert result["summary"] == "Filled one answer"
    task = mock_agent.run.await_args.kwargs["task"]
    assert "Existing answer" in task
    assert "Clarify inherited services." in task
    assert "scope page" in task


@pytest.mark.asyncio
async def test_draft_scope_questionnaire_returns_raw_fallback_for_non_json() -> None:
    with patch("pretorin.workflows.questionnaire_population.CodexAgent") as mock_agent_ctor:
        mock_agent = mock_agent_ctor.return_value
        mock_agent.run = AsyncMock(return_value=SimpleNamespace(response="plain text only"))

        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary System"))
        client.get_scope = AsyncMock(return_value=ScopeResponse(scope_questions=[]))

        result = await draft_scope_questionnaire(
            client,
            system_id="sys-1",
            framework_id="fedramp-moderate",
        )

    assert result["parse_status"] == "raw_fallback"
    assert result["questions"] == []


@pytest.mark.asyncio
async def test_draft_policy_questionnaire_success_includes_saved_findings() -> None:
    raw_response = (
        '{"questions": [{"question_id": "q_purpose_1", "proposed_answer": "Updated purpose", '
        '"confidence": "medium", "evidence_summary": "Observed IAM docs", '
        '"needs_manual_input": false, "manual_input_reason": null}], '
        '"summary": "Updated one policy answer"}'
    )

    questionnaire = OrgPolicyQuestionnaireResponse(
        policy_id="pol-1",
        name="Access Control Policy",
        policy_template_id="access-control-policy",
        policy_qa_responses={
            "questions": [
                {
                    "id": "q_purpose_1",
                    "question": "Why does this policy exist?",
                    "answer": "Existing purpose answer",
                    "section_id": "purpose",
                }
            ]
        },
        template={
            "template_id": "access-control-policy",
            "template_name": "Access Control Policy",
            "document_type": "policy",
            "questions": [
                {
                    "question_id": "q_purpose_1",
                    "question": "Why does this policy exist?",
                    "section_id": "purpose",
                    "order": 1,
                    "guidance": {"tips": ["Tie the answer to least privilege."]},
                }
            ],
            "sections": [{"section_id": "purpose", "title": "Purpose", "order": 1, "required_content": []}],
        },
        policy_review={
            "readiness": "needs_work",
            "recommended_changes": [{"section": "Purpose", "change": "Clarify business drivers.", "priority": "high"}],
        },
        policy_reviewed_at="2026-03-02T00:00:00+00:00",
    )

    with patch("pretorin.workflows.questionnaire_population.CodexAgent") as mock_agent_ctor:
        mock_agent = mock_agent_ctor.return_value
        mock_agent.run = AsyncMock(return_value=SimpleNamespace(response=raw_response))

        client = AsyncMock()

        result = await draft_policy_questionnaire(
            client,
            questionnaire=questionnaire,
        )

    assert result["parse_status"] == "json"
    assert result["summary"] == "Updated one policy answer"
    task = mock_agent.run.await_args.kwargs["task"]
    assert "Existing purpose answer" in task
    assert "Clarify business drivers." in task
    assert "policy page" in task


@pytest.mark.asyncio
async def test_draft_questionnaire_wraps_runtime_error() -> None:
    with patch(
        "pretorin.workflows.questionnaire_population.CodexAgent",
        side_effect=RuntimeError("Codex agent is not available"),
    ):
        client = AsyncMock()
        client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary System"))
        client.get_scope = AsyncMock(return_value=ScopeResponse(scope_questions=[]))

        with pytest.raises(Exception, match="Codex agent is not available"):
            await draft_scope_questionnaire(
                client,
                system_id="sys-1",
                framework_id="fedramp-moderate",
            )
