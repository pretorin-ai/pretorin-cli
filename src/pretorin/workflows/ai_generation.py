"""Shared AI drafting workflows for compliance artifacts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from pretorin.cli.context import resolve_execution_context
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.client.config import Config
from pretorin.utils import normalize_control_id

logger = logging.getLogger(__name__)


async def _ensure_org_model_cached(client: PretorianClient) -> None:
    """Fetch the org's CLI model from the platform and cache it on Config.

    This is a best-effort call — if it fails (e.g. no API token, network
    error, old server without the endpoint), we silently fall back to the
    local config / default.
    """
    config = Config()
    if config._org_cli_model is not None:
        return  # already cached this session
    try:
        data = await client.get_org_ai_settings()
        cli_model = data.get("cli_model")
        if cli_model:
            config.set_org_cli_model(cli_model)
            logger.debug("Using org CLI model from platform: %s", cli_model)
    except Exception:
        logger.debug("Could not fetch org AI settings, using local config")


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
    from pretorin.mcp.helpers import VALID_EVIDENCE_TYPES

    enum_list = "|".join(sorted(VALID_EVIDENCE_TYPES))
    return (
        f"Draft compliance artifacts for system {system_name} ({system_id}), "
        f"framework {framework_id}, control {control_id}.\n\n"
        "Step 1 — Read current platform state via Pretorin tools: control context, current narrative, "
        "evidence, and notes.\n"
        "Step 2 — Actively explore the working directory for concrete artifacts that back this control. "
        "Grep for relevant config keys, read modules and docs, inspect CI/CD files. Do NOT skip this step; "
        "an empty evidence_recommendations list is only valid AFTER you have searched the workspace and "
        "found nothing. Platform state alone is not enough to conclude the workspace is empty.\n"
        "Step 3 — Draft artifacts. Do not write anything back to the platform. "
        "Return ONLY valid JSON with this exact shape:\n"
        "{\n"
        '  "narrative_draft": "<auditor-ready markdown>",\n'
        '  "evidence_gap_assessment": "<auditor-ready markdown>",\n'
        '  "recommended_notes": ["<canonical gap note>", "..."],\n'
        '  "evidence_recommendations": [\n'
        '    {"name": "<short title>", "evidence_type": "'
        + f"<{enum_list}>"
        + '", "description": "<auditor-ready markdown>", '
        '"code_file_path": "<path/to/file or null>", '
        '"code_line_numbers": "<start-end or null>", '
        '"code_snippet": "<relevant excerpt or null>"}\n'
        "  ]\n"
        "}\n\n"
        "Requirements:\n"
        "- Use only observable facts from Pretorin tools and the workspace. Mark unknowns explicitly.\n"
        "- Use zero-padded control IDs (for example, ac-02).\n"
        "- The narrative_draft must be auditor-ready markdown with no headings, at least two rich elements, "
        "and at least one structural element.\n"
        "- The evidence_gap_assessment must be auditor-ready markdown and include at least one table or list.\n"
        "- If important narrative details are missing, include the exact [[PRETORIN_TODO]] block format.\n"
        "- Each recommended note must use the exact Gap/Observed/Missing/Why missing/Manual next step format.\n"
        "- Each evidence_recommendations.description must contain at least one rich markdown element and no headings.\n"
        f"- evidence_type is REQUIRED on every evidence_recommendations entry and must be exactly one of: {enum_list}. "
        "If you cannot pick a type, omit the entry and describe the gap in recommended_notes instead.\n"
        "- When evidence is found in a workspace file, set code_file_path to the file path relative to "
        "the workspace root, code_line_numbers to the relevant line range (e.g. '42-67'), and code_snippet "
        "to the relevant excerpt. These fields are optional but strongly preferred for traceability.\n"
        "- An empty evidence_recommendations list is a valid and expected result ONLY after Step 2 confirms "
        "no observable workspace artifact supports this control. Describe every unverified gap in "
        "recommended_notes instead of fabricating evidence to fill the shape."
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

    # Pre-fetch org model setting so CodexAgent picks it up via Config
    if model is None:
        await _ensure_org_model_cached(client)

    normalized_control_id = normalize_control_id(control_id)
    system_id, resolved_framework_id = await resolve_execution_context(
        client,
        system=system,
        framework=framework_id,
    )
    system_name = (await client.get_system(system_id)).name

    try:
        agent = CodexAgent(model=model)
        result = await agent.run(
            task=_build_generation_task(
                system_id,
                system_name,
                resolved_framework_id,
                normalized_control_id,
            ),
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
        "framework_id": resolved_framework_id,
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
