"""MCP server for Pretorin Compliance API."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)

from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError

# Create the MCP server instance
server = Server("pretorin")


def _format_error(message: str) -> list[TextContent]:
    """Format an error message for MCP response."""
    return [TextContent(type="text", text=f"Error: {message}")]


def _format_json(data: Any) -> list[TextContent]:
    """Format data as JSON for MCP response."""
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="pretorin_list_frameworks",
            description="List all available compliance frameworks (NIST 800-53, FedRAMP, SOC 2, ISO 27001, etc.)",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_framework",
            description="Get detailed metadata about a specific compliance framework",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5, fedramp-moderate, soc2)",
                    },
                },
                "required": ["framework_id"],
            },
        ),
        Tool(
            name="pretorin_list_control_families",
            description="List all control families for a specific framework (e.g., AC, AU, CM for NIST)",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                },
                "required": ["framework_id"],
            },
        ),
        Tool(
            name="pretorin_list_controls",
            description="List controls for a framework, optionally filtered by control family",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "family_id": {
                        "type": "string",
                        "description": "Optional: Filter by control family ID (e.g., ac, au, cm)",
                    },
                },
                "required": ["framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_control",
            description="Get detailed information about a specific control including parameters and enhancements",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID (e.g., ac-1, ac-2, au-2)",
                    },
                },
                "required": ["framework_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_get_control_references",
            description="Get reference information for a control including statement, guidance, objectives, and related controls",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID (e.g., ac-1, ac-2)",
                    },
                },
                "required": ["framework_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_get_document_requirements",
            description="Get document requirements for a framework - both explicit requirements and those implied by controls",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5, fedramp-moderate)",
                    },
                },
                "required": ["framework_id"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        async with PretorianClient() as client:
            if not client.is_configured:
                return _format_error(
                    "Not authenticated. Please run 'pretorin login' in the terminal first."
                )

            if name == "pretorin_list_frameworks":
                return await _handle_list_frameworks(client)
            elif name == "pretorin_get_framework":
                return await _handle_get_framework(client, arguments)
            elif name == "pretorin_list_control_families":
                return await _handle_list_control_families(client, arguments)
            elif name == "pretorin_list_controls":
                return await _handle_list_controls(client, arguments)
            elif name == "pretorin_get_control":
                return await _handle_get_control(client, arguments)
            elif name == "pretorin_get_control_references":
                return await _handle_get_control_references(client, arguments)
            elif name == "pretorin_get_document_requirements":
                return await _handle_get_document_requirements(client, arguments)
            else:
                return _format_error(f"Unknown tool: {name}")

    except AuthenticationError as e:
        return _format_error(f"Authentication failed: {e.message}")
    except NotFoundError as e:
        return _format_error(f"Not found: {e.message}")
    except PretorianClientError as e:
        return _format_error(e.message)
    except Exception as e:
        return _format_error(str(e))


async def _handle_list_frameworks(client: PretorianClient) -> list[TextContent]:
    """Handle the list_frameworks tool."""
    result = await client.list_frameworks()
    return _format_json({
        "total": result.total,
        "frameworks": [
            {
                "id": fw.external_id,
                "title": fw.title,
                "version": fw.version,
                "tier": fw.tier,
                "category": fw.category,
                "families_count": fw.families_count,
                "controls_count": fw.controls_count,
            }
            for fw in result.frameworks
        ],
    })


async def _handle_get_framework(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_framework tool."""
    framework_id = arguments.get("framework_id", "")
    framework = await client.get_framework(framework_id)
    return _format_json({
        "id": framework.external_id,
        "title": framework.title,
        "version": framework.version,
        "oscal_version": framework.oscal_version,
        "description": framework.description,
        "tier": framework.tier,
        "category": framework.category,
        "published": framework.published,
        "last_modified": framework.last_modified,
    })


async def _handle_list_control_families(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_control_families tool."""
    framework_id = arguments.get("framework_id", "")
    families = await client.list_control_families(framework_id)
    return _format_json({
        "framework_id": framework_id,
        "total": len(families),
        "families": [
            {
                "id": f.id,
                "title": f.title,
                "class": f.class_type,
                "controls_count": f.controls_count,
            }
            for f in families
        ],
    })


async def _handle_list_controls(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_controls tool."""
    framework_id = arguments.get("framework_id", "")
    family_id = arguments.get("family_id")
    controls = await client.list_controls(framework_id, family_id)
    return _format_json({
        "framework_id": framework_id,
        "family_id": family_id,
        "total": len(controls),
        "controls": [
            {
                "id": c.id,
                "title": c.title,
                "family_id": c.family_id,
            }
            for c in controls
        ],
    })


async def _handle_get_control(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control tool."""
    framework_id = arguments.get("framework_id", "")
    control_id = arguments.get("control_id", "")
    control = await client.get_control(framework_id, control_id)
    return _format_json({
        "id": control.id,
        "title": control.title,
        "class": control.class_type,
        "control_type": control.control_type,
        "parameters": control.params,
        "parts": control.parts,
        "enhancements_count": len(control.controls) if control.controls else 0,
        "has_ai_guidance": control.ai_guidance is not None,
    })


async def _handle_get_control_references(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_references tool."""
    framework_id = arguments.get("framework_id", "")
    control_id = arguments.get("control_id", "")
    refs = await client.get_control_references(framework_id, control_id)
    return _format_json({
        "control_id": refs.control_id,
        "title": refs.title,
        "statement": refs.statement,
        "guidance": refs.guidance,
        "objectives": refs.objectives,
        "parameters": refs.parameters,
        "related_controls": [
            {"id": rc.id, "title": rc.title, "family_id": rc.family_id}
            for rc in refs.related_controls
        ],
    })


async def _handle_get_document_requirements(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_document_requirements tool."""
    framework_id = arguments.get("framework_id", "")
    docs = await client.get_document_requirements(framework_id)
    return _format_json({
        "framework_id": docs.framework_id,
        "framework_title": docs.framework_title,
        "total": docs.total,
        "explicit_documents": [
            {
                "id": d.id,
                "document_name": d.document_name,
                "description": d.description,
                "is_required": d.is_required,
                "control_references": d.control_references,
            }
            for d in docs.explicit_documents
        ],
        "implicit_documents": [
            {
                "id": d.id,
                "document_name": d.document_name,
                "description": d.description,
                "control_references": d.control_references,
            }
            for d in docs.implicit_documents
        ],
    })


async def _run_server() -> None:
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def run_server() -> None:
    """Entry point to run the MCP server."""
    asyncio.run(_run_server())


if __name__ == "__main__":
    run_server()
