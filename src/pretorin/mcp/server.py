"""MCP server for Pretorin Compliance API."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Resource, TextContent, Tool

from pretorin.cli.version_check import get_update_status
from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError
from pretorin.mcp.handlers import TOOL_HANDLERS
from pretorin.mcp.helpers import format_error
from pretorin.mcp.resources import list_resources as _list_resources
from pretorin.mcp.resources import read_resource as _read_resource
from pretorin.mcp.tools import list_tools as _list_tools

logger = logging.getLogger(__name__)
PUBLIC_TOOL_NAMES = {"pretorin_get_cli_status"}

# Create the MCP server instance
server = Server(
    "pretorin",
    instructions=(
        "Pretorin is currently in BETA. Framework and control reference tools "
        "(list_frameworks, get_control, etc.) are available to authenticated users. "
        "\n\n"
        "ROUTING — IMPORTANT: When the user references pretorin work (a control, "
        "system, framework, questionnaire, or campaign), the FIRST tool to call "
        "is pretorin_start_task. Extract entities (intent_verb, system_id, "
        "framework_id, control_ids, scope_question_ids, policy_question_ids) "
        "from the user prompt and pass them in. Pretorin runs deterministic "
        "rules to pick a workflow and bundles the relevant platform state into "
        "the response. Then read the selected workflow's body via "
        "pretorin_get_workflow and follow it. Do NOT call evidence/narrative "
        "write tools before pretorin_start_task has resolved the workflow and "
        "scope — that path produces wrong-framework writes and breaks the "
        "audit chain. The one exception is when the user is asking pure "
        "reference questions ('show me AC-2', 'list frameworks'); those go "
        "directly to the read-side tools without start_task. "
        "\n\n"
        "Creating a system requires a beta code — systems can only be created on "
        "the Pretorin platform (https://platform.pretorin.com), not through the CLI "
        "or MCP. Without a system, platform write features (evidence, narratives, "
        "monitoring, control status) cannot be used. If list_systems returns no "
        "systems, tell the user they need a beta code to create one on the platform "
        "and can sign up for early access at https://pretorin.com/early-access/. "
        "MCP hosts can inspect pretorin_get_cli_status or status://cli to surface "
        "local CLI update guidance."
    ),
)


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available MCP resources for compliance analysis."""
    return await _list_resources()


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read an analysis resource."""
    return await _read_resource(uri)


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return await _list_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Handle tool calls."""
    logger.info("Tool call: %s", name)
    try:
        handler = TOOL_HANDLERS.get(name)
        if name in PUBLIC_TOOL_NAMES:
            if handler:
                return await handler(None, arguments)
            logger.warning("Unknown tool requested: %s", name)
            return format_error(f"Unknown tool: {name}")

        async with PretorianClient() as client:
            if not client.is_configured:
                logger.warning("Tool call %s failed: client not authenticated", name)
                return format_error("Not authenticated. Please run 'pretorin login' in the terminal first.")

            if handler:
                return await handler(client, arguments)
            # Phase C: per-recipe-script tools (pretorin_recipe_<id>__<tool>) are
            # not in the static TOOL_HANDLERS table — they're registered dynamically
            # from the recipe registry. Dispatch the catch-all here when the name
            # matches the prefix.
            if name.startswith("pretorin_recipe_") and "__" in name[len("pretorin_recipe_") :]:
                from pretorin.mcp.handlers.recipe import handle_run_recipe_script

                return await handle_run_recipe_script(client, arguments, tool_name=name)
            logger.warning("Unknown tool requested: %s", name)
            return format_error(f"Unknown tool: {name}")

    except AuthenticationError as e:
        logger.warning("Authentication error during tool %s: %s", name, e.message)
        return format_error(f"Authentication failed: {e.message}")
    except NotFoundError as e:
        logger.warning("Not found during tool %s: %s", name, e.message)
        return format_error(f"Not found: {e.message}")
    except PretorianClientError as e:
        logger.error("Client error during tool %s: %s", name, e.message)
        return format_error(e.message)
    except Exception as e:
        logger.error("Unexpected error during tool %s: %s", name, e, exc_info=True)
        return format_error(str(e))


async def _run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def _maybe_print_startup_update_notice() -> None:
    """Emit a non-blocking update prompt for MCP hosts on stderr."""
    status = get_update_status()
    prompt = status.get("prompt")
    if not prompt:
        return
    print(f"NOTICE: {prompt}", file=sys.stderr, flush=True)


def run_server() -> None:
    """Entry point to run the MCP server."""
    logger.info("Starting Pretorin MCP server")
    _maybe_print_startup_update_notice()
    asyncio.run(_run_server())


if __name__ == "__main__":
    run_server()
