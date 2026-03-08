"""Shared AI drafting workflows for compliance artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.utils import normalize_control_id
from pretorin.workflows.compliance_updates import resolve_system


def _strip_json_fence(text: str) -> str:
    """Remove optional fenced-code wrappers from agent JSON responses."""
    stripped = text.strip()
    if stripped.startswith("```json"):
        stripped = stripped[7:]
    elif stripped.startswith("```"):
        stripped = stripped[3:]
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Parse a JSON object from a model response, tolerating surrounding prose."""
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


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _dict_list(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    results: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        results.append({str(key): str(val) for key, val in item.items() if val is not None})
    return results


def _build_generation_task(system_id: str, system_name: str, framework_id: str, control_id: str) -> str:
    """Create a tightly-scoped drafting task for the Codex agent."""
    return (
        f"Draft compliance artifacts for system {system_name} ({system_id}), "
        f"framework {framework_id}, control {control_id}.\n\n"
        "Use Pretorin tools first to read current control context, current narrative, evidence, and notes. "
        "Do not write anything back to the platform. Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "narrative_draft": "<auditor-ready markdown>",\n'
        '  "evidence_gap_assessment": "<auditor-ready markdown>",\n'
        '  "recommended_notes": ["<canonical gap note>", "..."],\n'
        '  "evidence_recommendations": [\n'
        '    {"name": "<short title>", "evidence_type": "<policy_document|configuration|...>", '
        '"description": "<auditor-ready markdown>"}\n'
        "  ]\n"
        "}\n\n"
        "Requirements:\n"
        "- Use only observable facts from Pretorin tools and mark unknowns explicitly.\n"
        "- Use zero-padded control IDs (for example, ac-02).\n"
        "- The narrative_draft must be auditor-ready markdown with no headings, at least two rich elements, "
        "and at least one structural element.\n"
        "- The evidence_gap_assessment must be auditor-ready markdown and include at least one table or list.\n"
        "- If important narrative details are missing, include the exact [[PRETORIN_TODO]] block format.\n"
        "- Each recommended note must use the exact Gap/Observed/Missing/Why missing/Manual next step format.\n"
        "- Each evidence_recommendations.description must contain at least one rich markdown element and no headings."
    )


async def draft_control_artifacts(
    client: PretorianClient,
    *,
    system: str,
    framework_id: str,
    control_id: str,
    working_directory: Path | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """Generate read-only narrative and evidence-gap drafts for a control."""
    from pretorin.agent.codex_agent import CodexAgent

    normalized_control_id = normalize_control_id(control_id)
    system_id, system_name = await resolve_system(client, system)

    try:
        agent = CodexAgent(model=model)
        result = await agent.run(
            task=_build_generation_task(system_id, system_name, framework_id, normalized_control_id),
            working_directory=working_directory,
            skill="narrative-generation",
            stream=False,
        )
    except RuntimeError as exc:
        raise PretorianClientError(str(exc)) from exc

    payload = _extract_json_object(result.response)
    response: dict[str, Any] = {
        "system_id": system_id,
        "system_name": system_name,
        "framework_id": framework_id,
        "control_id": normalized_control_id,
        "raw_response": result.response,
        "parse_status": "raw_fallback",
        "narrative_draft": None,
        "evidence_gap_assessment": None,
        "recommended_notes": [],
        "evidence_recommendations": [],
    }
    if payload is None:
        return response

    response.update(
        {
            "parse_status": "json",
            "narrative_draft": payload.get("narrative_draft"),
            "evidence_gap_assessment": payload.get("evidence_gap_assessment"),
            "recommended_notes": _string_list(payload.get("recommended_notes")),
            "evidence_recommendations": _dict_list(payload.get("evidence_recommendations")),
        }
    )
    return response
