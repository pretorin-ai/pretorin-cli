"""Handlers for agentic workflow tools (workflow state, scope, policy, family, analytics)."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import (
    format_error,
    format_json,
    require,
)

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
