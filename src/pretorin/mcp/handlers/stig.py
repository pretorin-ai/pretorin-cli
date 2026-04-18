"""Handlers for STIG and CCI tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import (
    format_error,
    format_json,
    require,
    resolve_system_id,
    safe_args,
)

logger = logging.getLogger(__name__)

# Alias for backward compatibility within this module.
_safe_args = safe_args


# ---------------------------------------------------------------------------
# Read-only reference tools (no system_id required)
# ---------------------------------------------------------------------------


async def handle_list_stigs(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_stigs tool."""
    logger.debug("handle_list_stigs called with %s", _safe_args(arguments))
    result = await client.list_stigs(
        technology_area=arguments.get("technology_area"),
        product=arguments.get("product"),
        limit=arguments.get("limit", 100),
        offset=arguments.get("offset", 0),
    )
    return format_json(result)


async def handle_get_stig(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_stig tool."""
    logger.debug("handle_get_stig called with %s", _safe_args(arguments))
    err = require(arguments, "stig_id")
    if err:
        return format_error(err)

    result = await client.get_stig(stig_id=arguments["stig_id"])
    return format_json(result)


async def handle_list_stig_rules(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the list_stig_rules tool."""
    logger.debug("handle_list_stig_rules called with %s", _safe_args(arguments))
    err = require(arguments, "stig_id")
    if err:
        return format_error(err)

    result = await client.list_stig_rules(
        stig_id=arguments["stig_id"],
        severity=arguments.get("severity"),
        cci_id=arguments.get("cci_id"),
        limit=arguments.get("limit", 100),
        offset=arguments.get("offset", 0),
    )
    return format_json(result)


async def handle_get_stig_rule(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_stig_rule tool."""
    logger.debug("handle_get_stig_rule called with %s", _safe_args(arguments))
    err = require(arguments, "stig_id", "rule_id")
    if err:
        return format_error(err)

    result = await client.get_stig_rule(
        stig_id=arguments["stig_id"],
        rule_id=arguments["rule_id"],
    )
    return format_json(result)


async def handle_list_ccis(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_ccis tool."""
    logger.debug("handle_list_ccis called with %s", _safe_args(arguments))
    result = await client.list_ccis(
        nist_control_id=arguments.get("nist_control_id"),
        status=arguments.get("status"),
        limit=arguments.get("limit", 100),
        offset=arguments.get("offset", 0),
    )
    return format_json(result)


async def handle_get_cci_chain(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_cci_chain tool."""
    logger.debug("handle_get_cci_chain called with %s", _safe_args(arguments))
    err = require(arguments, "nist_control_id")
    if err:
        return format_error(err)

    result = await client.get_cci_chain(nist_control_id=arguments["nist_control_id"])
    return format_json(result)


async def handle_get_cci(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_cci tool."""
    logger.debug("handle_get_cci called with %s", _safe_args(arguments))
    err = require(arguments, "cci_id")
    if err:
        return format_error(err)

    result = await client.get_cci(cci_id=arguments["cci_id"])
    return format_json(result)


# ---------------------------------------------------------------------------
# System-scoped tools (require system_id)
# ---------------------------------------------------------------------------


async def handle_get_test_manifest(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_test_manifest tool."""
    logger.debug("handle_get_test_manifest called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        return format_error("system_id is required")

    result = await client.get_test_manifest(
        system_id=system_id,
        stig_id=arguments.get("stig_id"),
    )
    return format_json(result)


async def handle_submit_test_results(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the submit_test_results tool."""
    logger.debug("handle_submit_test_results called with %s", _safe_args(arguments))
    err = require(arguments, "cli_run_id", "results")
    if err:
        return format_error(err)

    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        return format_error("system_id is required")

    result = await client.submit_test_results(
        system_id=system_id,
        cli_run_id=arguments["cli_run_id"],
        results=arguments["results"],
        cli_version=arguments.get("cli_version"),
    )
    return format_json(result)


async def handle_get_stig_applicability(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_stig_applicability tool."""
    logger.debug("handle_get_stig_applicability called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        return format_error("system_id is required")

    result = await client.get_stig_applicability(system_id=system_id)
    return format_json(result)


async def handle_get_cci_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_cci_status tool."""
    logger.debug("handle_get_cci_status called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        return format_error("system_id is required")

    result = await client.get_cci_status(
        system_id=system_id,
        nist_control_id=arguments.get("nist_control_id"),
    )
    return format_json(result)


async def handle_infer_stigs(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the infer_stigs tool."""
    logger.debug("handle_infer_stigs called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        return format_error("system_id is required")

    result = await client.infer_stigs(system_id=system_id)
    return format_json(result)
