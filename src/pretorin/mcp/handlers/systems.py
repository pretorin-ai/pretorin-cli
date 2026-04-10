"""Handlers for system management tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import TextContent

from pretorin.cli.version_check import get_update_status
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.mcp.helpers import format_json, resolve_system_id

logger = logging.getLogger(__name__)


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments with sensitive fields redacted."""
    return {k: ("***" if k == "api_key" else v) for k, v in arguments.items()}


async def handle_list_systems(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_systems tool."""
    logger.debug("handle_list_systems called with %s", _safe_args(arguments))
    systems = await client.list_systems()
    result: dict[str, Any] = {
        "total": len(systems),
        "systems": [
            {
                "id": s.get("id", ""),
                "name": s.get("name", ""),
                "description": s.get("description"),
                "security_impact_level": s.get("security_impact_level"),
            }
            for s in systems
        ],
    }
    if not systems:
        result["note"] = (
            "No systems found. Systems can only be created on the Pretorin platform "
            "(https://platform.pretorin.com) with a beta code. Pretorin is currently "
            "in closed beta — the user can sign up for early access at "
            "https://pretorin.com/early-access/. Without a system, framework and "
            "control browsing tools still work."
        )
    return format_json(result)


async def handle_get_system(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_system tool."""
    logger.debug("handle_get_system called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    system = await client.get_system(system_id)
    return format_json(
        {
            "id": system.id,
            "name": system.name,
            "description": system.description,
            "frameworks": system.frameworks,
            "security_impact_level": system.security_impact_level,
        }
    )


async def handle_get_compliance_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_compliance_status tool."""
    logger.debug("handle_get_compliance_status called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    status = await client.get_system_compliance_status(system_id)
    return format_json(status)


async def handle_get_cli_status(
    _client: PretorianClient | None,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_cli_status tool."""
    logger.debug("handle_get_cli_status called with %s", _safe_args(arguments))
    return format_json(get_update_status(force=bool(arguments.get("force", False))))
