"""Handlers for compliance workflow tools (narratives, notes, status, monitoring, artifacts)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.mcp.helpers import (
    VALID_CONTROL_STATUSES,
    VALID_EVENT_TYPES,
    VALID_SEVERITIES,
    format_error,
    format_json,
    require,
    resolve_execution_scope,
    resolve_system_id,
    validate_enum,
)
from pretorin.utils import normalize_control_id
from pretorin.workflows.ai_generation import draft_control_artifacts

logger = logging.getLogger(__name__)


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments with sensitive fields redacted."""
    return {k: ("***" if k == "api_key" else v) for k, v in arguments.items()}


async def handle_generate_control_artifacts(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle read-only AI drafting for control narratives and evidence gaps."""
    logger.debug("handle_generate_control_artifacts called with %s", _safe_args(arguments))
    err = require(arguments, "system_id", "control_id", "framework_id")
    if err:
        return format_error(err)

    result = await draft_control_artifacts(
        client,
        system=arguments["system_id"],
        framework_id=arguments["framework_id"],
        control_id=arguments["control_id"],
        working_directory=Path(arguments["working_directory"]) if arguments.get("working_directory") else None,
        model=arguments.get("model"),
    )
    return format_json(result)


async def handle_push_monitoring_event(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the push_monitoring_event tool."""
    logger.debug("handle_push_monitoring_event called with %s", _safe_args(arguments))
    err = require(arguments, "title")
    if err:
        return format_error(err)

    from pretorin.client.models import MonitoringEventCreate

    event_type = arguments.get("event_type", "security_scan")
    severity = arguments.get("severity", "medium")
    enum_err = validate_enum(event_type, VALID_EVENT_TYPES, "event_type")
    if enum_err:
        return format_error(enum_err)
    enum_err = validate_enum(severity, VALID_SEVERITIES, "severity")
    if enum_err:
        return format_error(enum_err)

    system_id, framework_id, normalized_control_id = await resolve_execution_scope(client, arguments)
    event = MonitoringEventCreate(
        event_type=event_type,
        title=arguments["title"],
        description=arguments.get("description", ""),
        severity=severity,
        control_id=normalized_control_id,
        framework_id=framework_id,
        event_data={"source": "cli"},
    )
    result = await client.create_monitoring_event(
        system_id=system_id,
        event=event,
    )
    return format_json(result)


async def handle_get_control_context(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_context tool."""
    logger.debug("handle_get_control_context called with %s", _safe_args(arguments))
    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        control_required=True,
    )
    ctx = await client.get_control_context(
        system_id=system_id,
        control_id=normalized_control_id or "",
        framework_id=framework_id,
    )
    return format_json(ctx.model_dump())


async def handle_get_scope(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_scope tool."""
    logger.debug("handle_get_scope called with %s", _safe_args(arguments))
    err = require(arguments, "system_id", "framework_id")
    if err:
        return format_error(err)
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    scope = await client.get_scope(
        system_id=system_id,
        framework_id=arguments["framework_id"],
    )
    return format_json(scope.model_dump())


async def handle_add_control_note(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the add_control_note tool."""
    logger.debug("handle_add_control_note called with %s", _safe_args(arguments))
    err = require(arguments, "system_id", "control_id", "framework_id", "content")
    if err:
        return format_error(err)

    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    result = await client.add_control_note(
        system_id=system_id,
        control_id=normalize_control_id(arguments["control_id"]),
        content=arguments["content"],
        framework_id=arguments["framework_id"],
        source="cli",
    )
    return format_json(result)


async def handle_get_control_notes(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_notes tool."""
    logger.debug("handle_get_control_notes called with %s", _safe_args(arguments))
    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        control_required=True,
    )
    notes = await client.list_control_notes(
        system_id=system_id,
        control_id=normalized_control_id or "",
        framework_id=framework_id,
    )
    return format_json(
        {
            "control_id": normalized_control_id,
            "system_id": system_id,
            "framework_id": framework_id,
            "total": len(notes),
            "notes": notes,
        }
    )


async def handle_update_narrative(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the update_narrative tool."""
    logger.debug("handle_update_narrative called with %s", _safe_args(arguments))
    err = require(arguments, "system_id", "control_id", "framework_id", "narrative")
    if err:
        return format_error(err)

    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    try:
        result = await client.update_narrative(
            system_id=system_id,
            control_id=normalize_control_id(arguments["control_id"]),
            framework_id=arguments["framework_id"],
            narrative=arguments["narrative"],
            is_ai_generated=arguments.get("is_ai_generated", False),
        )
    except ValueError as e:
        return format_error(str(e))
    return format_json(result)


async def handle_update_control_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the update_control_status tool."""
    logger.debug("handle_update_control_status called with %s", _safe_args(arguments))
    err = require(arguments, "control_id", "status")
    if err:
        return format_error(err)

    enum_err = validate_enum(arguments["status"], VALID_CONTROL_STATUSES, "status")
    if enum_err:
        return format_error(enum_err)

    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        control_required=True,
    )
    result = await client.update_control_status(
        system_id=system_id,
        control_id=normalized_control_id or "",
        status=arguments["status"],
        framework_id=framework_id,
    )
    return format_json(result)


async def handle_get_control_implementation(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_control_implementation tool."""
    logger.debug("handle_get_control_implementation called with %s", _safe_args(arguments))
    err = require(arguments, "system_id", "control_id", "framework_id")
    if err:
        return format_error(err)

    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    impl = await client.get_control_implementation(
        system_id=system_id,
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
    )
    return format_json(
        {
            "control_id": impl.control_id,
            "system_id": system_id,
            "status": impl.status,
            "narrative": impl.narrative,
            "evidence_count": impl.evidence_count,
            "notes": impl.notes,
        }
    )
