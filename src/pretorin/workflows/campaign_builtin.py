"""Optional builtin executor for campaign runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.workflows.ai_generation import draft_control_artifacts
from pretorin.workflows.campaign import (
    CampaignItem,
    CampaignItemState,
    CampaignPresenter,
    CampaignRunRequest,
    CampaignRunSummary,
    WorkflowContextSnapshot,
    execute_campaign_with_provider,
)
from pretorin.workflows.questionnaire_population import draft_policy_questionnaire, draft_scope_questionnaire


async def _draft_control_fix(
    client: PretorianClient,
    *,
    system_id: str,
    framework_id: str,
    control_id: str,
    instruction_block: str,
    working_directory: Path,
) -> dict[str, Any]:
    from pretorin.agent.codex_agent import CodexAgent
    from pretorin.mcp.helpers import VALID_EVIDENCE_TYPES
    from pretorin.workflows.ai_generation import _dict_list, _extract_json_object, _string_list

    context = await client.get_control_context(system_id, control_id, framework_id)
    implementation = await client.get_control_implementation(system_id, control_id, framework_id)
    notes = await client.list_control_notes(system_id, control_id, framework_id)
    evidence = await client.list_evidence(system_id, framework_id, control_id=control_id, limit=50)
    enum_list = "|".join(sorted(VALID_EVIDENCE_TYPES))
    task = (
        f"Update control {control_id} for system {system_id} in framework {framework_id}.\n\n"
        "You are remediating existing platform workflow findings or notes. "
        "Read the provided control context, current implementation, notes, and evidence. "
        "Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "narrative_draft": "<auditor-ready markdown or null>",\n'
        '  "evidence_gap_assessment": "<markdown or null>",\n'
        '  "recommended_notes": ["<plain text note>", "..."],\n'
        '  "evidence_recommendations": [\n'
        '    {"name": "<short title>", "evidence_type": "'
        + f"<{enum_list}>"
        + '", "description": "<auditor-ready markdown>"}\n'
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "- An empty evidence_recommendations list is a valid and expected result when no observable "
        "workspace artifact supports this control. Use recommended_notes to describe each unverified gap "
        "rather than fabricating evidence to fill the shape.\n\n"
        "Instructions:\n"
        f"{instruction_block}\n\n"
        "Control context JSON:\n"
        f"{json.dumps(context.model_dump(mode='json'), indent=2)}\n\n"
        "Implementation JSON:\n"
        f"{json.dumps(implementation.model_dump(mode='json'), indent=2)}\n\n"
        "Notes JSON:\n"
        f"{json.dumps(notes, indent=2, default=str)}\n\n"
        "Evidence JSON:\n"
        f"{json.dumps([item.model_dump(mode='json') for item in evidence], indent=2)}"
    )
    try:
        agent = CodexAgent()
        result = await agent.run(
            task=task,
            working_directory=working_directory,
            skill="narrative-generation",
            stream=False,
        )
    except RuntimeError as exc:
        raise PretorianClientError(str(exc)) from exc
    payload = _extract_json_object(result.response)
    if payload is None:
        return {
            "parse_status": "raw_fallback",
            "raw_response": result.response,
            "narrative_draft": None,
            "evidence_gap_assessment": None,
            "recommended_notes": [],
            "evidence_recommendations": [],
        }
    return {
        "parse_status": "json",
        "raw_response": result.response,
        "narrative_draft": payload.get("narrative_draft"),
        "evidence_gap_assessment": payload.get("evidence_gap_assessment"),
        "recommended_notes": _string_list(payload.get("recommended_notes")),
        "evidence_recommendations": _dict_list(payload.get("evidence_recommendations")),
    }


async def _builtin_proposal_provider(
    client: PretorianClient,
    request: CampaignRunRequest,
    item: CampaignItem,
    item_state: CampaignItemState,
    snapshot: WorkflowContextSnapshot,
) -> dict[str, Any]:
    if request.domain == "controls":
        system_id = str(snapshot.scope["system_id"])
        framework_id = str(snapshot.scope["framework_id"])
        if request.mode == "initial":
            return await draft_control_artifacts(
                client,
                system=system_id,
                framework_id=framework_id,
                control_id=item.item_id,
                working_directory=request.working_directory,
            )
        if request.mode == "notes-fix":
            notes = await client.list_control_notes(system_id, item.item_id, framework_id)
            note_block = "\n".join(f"- {note.get('content', '')}" for note in notes)
            return await _draft_control_fix(
                client,
                system_id=system_id,
                framework_id=framework_id,
                control_id=item.item_id,
                instruction_block=f"Address these platform notes:\n{note_block}",
                working_directory=request.working_directory,
            )
        findings_map = snapshot.extras.get("review_findings", {})
        findings = findings_map.get(item.item_id, [])
        instruction_block = "Address these family review findings:\n" + json.dumps(findings, indent=2, default=str)
        return await _draft_control_fix(
            client,
            system_id=system_id,
            framework_id=framework_id,
            control_id=item.item_id,
            instruction_block=instruction_block,
            working_directory=request.working_directory,
        )

    if request.domain == "policy":
        questionnaire = await client.get_org_policy_questionnaire(item.item_id)
        return await draft_policy_questionnaire(
            client,
            questionnaire=questionnaire,
            working_directory=request.working_directory,
        )

    system_id = str(snapshot.scope["system_id"])
    framework_id = str(snapshot.scope["framework_id"])
    return await draft_scope_questionnaire(
        client,
        system_id=system_id,
        framework_id=framework_id,
        working_directory=request.working_directory,
    )


async def execute_prepared_campaign(
    client: PretorianClient,
    checkpoint_path: Path,
    *,
    presenter: CampaignPresenter | None = None,
) -> CampaignRunSummary:
    """Execute a prepared campaign using Pretorin's builtin Codex backend."""
    return await execute_campaign_with_provider(
        client,
        checkpoint_path,
        proposal_provider=_builtin_proposal_provider,
        presenter=presenter,
        lease_owner="builtin-codex",
    )
