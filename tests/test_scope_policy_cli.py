"""Tests for the stateful scope and policy CLI flows."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.models import OrgPolicyListResponse, OrgPolicyQuestionnaireResponse, ScopeResponse

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    set_json_mode(False)
    yield
    set_json_mode(False)


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.client.api.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


def _config_stub() -> SimpleNamespace:
    return SimpleNamespace(platform_api_base_url="https://platform.example/api/v1/public")


def _scope_response() -> ScopeResponse:
    return ScopeResponse(
        scope_status="in_progress",
        scope_qa_responses={
            "questions": [
                {
                    "id": "sd-1",
                    "question": "What does the system do?",
                    "answer": "Existing system answer",
                    "section": "system_description",
                },
                {
                    "id": "sd-3",
                    "question": "What information does the system handle?",
                    "answer": None,
                    "section": "system_description",
                },
            ]
        },
        scope_questions=[
            {
                "id": "sd-1",
                "question": "What does the system do?",
                "section": "system_description",
                "section_title": "System Description",
                "order": 0,
                "guidance": {"tips": ["Explain the system mission."]},
            },
            {
                "id": "sd-3",
                "question": "What information does the system handle?",
                "section": "system_description",
                "section_title": "System Description",
                "order": 1,
                "guidance": {"tips": ["List sensitive data types."]},
            },
        ],
        scope_review={
            "readiness": "needs_work",
            "gaps": [{"area": "boundary", "severity": "medium", "description": "Clarify inherited services."}],
            "recommended_changes": [
                {"section": "System Description", "change": "Add user counts.", "priority": "high"}
            ],
        },
        scope_reviewed_at="2026-03-02T00:00:00+00:00",
    )


def _policy_list() -> OrgPolicyListResponse:
    return OrgPolicyListResponse(
        policies=[
            {
                "id": "pol-001",
                "name": "Access Control Policy",
                "policy_template_id": "access-control-policy",
                "status": "draft",
                "policy_qa_status": "in_progress",
                "policy_reviewed_at": "2026-03-02T00:00:00+00:00",
            }
        ],
        total=1,
    )


def _policy_questionnaire() -> OrgPolicyQuestionnaireResponse:
    return OrgPolicyQuestionnaireResponse(
        policy_id="pol-001",
        name="Access Control Policy",
        policy_template_id="access-control-policy",
        policy_qa_status="in_progress",
        policy_qa_responses={
            "questions": [
                {
                    "id": "q_purpose_1",
                    "question": "Why does this Access Control Policy exist?",
                    "answer": "Existing purpose answer",
                    "section_id": "purpose",
                },
                {
                    "id": "q_scope_2",
                    "question": "What systems are covered?",
                    "answer": None,
                    "section_id": "scope",
                },
            ]
        },
        template={
            "template_id": "access-control-policy",
            "template_name": "Access Control Policy",
            "document_type": "policy",
            "sections": [
                {"section_id": "purpose", "title": "Purpose", "order": 1, "required_content": []},
                {"section_id": "scope", "title": "Scope", "order": 2, "required_content": []},
            ],
            "questions": [
                {
                    "question_id": "q_purpose_1",
                    "question": "Why does this Access Control Policy exist?",
                    "section_id": "purpose",
                    "order": 1,
                    "guidance": {"tips": ["Tie the policy to least privilege."]},
                },
                {
                    "question_id": "q_scope_2",
                    "question": "What systems are covered?",
                    "section_id": "scope",
                    "order": 2,
                    "guidance": {"tips": ["Name the systems and user groups."]},
                },
            ],
        },
        policy_review={
            "readiness": "needs_work",
            "gaps": [{"area": "scope", "severity": "medium", "description": "Clarify exclusions."}],
            "recommended_changes": [{"section": "Scope", "change": "Add service accounts.", "priority": "high"}],
        },
        policy_reviewed_at="2026-03-02T00:00:00+00:00",
    )


def test_scope_show_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.get_scope = AsyncMock(return_value=_scope_response())

    with patch("pretorin.cli.scope.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.scope.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ), patch("pretorin.cli.scope.Config", return_value=_config_stub()):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["--json", "scope", "show", "--system", "Primary", "--framework-id", "fedramp-moderate"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["system_id"] == "sys-1"
    assert payload["scope"]["scope_review"]["readiness"] == "needs_work"
    assert payload["handoff_url"] == "https://platform.example/compliance/scope"


def test_scope_populate_json_reads_existing_state() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.get_scope = AsyncMock(return_value=_scope_response())

    proposal = {
        "parse_status": "json",
        "summary": "Filled one missing answer from observed configuration.",
        "questions": [
            {
                "question_id": "sd-1",
                "proposed_answer": "Existing system answer",
                "confidence": "high",
                "evidence_summary": "No change needed.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            },
            {
                "question_id": "sd-3",
                "proposed_answer": "The system handles CUI and audit logs.",
                "confidence": "medium",
                "evidence_summary": "Observed compliance artifacts and logging configuration.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            },
        ],
    }

    with patch("pretorin.cli.scope.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.scope.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ), patch("pretorin.cli.scope.draft_scope_questionnaire", AsyncMock(return_value=proposal)), patch(
        "pretorin.cli.scope.Config", return_value=_config_stub()
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["--json", "scope", "populate", "--system", "Primary", "--framework-id", "fedramp-moderate"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["summary"] == proposal["summary"]
    assert payload["updates"] == [{"question_id": "sd-3", "answer": "The system handles CUI and audit logs."}]
    assert payload["diffs"][0]["status"] == "unchanged"
    assert payload["diffs"][1]["status"] == "newly_filled"
    client.patch_scope_qa.assert_not_called()


def test_scope_populate_apply_patches_only_changed_answers() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.get_scope = AsyncMock(return_value=_scope_response())
    client.patch_scope_qa = AsyncMock(return_value=_scope_response())

    proposal = {
        "parse_status": "json",
        "summary": "One answer updated.",
        "questions": [
            {
                "question_id": "sd-3",
                "proposed_answer": "The system handles CUI and audit logs.",
                "confidence": "medium",
                "evidence_summary": "Observed compliance artifacts and logging configuration.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            }
        ],
    }

    with patch("pretorin.cli.scope.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.scope.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ), patch("pretorin.cli.scope.draft_scope_questionnaire", AsyncMock(return_value=proposal)), patch(
        "pretorin.cli.scope.Config", return_value=_config_stub()
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["scope", "populate", "--system", "Primary", "--framework-id", "fedramp-moderate", "--apply"],
        )

    assert result.exit_code == 0
    client.patch_scope_qa.assert_awaited_once_with(
        "sys-1",
        "fedramp-moderate",
        [{"question_id": "sd-3", "answer": "The system handles CUI and audit logs."}],
    )


def test_scope_populate_json_apply_patches_changed_answers() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.get_scope = AsyncMock(return_value=_scope_response())
    client.patch_scope_qa = AsyncMock(return_value=_scope_response())

    proposal = {
        "parse_status": "json",
        "summary": "One answer updated.",
        "questions": [
            {
                "question_id": "sd-3",
                "proposed_answer": "The system handles CUI and audit logs.",
                "confidence": "medium",
                "evidence_summary": "Observed compliance artifacts and logging configuration.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            }
        ],
    }

    with patch("pretorin.cli.scope.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.scope.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ), patch("pretorin.cli.scope.draft_scope_questionnaire", AsyncMock(return_value=proposal)), patch(
        "pretorin.cli.scope.Config", return_value=_config_stub()
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["--json", "scope", "populate", "--system", "Primary", "--framework-id", "fedramp-moderate", "--apply"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    client.patch_scope_qa.assert_awaited_once_with(
        "sys-1",
        "fedramp-moderate",
        [{"question_id": "sd-3", "answer": "The system handles CUI and audit logs."}],
    )


def test_policy_list_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(return_value=_policy_list())

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["--json", "policy", "list"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["policies"][0]["policy_template_id"] == "access-control-policy"


def test_policy_show_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(return_value=_policy_list())
    client.get_org_policy_questionnaire = AsyncMock(return_value=_policy_questionnaire())

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.policy.Config", return_value=_config_stub()
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["--json", "policy", "show", "--policy", "access-control-policy"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["policy"]["policy_review"]["gaps"][0]["area"] == "scope"
    assert payload["handoff_url"] == (
        "https://platform.example/compliance/policies?openPolicyId=pol-001&openWorkflow=1"
    )


def test_policy_populate_json_resolves_by_template_and_builds_diffs() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(return_value=_policy_list())
    client.get_org_policy_questionnaire = AsyncMock(return_value=_policy_questionnaire())

    proposal = {
        "parse_status": "json",
        "summary": "Filled the missing scope answer.",
        "questions": [
            {
                "question_id": "q_purpose_1",
                "proposed_answer": "Existing purpose answer",
                "confidence": "high",
                "evidence_summary": "No change needed.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            },
            {
                "question_id": "q_scope_2",
                "proposed_answer": "Production systems, CUI, and administrators.",
                "confidence": "medium",
                "evidence_summary": "Observed repository and deployment boundaries.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            },
        ],
    }

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.policy.draft_policy_questionnaire", AsyncMock(return_value=proposal)
    ), patch("pretorin.cli.policy.Config", return_value=_config_stub()):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["--json", "policy", "populate", "--policy", "access-control-policy"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["policy_id"] == "pol-001"
    assert payload["updates"] == [
        {"question_id": "q_scope_2", "answer": "Production systems, CUI, and administrators."}
    ]
    assert payload["diffs"][0]["status"] == "unchanged"
    assert payload["diffs"][1]["status"] == "newly_filled"
    client.patch_org_policy_qa.assert_not_called()


def test_policy_show_rejects_ambiguous_name_matches() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(
        return_value=OrgPolicyListResponse(
            policies=[
                {
                    "id": "pol-001",
                    "name": "Access Control Policy",
                    "policy_template_id": "access-control-policy",
                    "status": "draft",
                },
                {
                    "id": "pol-002",
                    "name": "access control policy",
                    "policy_template_id": "enhanced-access-control-policy",
                    "status": "draft",
                },
            ],
            total=2,
        )
    )

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor:
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["policy", "show", "--policy", "Access Control Policy"])

    assert result.exit_code == 1
    assert "ambiguous" in result.stdout.lower()


def test_policy_populate_apply_patches_only_changed_answers() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(return_value=_policy_list())
    client.get_org_policy_questionnaire = AsyncMock(return_value=_policy_questionnaire())
    client.patch_org_policy_qa = AsyncMock(return_value=_policy_questionnaire())

    proposal = {
        "parse_status": "json",
        "summary": "Filled the missing scope answer.",
        "questions": [
            {
                "question_id": "q_scope_2",
                "proposed_answer": "Production systems, CUI, and administrators.",
                "confidence": "medium",
                "evidence_summary": "Observed repository and deployment boundaries.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            }
        ],
    }

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.policy.draft_policy_questionnaire", AsyncMock(return_value=proposal)
    ), patch("pretorin.cli.policy.Config", return_value=_config_stub()):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["policy", "populate", "--policy", "access-control-policy", "--apply"])

    assert result.exit_code == 0
    client.patch_org_policy_qa.assert_awaited_once_with(
        "pol-001",
        [{"question_id": "q_scope_2", "answer": "Production systems, CUI, and administrators."}],
    )


def test_policy_populate_json_apply_patches_changed_answers() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_org_policies = AsyncMock(return_value=_policy_list())
    client.get_org_policy_questionnaire = AsyncMock(return_value=_policy_questionnaire())
    client.patch_org_policy_qa = AsyncMock(return_value=_policy_questionnaire())

    proposal = {
        "parse_status": "json",
        "summary": "Filled the missing scope answer.",
        "questions": [
            {
                "question_id": "q_scope_2",
                "proposed_answer": "Production systems, CUI, and administrators.",
                "confidence": "medium",
                "evidence_summary": "Observed repository and deployment boundaries.",
                "needs_manual_input": False,
                "manual_input_reason": None,
            }
        ],
    }

    with patch("pretorin.cli.policy.PretorianClient") as mock_ctor, patch(
        "pretorin.cli.policy.draft_policy_questionnaire", AsyncMock(return_value=proposal)
    ), patch("pretorin.cli.policy.Config", return_value=_config_stub()):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["--json", "policy", "populate", "--policy", "access-control-policy", "--apply"],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    client.patch_org_policy_qa.assert_awaited_once_with(
        "pol-001",
        [{"question_id": "q_scope_2", "answer": "Production systems, CUI, and administrators."}],
    )
