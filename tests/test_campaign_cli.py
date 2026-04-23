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
    ControlFamilySummary,
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
    client.list_control_families = AsyncMock(
        return_value=[
            ControlFamilySummary(
                id="AC",
                title="Access Control",
                controls_count=2,
                **{"class": "nist"},
            )
        ]
    )
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


def _soc2_cc6_client(*, list_controls_return: list[ControlSummary] | None = None) -> AsyncMock:
    """Build a mock client preloaded for SOC 2 CC6 family_id resolution tests."""
    client = _mock_campaign_client()
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.get_workflow_state = AsyncMock(return_value={"lifecycle_stage": "controls"})
    client.get_analytics_summary = AsyncMock(return_value={"controls_total": 2})
    client.get_family_analytics = AsyncMock(return_value={"families": []})
    client.list_control_families = AsyncMock(
        return_value=[
            ControlFamilySummary(id="CC1", title="Control Environment", controls_count=4, **{"class": "soc2"}),
            ControlFamilySummary(id="CC6", title="Logical and Physical Access", controls_count=8, **{"class": "soc2"}),
            ControlFamilySummary(id="PI1", title="Processing Integrity", controls_count=3, **{"class": "soc2"}),
        ]
    )
    controls = list_controls_return
    if controls is None:
        controls = [
            ControlSummary(id="CC6.1", title="Logical Access Security", family_id="CC6"),
            ControlSummary(id="CC6.2", title="Access Provisioning", family_id="CC6"),
        ]
    client.list_controls = AsyncMock(return_value=controls)
    client.get_family_bundle = AsyncMock(return_value={"family_id": "CC6"})
    client.get_controls_batch = AsyncMock(return_value=ControlBatchResponse(controls=[], total=0))
    return client


def _soc2_cc6_request(tmp_path: Path, *, family_id: str) -> CampaignRunRequest:
    return CampaignRunRequest(
        domain="controls",
        mode="initial",
        apply=False,
        output="json",
        concurrency=2,
        max_retries=1,
        checkpoint_path=tmp_path / "controls-cc6.json",
        working_directory=tmp_path,
        system="Primary",
        framework_id="soc2",
        family_id=family_id,
    )


@pytest.mark.asyncio
async def test_prepare_campaign_resolves_soc2_exact_family(tmp_path: Path) -> None:
    """CC6 (canonical, exact match) resolves and drives list_controls + get_family_bundle."""
    client = _soc2_cc6_client()
    request = _soc2_cc6_request(tmp_path, family_id="CC6")

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "soc2")),
    ):
        checkpoint = await prepare_campaign(client, request)

    assert set(checkpoint.items.keys()) == {"CC6.1", "CC6.2"}
    client.list_controls.assert_any_call("soc2", "CC6")
    client.get_family_bundle.assert_awaited_once_with("sys-1", "CC6", "soc2")


@pytest.mark.asyncio
async def test_prepare_campaign_resolves_soc2_mixed_case_family(tmp_path: Path) -> None:
    """Lowercase cc6 resolves to canonical CC6; resolved value flows to downstream calls."""
    client = _soc2_cc6_client()
    request = _soc2_cc6_request(tmp_path, family_id="cc6")

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "soc2")),
    ):
        checkpoint = await prepare_campaign(client, request)

    assert set(checkpoint.items.keys()) == {"CC6.1", "CC6.2"}
    client.list_controls.assert_any_call("soc2", "CC6")
    client.get_family_bundle.assert_awaited_once_with("sys-1", "CC6", "soc2")


@pytest.mark.asyncio
async def test_prepare_campaign_resolves_family_with_whitespace(tmp_path: Path) -> None:
    """' CC6 ' (whitespace) resolves to canonical CC6."""
    client = _soc2_cc6_client()
    request = _soc2_cc6_request(tmp_path, family_id=" CC6 ")

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "soc2")),
    ):
        checkpoint = await prepare_campaign(client, request)

    assert set(checkpoint.items.keys()) == {"CC6.1", "CC6.2"}
    client.list_controls.assert_any_call("soc2", "CC6")


@pytest.mark.asyncio
async def test_prepare_campaign_unknown_family_raises_with_available(tmp_path: Path) -> None:
    """Unknown family raises PretorianClientError with sorted available list + structured details."""
    client = _soc2_cc6_client()
    request = _soc2_cc6_request(tmp_path, family_id="CCX")

    with (
        patch(
            "pretorin.workflows.campaign.resolve_execution_context",
            AsyncMock(return_value=("sys-1", "soc2")),
        ),
        pytest.raises(PretorianClientError) as exc_info,
    ):
        await prepare_campaign(client, request)

    err = exc_info.value
    assert "'CCX'" in err.message
    assert "CC1" in err.message and "CC6" in err.message and "PI1" in err.message
    # Both CLI and MCP discovery pointers appear in the message
    assert "pretorin frameworks families soc2" in err.message
    assert "pretorin_list_control_families" in err.message
    assert err.details["framework_id"] == "soc2"
    assert err.details["requested_family_id"] == "CCX"
    assert err.details["available_families"] == ["CC1", "CC6", "PI1"]
    # Structured discovery payload for MCP agents
    assert err.details["discovery"] == {
        "cli": "pretorin frameworks families soc2",
        "mcp_tool": "pretorin_list_control_families",
    }


@pytest.mark.asyncio
async def test_prepare_campaign_framework_with_no_families_raises(tmp_path: Path) -> None:
    """Framework with zero declared families raises an explicit error."""
    client = _soc2_cc6_client()
    client.list_control_families = AsyncMock(return_value=[])
    request = _soc2_cc6_request(tmp_path, family_id="CC6")

    with (
        patch(
            "pretorin.workflows.campaign.resolve_execution_context",
            AsyncMock(return_value=("sys-1", "soc2")),
        ),
        pytest.raises(PretorianClientError) as exc_info,
    ):
        await prepare_campaign(client, request)

    assert "declares no control families" in exc_info.value.message
    assert exc_info.value.details["available_families"] == []


@pytest.mark.asyncio
async def test_prepare_campaign_belt_and_suspenders_filters_client_side(tmp_path: Path) -> None:
    """When list_controls with family filter returns [], fall back to unfiltered + client-side filter."""
    client = _soc2_cc6_client(list_controls_return=[])

    # First call (filtered by family_id) returns []. Second call (unfiltered) returns
    # controls from multiple families. Only CC6 controls should survive.
    mixed_controls = [
        ControlSummary(id="CC1.1", title="Org Values", family_id="CC1"),
        ControlSummary(id="CC6.1", title="Logical Access Security", family_id="CC6"),
        ControlSummary(id="CC6.2", title="Access Provisioning", family_id="CC6"),
        ControlSummary(id="PI1.1", title="Processing Integrity", family_id="PI1"),
    ]
    client.list_controls = AsyncMock(side_effect=[[], mixed_controls])
    request = _soc2_cc6_request(tmp_path, family_id="cc6")

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "soc2")),
    ):
        checkpoint = await prepare_campaign(client, request)

    assert set(checkpoint.items.keys()) == {"CC6.1", "CC6.2"}
    assert client.list_controls.await_count == 2


def _nist_families() -> list[ControlFamilySummary]:
    """Shape matches the live fedramp-moderate / nist-800-53-r5 backend response:
    canonical id is the slugified title, class_type holds the natural abbreviation.
    """
    return [
        ControlFamilySummary(id="access-control", title="Access Control", controls_count=17, **{"class": "ac"}),
        ControlFamilySummary(
            id="system-and-communications-protection",
            title="System and Communications Protection",
            controls_count=19,
            **{"class": "sc"},
        ),
        ControlFamilySummary(
            id="identification-and-authentication",
            title="Identification and Authentication",
            controls_count=10,
            **{"class": "ia"},
        ),
    ]


@pytest.mark.asyncio
async def test_resolve_family_id_class_fallback_nist_abbreviation() -> None:
    """User-facing abbreviations (NIST 'AC') resolve to the canonical slug id via class fallback."""
    from pretorin.workflows.campaign import _resolve_family_id

    client = _mock_campaign_client()
    client.list_control_families = AsyncMock(return_value=_nist_families())

    for raw in ["AC", "ac", " Ac ", "SC", "IA"]:
        resolved = await _resolve_family_id(client, "fedramp-moderate", raw)
        expected = {
            "AC": "access-control",
            "ac": "access-control",
            " Ac ": "access-control",
            "SC": "system-and-communications-protection",
            "IA": "identification-and-authentication",
        }[raw]
        assert resolved == expected, f"{raw!r} resolved to {resolved!r}, expected {expected!r}"


@pytest.mark.asyncio
async def test_resolve_family_id_class_fallback_cmmc_suffix() -> None:
    """CMMC-style class abbreviations with suffixes ('AC-L2') resolve to their canonical id."""
    from pretorin.workflows.campaign import _resolve_family_id

    client = _mock_campaign_client()
    client.list_control_families = AsyncMock(
        return_value=[
            ControlFamilySummary(
                id="access-control-level-2",
                title="Access Control (Level 2)",
                controls_count=22,
                **{"class": "AC-L2"},
            ),
        ]
    )

    for raw in ["AC-L2", "ac-l2", "Ac-L2"]:
        resolved = await _resolve_family_id(client, "cmmc-l2", raw)
        assert resolved == "access-control-level-2"


@pytest.mark.asyncio
async def test_resolve_family_id_id_match_takes_precedence_over_class() -> None:
    """If the input matches both a family's id and another family's class, id wins."""
    from pretorin.workflows.campaign import _resolve_family_id

    # Contrived pathological case: one family has id='AC', another has class='AC'.
    # The id match should win (primary pass).
    client = _mock_campaign_client()
    client.list_control_families = AsyncMock(
        return_value=[
            ControlFamilySummary(id="access-control", title="Access Control", controls_count=17, **{"class": "ac"}),
            ControlFamilySummary(id="AC", title="Edge Case", controls_count=1, **{"class": "other"}),
        ]
    )

    resolved = await _resolve_family_id(client, "weird-fw", "AC")
    assert resolved == "AC"  # id match wins over class="ac" match


@pytest.mark.asyncio
async def test_resolve_family_id_null_class_is_skipped_gracefully() -> None:
    """SOC 2 families have class=None; that must not raise when the class fallback runs."""
    from pretorin.workflows.campaign import _resolve_family_id

    client = _mock_campaign_client()
    # SOC 2-shaped: class is None on the model.
    client.list_control_families = AsyncMock(
        return_value=[
            ControlFamilySummary(id="CC6", title="Logical Access", controls_count=8, class_type=None),
        ]
    )

    # Exact id match still works
    assert await _resolve_family_id(client, "soc2", "CC6") == "CC6"
    # Miss still errors cleanly (doesn't crash on None in class fallback)
    with pytest.raises(PretorianClientError, match="Unknown family"):
        await _resolve_family_id(client, "soc2", "ZZZ")


@pytest.mark.asyncio
async def test_resolve_family_id_empty_input_raises() -> None:
    """Defensive branch: direct call to _resolve_family_id with empty input raises."""
    from pretorin.workflows.campaign import _resolve_family_id

    client = _mock_campaign_client()
    client.list_control_families = AsyncMock(return_value=[])

    with pytest.raises(PretorianClientError) as exc_info:
        await _resolve_family_id(client, "soc2", "")

    assert "cannot be empty" in exc_info.value.message
    assert exc_info.value.details == {"framework_id": "soc2"}
    # list_control_families should not be called when input is empty
    client.list_control_families.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_family_id_whitespace_only_raises() -> None:
    """' \\t\\n ' should be treated as empty after strip."""
    from pretorin.workflows.campaign import _resolve_family_id

    client = _mock_campaign_client()
    client.list_control_families = AsyncMock(return_value=[])

    with pytest.raises(PretorianClientError) as exc_info:
        await _resolve_family_id(client, "soc2", "  \t\n  ")

    assert "cannot be empty" in exc_info.value.message
    client.list_control_families.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_campaign_preserves_raw_family_id_on_request(tmp_path: Path) -> None:
    """Raw user input on request.family_id is not mutated by the resolver (checkpoint determinism)."""
    client = _soc2_cc6_client()
    request = _soc2_cc6_request(tmp_path, family_id="cc6")

    with patch(
        "pretorin.workflows.campaign.resolve_execution_context",
        AsyncMock(return_value=("sys-1", "soc2")),
    ):
        await prepare_campaign(client, request)

    assert request.family_id == "cc6"


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
