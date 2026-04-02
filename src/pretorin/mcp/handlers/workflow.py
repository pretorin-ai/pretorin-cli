"""Handlers for agentic workflow tools (workflow state, scope, policy, family, analytics)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.mcp.helpers import (
    format_error,
    format_json,
    require,
)
from pretorin.workflows.campaign import (
    apply_campaign,
    claim_campaign_items,
    get_campaign_item_context,
    get_campaign_status,
    prepare_campaign,
    submit_campaign_proposal,
)
from pretorin.workflows.campaign_protocol import build_campaign_request_from_mapping

logger = logging.getLogger(__name__)


# === Workflow State ===


async def handle_get_workflow_state(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_workflow_state tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.get_workflow_state(arguments["system_id"], arguments["framework_id"]))


# === Scope Questions ===


async def handle_get_pending_scope_questions(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_pending_scope_questions tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.get_pending_scope_questions(arguments["system_id"], arguments["framework_id"]))


async def handle_get_scope_question_detail(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_scope_question_detail tool."""
    err = require(arguments, "system_id", "question_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(
        await client.get_scope_question_detail(
            arguments["system_id"], arguments["question_id"], arguments["framework_id"]
        )
    )


async def handle_answer_scope_question(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the answer_scope_question tool."""
    err = require(arguments, "system_id", "question_id", "answer", "framework_id")
    if err:
        return format_error(err)
    return format_json(
        await client.answer_scope_question(
            arguments["system_id"],
            arguments["question_id"],
            arguments["answer"],
            arguments["framework_id"],
        )
    )


async def handle_trigger_scope_generation(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the trigger_scope_generation tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.trigger_scope_generation(arguments["system_id"], arguments["framework_id"]))


async def handle_trigger_scope_review(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the trigger_scope_review tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.trigger_scope_review(arguments["system_id"], arguments["framework_id"]))


async def handle_get_scope_review_results(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_scope_review_results tool."""
    err = require(arguments, "system_id", "job_id")
    if err:
        return format_error(err)
    return format_json(await client.get_scope_review_results(arguments["system_id"], arguments["job_id"]))


# === Policy Questions ===


async def handle_get_pending_policy_questions(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_pending_policy_questions tool."""
    err = require(arguments, "policy_id")
    if err:
        return format_error(err)
    return format_json(await client.get_pending_policy_questions(arguments["policy_id"]))


async def handle_get_policy_question_detail(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_policy_question_detail tool."""
    err = require(arguments, "policy_id", "question_id")
    if err:
        return format_error(err)
    return format_json(await client.get_policy_question_detail(arguments["policy_id"], arguments["question_id"]))


async def handle_answer_policy_question(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the answer_policy_question tool."""
    err = require(arguments, "policy_id", "question_id", "answer")
    if err:
        return format_error(err)
    return format_json(
        await client.answer_policy_question(arguments["policy_id"], arguments["question_id"], arguments["answer"])
    )


async def handle_trigger_policy_generation(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the trigger_policy_generation tool."""
    err = require(arguments, "policy_id")
    if err:
        return format_error(err)
    return format_json(
        await client.trigger_policy_generation(arguments["policy_id"], system_id=arguments.get("system_id"))
    )


async def handle_trigger_policy_review(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the trigger_policy_review tool."""
    err = require(arguments, "policy_id")
    if err:
        return format_error(err)
    return format_json(await client.trigger_policy_review(arguments["policy_id"]))


async def handle_get_policy_review_results(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_policy_review_results tool."""
    err = require(arguments, "policy_id", "job_id")
    if err:
        return format_error(err)
    return format_json(await client.get_policy_review_results(arguments["policy_id"], arguments["job_id"]))


async def handle_get_policy_workflow_state(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_policy_workflow_state tool."""
    err = require(arguments, "policy_id")
    if err:
        return format_error(err)
    return format_json(await client.get_policy_workflow_state(arguments["policy_id"]))


# === Family Tools ===


async def handle_get_pending_families(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_pending_families tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.get_pending_families(arguments["system_id"], arguments["framework_id"]))


async def handle_get_family_bundle(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_family_bundle tool."""
    err = require(arguments, "system_id", "family_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(
        await client.get_family_bundle(arguments["system_id"], arguments["family_id"], arguments["framework_id"])
    )


async def handle_trigger_family_review(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the trigger_family_review tool."""
    err = require(arguments, "system_id", "family_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(
        await client.trigger_family_review(arguments["system_id"], arguments["family_id"], arguments["framework_id"])
    )


async def handle_get_family_review_results(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_family_review_results tool."""
    err = require(arguments, "system_id", "job_id")
    if err:
        return format_error(err)
    return format_json(await client.get_family_review_results(arguments["system_id"], arguments["job_id"]))


# === Analytics ===


async def handle_get_analytics_summary(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_analytics_summary tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.get_analytics_summary(arguments["system_id"], arguments["framework_id"]))


async def handle_prepare_campaign(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Prepare a campaign for external or builtin execution."""
    try:
        request = build_campaign_request_from_mapping(arguments)
    except ValueError as exc:
        raise PretorianClientError(str(exc)) from exc
    checkpoint = await prepare_campaign(client, request)
    summary = get_campaign_status(request.checkpoint_path)
    return format_json(
        {
            "checkpoint_path": str(request.checkpoint_path),
            "normalized_request": request.to_dict(),
            "workflow_snapshot": checkpoint.workflow_snapshot,
            "summary": summary.to_dict(),
        }
    )


async def handle_claim_campaign_items(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Claim prepared campaign items for drafting."""
    del client
    err = require(arguments, "checkpoint_path")
    if err:
        return format_error(err)
    result = claim_campaign_items(
        Path(str(arguments["checkpoint_path"])).expanduser().resolve(),
        max_items=int(arguments.get("max_items", 1)),
        lease_owner=str(arguments.get("lease_owner", "external-agent")),
        lease_ttl_seconds=int(arguments.get("lease_ttl_seconds", 300)),
    )
    return format_json(result)


async def handle_get_campaign_item_context(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Fetch full item context plus drafting instructions."""
    err = require(arguments, "checkpoint_path", "item_id")
    if err:
        return format_error(err)
    result = await get_campaign_item_context(
        client,
        Path(str(arguments["checkpoint_path"])).expanduser().resolve(),
        item_id=str(arguments["item_id"]),
    )
    return format_json(result)


async def handle_submit_campaign_proposal(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Persist one campaign proposal."""
    del client
    err = require(arguments, "checkpoint_path", "item_id", "proposal")
    if err:
        return format_error(err)
    proposal = arguments["proposal"]
    if not isinstance(proposal, dict):
        return format_error("proposal must be a JSON object")
    result = submit_campaign_proposal(
        Path(str(arguments["checkpoint_path"])).expanduser().resolve(),
        item_id=str(arguments["item_id"]),
        proposal=proposal,
    )
    return format_json(result)


async def handle_apply_campaign(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Apply stored proposals back to platform workflow records."""
    err = require(arguments, "checkpoint_path")
    if err:
        return format_error(err)
    item_ids = arguments.get("item_ids")
    if item_ids is not None and not isinstance(item_ids, list):
        return format_error("item_ids must be a list of item ids when provided")
    summary = await apply_campaign(
        client,
        Path(str(arguments["checkpoint_path"])).expanduser().resolve(),
        item_ids=[str(item) for item in item_ids] if isinstance(item_ids, list) else None,
    )
    return format_json(summary.to_dict())


async def handle_get_campaign_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Return structured campaign status and a stable transcript snapshot."""
    del client
    err = require(arguments, "checkpoint_path")
    if err:
        return format_error(err)
    summary = get_campaign_status(Path(str(arguments["checkpoint_path"])).expanduser().resolve())
    return format_json(summary.to_dict())


async def handle_get_family_analytics(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_family_analytics tool."""
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    return format_json(await client.get_family_analytics(arguments["system_id"], arguments["framework_id"]))


async def handle_get_policy_analytics(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_policy_analytics tool."""
    err = require(arguments, "policy_id")
    if err:
        return format_error(err)
    return format_json(await client.get_policy_analytics(arguments["policy_id"]))
