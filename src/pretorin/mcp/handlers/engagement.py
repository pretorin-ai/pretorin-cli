"""MCP handler for ``pretorin_start_task`` — the engagement entry point.

Per the recipe-implementation design's WS0: the calling agent extracts
entities from the user prompt, pretorin runs deterministic rules over
them, the result is an ``EngagementSelection`` that names the workflow.
No LLM in pretorin during this call — entity extraction is the calling
agent's job.

Three response shapes:

1. **MCP error** — hard cross-check failure (hallucinated entity).
2. **EngagementSelection (routed)** — ``selected_workflow`` set, calling
   agent reads the workflow body and follows it.
3. **EngagementSelection (ambiguous)** — coherence problem the calling
   agent surfaces to the user before retrying.
"""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from pretorin.client import PretorianClient
from pretorin.engagement.cross_check import cross_check_entities
from pretorin.engagement.entities import EngagementEntities
from pretorin.engagement.inspect import gather_inspect_summary
from pretorin.engagement.rules import select_workflow
from pretorin.engagement.selection import EngagementSelection
from pretorin.mcp.helpers import format_error, format_json, safe_args

logger = logging.getLogger(__name__)


async def handle_start_task(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Route a user prompt to a workflow.

    Inputs (all under ``entities``):
    - ``intent_verb`` (required): one of work_on / collect_evidence /
      draft_narrative / answer / campaign / inspect_status.
    - ``raw_prompt`` (required): the user's verbatim prompt for audit.
    - ``system_id`` / ``framework_id`` / ``control_ids`` /
      ``scope_question_ids`` / ``policy_question_ids`` (all optional).

    Optional top-level args:
    - ``active_system_id`` — caller's CLI context system. When set and
      different from the resolved system, the response is ambiguous so
      the calling agent surfaces cross-system intent.
    - ``skip_inspect`` (default false) — skip the server-side platform
      reads. Use when the calling agent already has fresh state.

    Returns a JSON ``EngagementSelection``. Hard cross-check failures
    surface as MCP errors so the calling agent sees the failure mode.
    """
    logger.debug("handle_start_task called with %s", safe_args(arguments))

    entities_input = arguments.get("entities")
    if not isinstance(entities_input, dict):
        return format_error(
            "Argument 'entities' is required and must be an object with at least intent_verb and raw_prompt."
        )

    try:
        entities = EngagementEntities.model_validate(entities_input)
    except ValidationError as exc:
        return format_error(f"entities failed schema validation: {exc}")

    active_system_id = arguments.get("active_system_id")
    if active_system_id is not None and not isinstance(active_system_id, str):
        return format_error("active_system_id must be a string when provided")

    skip_inspect = bool(arguments.get("skip_inspect", False))

    # Cross-check the entities against platform state before routing.
    cross_check = await cross_check_entities(client, entities, active_system_id=active_system_id)

    if cross_check.has_hard_error:
        return format_error("; ".join(cross_check.hard_errors))

    # Inspect the system/framework state — best-effort, never fails the
    # call. Skipped only when the caller explicitly opts out.
    if skip_inspect:
        inspect_summary: dict[str, Any] = {"skipped": True}
    else:
        inspect_summary = await gather_inspect_summary(
            client,
            system_id=cross_check.resolved_system_id or entities.system_id,
            framework_id=cross_check.resolved_framework_id or entities.framework_id,
        )

    # Apply the routing rules.
    selection = select_workflow(entities, inspect_summary)

    # If the cross-check found ambiguities (cross-system, wrong-framework,
    # control-in-wrong-framework), override the rule-matched outcome with
    # an ambiguous response so the calling agent asks the user to confirm
    # before any writes happen.
    if cross_check.has_ambiguity:
        selection = EngagementSelection(
            entities=entities,
            inspect_summary=inspect_summary,
            selected_workflow=None,
            workflow_params={},
            rule_matched="",
            ambiguous=True,
            ambiguity_reason=" | ".join(cross_check.ambiguities),
        )

    return format_json(selection.model_dump())


__all__ = ["handle_start_task"]
