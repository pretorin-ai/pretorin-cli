"""Tests for campaign CLI and external-agent-first workflow behavior."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import PretorianClientError
from pretorin.client.models import (
    ControlBatchResponse,
    ControlSummary,
    OrgPolicyListResponse,
    OrgPolicyQuestionnaireResponse,
    ScopeResponse,
)
from pretorin.workflows.campaign import (
    CampaignCheckpoint,
    CampaignItemState,
    CampaignRunRequest,
    CampaignRunSummary,
    apply_campaign,
    claim_campaign_items,
    get_campaign_status,
    prepare_campaign,
    run_campaign,
    submit_campaign_proposal,
)
from pretorin.workflows.campaign_protocol import (
    build_campaign_request,
    build_campaign_request_from_mapping,
)

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
    set_json_mode(False)
    yield
    set_json_mode(False)


def _mock_campaign_client() -> AsyncMock:
    client = AsyncMock()
    client.is_configured = True
    client.api_base_url = "https://platform.pretorin.com/api/v1/public"
    return client


def _policy_questionnaire() -> OrgPolicyQuestionnaireResponse:
    return OrgPolicyQuestionnaireResponse(
        policy_id="pol-001",
        name="Access Control Policy",
        policy_template_id="access-control-policy",
        policy_qa_status="in_progress",
        policy_qa_responses={
            "questions": [
                {
                    "id": "q_scope_2",
                    "question": "What systems are covered?",
                    "answer": None,
                    "section_id": "scope",
                }
            ]
        },
        template={
            "template_id": "access-control-policy",
            "template_name": "Access Control Policy",
            "document_type": "policy",
            "sections": [
                {"section_id": "scope", "title": "Scope", "order": 1, "required_content": []},
            ],
            "questions": [
                {
                    "question_id": "q_scope_2",
                    "question": "What systems are covered?",
                    "section_id": "scope",
                    "order": 1,
                    "guidance": {"tips": ["Name covered systems."]},
                },
            ],
        },
        policy_review={
            "readiness": "needs_work",
            "recommended_changes": [{"section": "Scope", "change": "Add service accounts.", "priority": "high"}],
        },
    )


def _scope_response() -> ScopeResponse:
    return ScopeResponse(
        scope_status="in_progress",
        scope_qa_responses={
            "questions": [
                {
                    "id": "sd-3",
                    "question": "What information does the system handle?",
                    "answer": None,
                    "section": "system_description",
                }
            ]
        },
        scope_questions=[
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
            "recommended_changes": [
                {"section": "System Description", "change": "Mention audit logs.", "priority": "high"}
            ],
        },
    )


def _summary_for(request: CampaignRunRequest, *, prepared_only: bool = False) -> CampaignRunSummary:
    return CampaignRunSummary(
        domain=request.domain,
        mode=request.mode,
        apply=request.apply,
        output_mode=request.output,
        checkpoint_path=str(request.checkpoint_path),
        workflow_snapshot={"subject": "Primary / fedramp-moderate"},
        total=1,
        pending=1 if prepared_only else 0,
        claimed=0,
        proposed=0,
        succeeded=0 if prepared_only else 1,
        failed=0,
        skipped=0,
        retries_used=0,
        items={},
        status_snapshot="snapshot",
        prepared_only=prepared_only,
        next_steps=["Use MCP tools"] if prepared_only else [],
    )


def test_controls_campaign_json_builds_request() -> None:
    client = _mock_campaign_client()
    captured: dict[str, CampaignRunRequest] = {}

    async def _capture(_: object, request: CampaignRunRequest) -> CampaignRunSummary:
        captured["request"] = request
        return _summary_for(request)

    with (
        patch("pretorin.cli.campaign.PretorianClient") as mock_ctor,
        patch("pretorin.cli.campaign.run_campaign", AsyncMock(side_effect=_capture)),
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            [
                "--json",
                "campaign",
                "controls",
                "--system",
                "Primary",
                "--framework-id",
                "fedramp-moderate",
                "--family",
                "AC",
                "--mode",
                "initial",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["domain"] == "controls"
    assert payload["mode"] == "initial"
    assert captured["request"].family_id == "AC"
    assert captured["request"].apply is False
    assert captured["request"].artifacts == "both"


def test_controls_campaign_review_fix_requires_review_job() -> None:
    result = runner.invoke(
        app,
        [
            "campaign",
            "controls",
            "--system",
            "Primary",
            "--framework-id",
            "fedramp-moderate",
            "--family",
            "AC",
            "--mode",
            "review-fix",
        ],
    )

    assert result.exit_code == 2


def test_policy_campaign_defaults_to_all_incomplete() -> None:
    client = _mock_campaign_client()
    captured: dict[str, CampaignRunRequest] = {}

    async def _capture(_: object, request: CampaignRunRequest) -> CampaignRunSummary:
        captured["request"] = request
        return _summary_for(request)

    with (
        patch("pretorin.cli.campaign.PretorianClient") as mock_ctor,
        patch("pretorin.cli.campaign.run_campaign", AsyncMock(side_effect=_capture)),
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(app, ["campaign", "policy", "--mode", "answer"])

    assert result.exit_code == 0
    assert captured["request"].all_incomplete is True
    assert captured["request"].policy_ids == []


def test_cli_and_mcp_build_the_same_controls_request(tmp_path: Path) -> None:
    cli_request = build_campaign_request(
        domain="controls",
        mode="review-fix",
        apply=True,
        output="json",
        concurrency=4,
        max_retries=2,
        checkpoint_path=tmp_path / "campaign.json",
        working_directory=tmp_path,
        system="Primary",
        framework_id="fedramp-moderate",
        family_id="AC",
        review_job="job-123",
        artifacts="both",
    )
    mcp_request = build_campaign_request_from_mapping(
        {
            "domain": "controls",
            "mode": "review-fix",
            "apply": True,
            "output": "json",
            "concurrency": 4,
            "max_retries": 2,
            "checkpoint_path": str(tmp_path / "campaign.json"),
            "working_directory": str(tmp_path),
            "system_id": "Primary",
            "framework_id": "fedramp-moderate",
            "family_id": "AC",
            "review_job": "job-123",
            "artifacts": "both",
        }
    )

    assert cli_request.to_dict() == mcp_request.to_dict()


def test_campaign_protocol_normalizes_control_ids_from_mcp_mapping(tmp_path: Path) -> None:
    request = build_campaign_request_from_mapping(
        {
            "domain": "controls",
            "mode": "initial",
            "output": "json",
            "checkpoint_path": str(tmp_path / "campaign.json"),
            "working_directory": str(tmp_path),
            "system_id": "Primary",
            "framework_id": "fedramp-moderate",
            "control_ids": ["ac-2", "SC-7"],
        }
    )

    assert request.control_ids == ["ac-02", "sc-07"]


def test_campaign_protocol_rejects_invalid_policy_selector_mix(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Use either --policies or --all-incomplete"):
        build_campaign_request(
            domain="policy",
            mode="answer",
            apply=False,
            output="json",
            concurrency=1,
            max_retries=1,
            checkpoint_path=tmp_path / "campaign.json",
            working_directory=tmp_path,
            policy_ids=["pol-001"],
            all_incomplete=True,
        )


def test_campaign_cli_shows_prepare_guidance_when_builtin_is_absent() -> None:
    client = _mock_campaign_client()
    request_summary = _summary_for(
        CampaignRunRequest(
            domain="scope",
            mode="answer",
            apply=False,
            output="compact",
            concurrency=1,
            max_retries=1,
            checkpoint_path=Path("/tmp/campaign.json"),
            working_directory=Path.cwd(),
            system="Primary",
            framework_id="fedramp-moderate",
        ),
        prepared_only=True,
    )

    with (
        patch("pretorin.cli.campaign.PretorianClient") as mock_ctor,
        patch("pretorin.cli.campaign.run_campaign", AsyncMock(return_value=request_summary)),
    ):
        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)
        mock_ctor.return_value = ctx

        result = runner.invoke(
            app,
            ["campaign", "scope", "--system", "Primary", "--framework-id", "fedramp-moderate", "--mode", "answer"],
        )

    assert result.exit_code == 0
    assert "Checkpoint:" in result.stdout
    assert "Use MCP tools" in result.stdout


def test_campaign_status_command_reads_checkpoint(tmp_path: Path) -> None:
    checkpoint = CampaignCheckpoint(
        version=2,
        identity={"domain": "scope", "mode": "answer", "apply": False},
        request={
            "domain": "scope",
            "mode": "answer",
            "apply": False,
            "output": "json",
            "concurrency": 1,
            "max_retries": 1,
            "working_directory": str(tmp_path),
        },
        output="json",
        created_at="2026-04-02T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        workflow_snapshot={"subject": "Primary / fedramp-moderate"},
        items={"sd-3": CampaignItemState(item={"item_id": "sd-3", "label": "sd-3", "kind": "scope-question"})},
        events=[],
    )
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(checkpoint.to_dict()))

    result = runner.invoke(app, ["--json", "campaign", "status", "--checkpoint", str(path)])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["checkpoint_path"] == str(path)
    assert payload["pending"] == 1


@pytest.mark.asyncio
async def test_prepare_campaign_controls_review_fix_filters_to_findings(tmp_path: Path) -> None:
    client = _mock_campaign_client()
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.get_workflow_state = AsyncMock(return_value={"lifecycle_stage": "controls"})
    client.get_analytics_summary = AsyncMock(return_value={"controls_total": 2})
    client.get_family_analytics = AsyncMock(return_value={"families": []})
    client.list_controls = AsyncMock(
        return_value=[
            ControlSummary(id="ac-02", title="Account Management", family_id="AC"),
            ControlSummary(id="ac-03", title="Access Enforcement", family_id="AC"),
        ]
    )
    client.get_family_bundle = AsyncMock(return_value={"family_id": "AC"})
    client.get_controls_batch = AsyncMock(return_value=ControlBatchResponse(controls=[], total=0))
    client.get_family_review_results = AsyncMock(
        return_value={
            "findings": [
                {"target_ref": "ac-02", "issue": "Missing evidence", "recommended_fix": "Add evidence"}
            ]
        }
    )

    request = CampaignRunRequest(
        domain="controls",
        mode="review-fix",
        apply=False,
        output="json",
        concurrency=2,
        max_retries=1,
        checkpoint_path=tmp_path / "controls-review.json",
        working_directory=tmp_path,
        system="Primary",
        framework_id="fedramp-moderate",
        family_id="AC",
        review_job="job-123",
    )

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ):
        checkpoint = await prepare_campaign(client, request)

    assert set(checkpoint.items.keys()) == {"ac-02"}


@pytest.mark.asyncio
async def test_prepare_claim_submit_apply_policy_campaign(tmp_path: Path) -> None:
    client = _mock_campaign_client()
    client.list_org_policies = AsyncMock(
        return_value=OrgPolicyListResponse(
            policies=[
                {
                    "id": "pol-001",
                    "name": "Access Control Policy",
                    "policy_template_id": "access-control-policy",
                    "status": "draft",
                    "policy_qa_status": "in_progress",
                }
            ],
            total=1,
        )
    )
    client.get_policy_workflow_state = AsyncMock(return_value={"next_action": "answer_questions"})
    questionnaire = _policy_questionnaire()
    client.get_org_policy_questionnaire = AsyncMock(return_value=questionnaire)
    client.patch_org_policy_qa = AsyncMock(return_value=questionnaire)

    request = CampaignRunRequest(
        domain="policy",
        mode="review-fix",
        apply=False,
        output="json",
        concurrency=1,
        max_retries=1,
        checkpoint_path=tmp_path / "policy-review.json",
        working_directory=tmp_path,
        policy_ids=["pol-001"],
    )

    await prepare_campaign(client, request)
    claim = claim_campaign_items(
        request.checkpoint_path,
        max_items=1,
        lease_owner="codex-main",
        lease_ttl_seconds=120,
    )
    assert claim["claimed"][0]["item_id"] == "pol-001"

    submit_campaign_proposal(
        request.checkpoint_path,
        item_id="pol-001",
        proposal={
            "questions": [
                {
                    "question_id": "q_scope_2",
                    "proposed_answer": "Production systems, CUI, administrators, and service accounts.",
                }
            ]
        },
    )
    summary = await apply_campaign(client, request.checkpoint_path)

    assert summary.succeeded == 1
    assert summary.apply is True
    status = get_campaign_status(request.checkpoint_path)
    assert status.apply is True
    client.patch_org_policy_qa.assert_awaited_once_with(
        "pol-001",
        [{"question_id": "q_scope_2", "answer": "Production systems, CUI, administrators, and service accounts."}],
    )


@pytest.mark.asyncio
async def test_run_campaign_prepares_only_when_builtin_backend_missing(tmp_path: Path) -> None:
    client = _mock_campaign_client()
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.get_workflow_state = AsyncMock(return_value={"lifecycle_stage": "scope"})
    client.get_scope = AsyncMock(return_value=_scope_response())

    request = CampaignRunRequest(
        domain="scope",
        mode="answer",
        apply=False,
        output="json",
        concurrency=1,
        max_retries=1,
        checkpoint_path=tmp_path / "scope-review.json",
        working_directory=tmp_path,
        system="Primary",
        framework_id="fedramp-moderate",
    )

    with (
        patch(
            "pretorin.workflows.campaign.resolve_execution_context",
            AsyncMock(return_value=("sys-1", "fedramp-moderate")),
        ),
        patch("pretorin.workflows.campaign._builtin_executor_available", return_value=False),
    ):
        summary = await run_campaign(client, request)

    assert summary.prepared_only is True
    assert summary.pending == 1
    assert "pretorin_claim_campaign_items" in " ".join(summary.next_steps)


@pytest.mark.asyncio
async def test_run_campaign_uses_builtin_executor_when_available(tmp_path: Path) -> None:
    client = _mock_campaign_client()
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.get_workflow_state = AsyncMock(return_value={"lifecycle_stage": "scope"})
    client.get_scope = AsyncMock(return_value=_scope_response())

    request = CampaignRunRequest(
        domain="scope",
        mode="answer",
        apply=False,
        output="json",
        concurrency=1,
        max_retries=1,
        checkpoint_path=tmp_path / "scope-review.json",
        working_directory=tmp_path,
        system="Primary",
        framework_id="fedramp-moderate",
    )

    builtin_summary = _summary_for(request)
    with (
        patch(
            "pretorin.workflows.campaign.resolve_execution_context",
            AsyncMock(return_value=("sys-1", "fedramp-moderate")),
        ),
        patch("pretorin.workflows.campaign._builtin_executor_available", return_value=True),
        patch("pretorin.workflows.campaign_builtin.execute_prepared_campaign", AsyncMock(return_value=builtin_summary)),
    ):
        summary = await run_campaign(client, request)

    assert summary.prepared_only is False
    assert summary.succeeded == 1


def test_submit_campaign_proposal_rejects_invalid_questionnaire_shape(tmp_path: Path) -> None:
    checkpoint = CampaignCheckpoint(
        version=2,
        identity={"domain": "policy", "mode": "answer", "apply": False},
        request={
            "domain": "policy",
            "mode": "answer",
            "apply": False,
            "output": "json",
            "concurrency": 1,
            "max_retries": 1,
            "working_directory": str(tmp_path),
        },
        output="json",
        created_at="2026-04-02T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        workflow_snapshot={"subject": "Policies"},
        items={"pol-001": CampaignItemState(item={"item_id": "pol-001", "label": "Policy", "kind": "policy"})},
        events=[],
    )
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(checkpoint.to_dict()))

    with pytest.raises(PretorianClientError, match="questions list"):
        submit_campaign_proposal(path, item_id="pol-001", proposal={"summary": "missing questions"})


@pytest.mark.asyncio
async def test_apply_campaign_rejects_checkpoint_with_wrong_environment(tmp_path: Path) -> None:
    """apply_campaign should raise when checkpoint URL differs from client URL."""
    client = _mock_campaign_client()
    client.api_base_url = "https://platform.pretorin.com/api/v1/public"

    checkpoint = CampaignCheckpoint(
        version=2,
        identity={"domain": "policy", "mode": "answer", "apply": False},
        request={
            "domain": "policy",
            "mode": "answer",
            "apply": False,
            "output": "json",
            "concurrency": 1,
            "max_retries": 1,
            "working_directory": str(tmp_path),
        },
        output="json",
        created_at="2026-04-02T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        workflow_snapshot={
            "domain": "policy",
            "subject": "Policies",
            "platform_api_base_url": "https://localhost:8000/api/v1/public",
        },
        items={"pol-001": CampaignItemState(item={"item_id": "pol-001", "label": "Policy", "kind": "policy"})},
        events=[],
    )
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(checkpoint.to_dict()))

    with pytest.raises(PretorianClientError, match="prepared against"):
        await apply_campaign(client, path)


@pytest.mark.asyncio
async def test_apply_campaign_warns_for_legacy_checkpoint_without_url(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Legacy checkpoints without platform_api_base_url should log a warning but not raise."""
    client = _mock_campaign_client()
    client.api_base_url = "https://platform.pretorin.com/api/v1/public"

    # Checkpoint with no items to apply — just verify the warning fires and no error is raised.
    checkpoint = CampaignCheckpoint(
        version=2,
        identity={"domain": "policy", "mode": "answer", "apply": False},
        request={
            "domain": "policy",
            "mode": "answer",
            "apply": False,
            "output": "json",
            "concurrency": 1,
            "max_retries": 1,
            "working_directory": str(tmp_path),
        },
        output="json",
        created_at="2026-04-02T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        workflow_snapshot={"domain": "policy", "subject": "Policies"},
        items={},
        events=[],
    )
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(checkpoint.to_dict()))

    import logging

    with caplog.at_level(logging.WARNING, logger="pretorin.workflows.campaign"):
        summary = await apply_campaign(client, path)

    assert "cannot verify environment affinity" in caplog.text
    assert summary.total == 0


def test_get_campaign_status_includes_snapshot(tmp_path: Path) -> None:
    checkpoint = CampaignCheckpoint(
        version=2,
        identity={"domain": "controls", "mode": "initial", "apply": False},
        request={
            "domain": "controls",
            "mode": "initial",
            "apply": False,
            "output": "json",
            "concurrency": 1,
            "max_retries": 1,
            "working_directory": str(tmp_path),
        },
        output="json",
        created_at="2026-04-02T00:00:00+00:00",
        updated_at="2026-04-02T00:00:00+00:00",
        workflow_snapshot={"subject": "Primary / fedramp-moderate"},
        items={"ac-02": CampaignItemState(item={"item_id": "ac-02", "label": "AC-02", "kind": "control"})},
        events=[],
    )
    path = tmp_path / "campaign.json"
    path.write_text(json.dumps(checkpoint.to_dict()))

    summary = get_campaign_status(path)

    assert "Campaign: controls:initial" in summary.status_snapshot
    assert summary.pending == 1
