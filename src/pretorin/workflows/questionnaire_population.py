"""Shared AI workflows for stateful scope and policy questionnaire population."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pretorin.agent.codex_agent import CodexAgent
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.client.models import OrgPolicyQuestionnaireResponse


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    candidate = _strip_json_fence(text)
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        parsed = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _build_task(
    *,
    workflow_name: str,
    subject_label: str,
    handoff_message: str,
    state_payload: dict[str, Any],
) -> str:
    payload_json = json.dumps(state_payload, indent=2, sort_keys=True)
    return (
        f"You are helping populate persisted Pretorin {workflow_name} questionnaire answers.\n\n"
        f"Subject: {subject_label}\n\n"
        "You are NOT generating the final document. Your task is only to propose "
        "questionnaire answer updates based on observable facts from the current workspace.\n\n"
        "Rules:\n"
        "- Read the current workspace and use only observable facts.\n"
        "- Start from the existing saved answers and improve or fill gaps where supported.\n"
        "- If a question cannot be answered confidently from the workspace, leave proposed_answer null.\n"
        "- Do not invent organizational facts, names, counts, systems, approvals, or policies.\n"
        "- Keep answers concise and practical. Bullet-point style is fine.\n"
        "- Preserve useful existing answers when the workspace does not contradict them.\n"
        "- Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "questions": [\n'
        "    {\n"
        '      "question_id": "<id>",\n'
        '      "proposed_answer": "<string or null>",\n'
        '      "confidence": "high|medium|low",\n'
        '      "evidence_summary": "<short explanation of what in the workspace supports the answer>",\n'
        '      "needs_manual_input": true,\n'
        '      "manual_input_reason": "<why a human still needs to answer>"\n'
        "    }\n"
        "  ],\n"
        '  "summary": "<short overall summary>"\n'
        "}\n\n"
        f"After the questionnaire is saved, {handoff_message}\n\n"
        "Questionnaire state:\n"
        f"{payload_json}"
    )


async def _run_questionnaire_population(
    *,
    task: str,
    working_directory: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    try:
        agent = CodexAgent(model=model)
        result = await agent.run(
            task=task,
            working_directory=working_directory,
            stream=False,
        )
    except RuntimeError as exc:
        raise PretorianClientError(str(exc)) from exc

    payload = _extract_json_object(result.response)
    if payload is None:
        return {
            "parse_status": "raw_fallback",
            "raw_response": result.response,
            "summary": None,
            "questions": [],
        }

    questions = payload.get("questions")
    return {
        "parse_status": "json",
        "raw_response": result.response,
        "summary": payload.get("summary"),
        "questions": questions if isinstance(questions, list) else [],
    }


async def draft_scope_questionnaire(
    client: PretorianClient,
    *,
    system_id: str,
    framework_id: str,
    working_directory: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Draft scope questionnaire updates from the current workspace."""
    system = await client.get_system(system_id)
    scope = await client.get_scope(system_id, framework_id)
    task = _build_task(
        workflow_name="scope",
        subject_label=f"{system.name} / {framework_id}",
        handoff_message=(
            "the user should return to the Pretorin platform scope page "
            "to run review and generate the scope document."
        ),
        state_payload={
            "system_id": system_id,
            "system_name": system.name,
            "framework_id": framework_id,
            "questions": [question.model_dump(mode="json") for question in scope.scope_questions],
            "existing_answers": scope.scope_qa_responses or {"questions": []},
            "persisted_review": (
                scope.scope_review.model_dump(mode="json") if scope.scope_review else None
            ),
            "persisted_reviewed_at": scope.scope_reviewed_at,
        },
    )
    return await _run_questionnaire_population(
        task=task,
        working_directory=working_directory,
        model=model,
    )


async def draft_policy_questionnaire(
    client: PretorianClient,
    *,
    questionnaire: OrgPolicyQuestionnaireResponse,
    working_directory: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Draft org-policy questionnaire updates from the current workspace."""
    template = questionnaire.template.model_dump(mode="json") if questionnaire.template else None
    task = _build_task(
        workflow_name="policy",
        subject_label=f"{questionnaire.name} ({questionnaire.policy_id})",
        handoff_message=(
            "the user should return to the Pretorin platform policy page "
            "to review findings and generate the final policy document."
        ),
        state_payload={
            "policy_id": questionnaire.policy_id,
            "policy_name": questionnaire.name,
            "policy_template_id": questionnaire.policy_template_id,
            "template": template,
            "existing_answers": questionnaire.policy_qa_responses or {"questions": []},
            "persisted_review": (
                questionnaire.policy_review.model_dump(mode="json")
                if questionnaire.policy_review
                else None
            ),
            "persisted_reviewed_at": questionnaire.policy_reviewed_at,
        },
    )
    return await _run_questionnaire_population(
        task=task,
        working_directory=working_directory,
        model=model,
    )
