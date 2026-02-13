"""MCP server for Pretorin Compliance API."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import urlparse

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    TextContent,
    Tool,
)

from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError
from pretorin.mcp.analysis_prompts import (
    format_control_analysis_prompt,
    get_artifact_schema,
    get_available_controls,
    get_control_summary,
    get_framework_guide,
)

# Create the MCP server instance
server = Server("pretorin")


def _format_error(message: str) -> list[TextContent]:
    """Format an error message for MCP response."""
    return [TextContent(type="text", text=f"Error: {message}")]


def _format_json(data: Any) -> list[TextContent]:
    """Format data as JSON for MCP response."""
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


# =============================================================================
# MCP Resources for Analysis
# =============================================================================


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available MCP resources for compliance analysis."""
    resources = [
        Resource(
            uri="analysis://schema",
            name="Compliance Artifact Schema",
            description="JSON schema for compliance artifacts that AI should produce during analysis",
            mimeType="text/markdown",
        ),
    ]

    # Add framework guides for common frameworks
    framework_guides = [
        ("fedramp-moderate", "FedRAMP Moderate"),
        ("nist-800-53-r5", "NIST 800-53 Rev 5"),
        ("nist-800-171-r3", "NIST 800-171 Rev 3"),
    ]

    for framework_id, title in framework_guides:
        resources.append(
            Resource(
                uri=f"analysis://guide/{framework_id}",
                name=f"{title} Analysis Guide",
                description=f"Analysis guidance for {title} framework",
                mimeType="text/markdown",
            )
        )

    # Add control analysis prompts for available controls
    for control_id in get_available_controls():
        summary = get_control_summary(control_id)
        resources.append(
            Resource(
                uri=f"analysis://control/{control_id}",
                name=f"Control {control_id.upper()} Analysis",
                description=f"Analysis guidance for {summary}",
                mimeType="text/markdown",
            )
        )

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read an analysis resource."""
    parsed = urlparse(uri)

    if parsed.scheme != "analysis":
        raise ValueError(f"Unknown resource scheme: {parsed.scheme}")

    # Parse the path (netloc + path for analysis:// URIs)
    # For "analysis://schema", netloc is "schema" and path is ""
    # For "analysis://guide/fedramp-moderate", netloc is "guide" and path is "/fedramp-moderate"
    resource_type = parsed.netloc
    path_parts = [p for p in parsed.path.split("/") if p]

    if resource_type == "schema":
        return get_artifact_schema()

    elif resource_type == "guide":
        if not path_parts:
            raise ValueError("Framework ID required for guide resource")
        framework_id = path_parts[0]
        guide = get_framework_guide(framework_id)
        if guide:
            return guide
        raise ValueError(f"No analysis guide available for framework: {framework_id}")

    elif resource_type == "control":
        if not path_parts:
            raise ValueError("Control ID required for control resource")
        # Support both analysis://control/ac-2 and analysis://control/fedramp-moderate/ac-2
        if len(path_parts) == 1:
            control_id = path_parts[0]
            framework_id = "fedramp-moderate"  # Default framework
        else:
            framework_id = path_parts[0]
            control_id = path_parts[1]

        return format_control_analysis_prompt(framework_id, control_id)

    else:
        raise ValueError(f"Unknown resource type: {resource_type}")


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
            description=(
                "Get detailed metadata about a specific compliance framework including"
                " AI context (purpose, target audience, regulatory context, scope, key concepts)"
            ),
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
            description=(
                "List all control families for a specific framework with"
                " AI context (domain summary, risk context, implementation priority)"
            ),
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
                        "description": "Optional: Filter by control family ID",
                    },
                },
                "required": ["framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_control",
            description=(
                "Get detailed information about a specific control including parameters,"
                " enhancements, and AI guidance (summary, intent, evidence expectations,"
                " implementation considerations, common failures)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                },
                "required": ["framework_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_get_control_references",
            description="Get control references: statement, guidance, objectives, and related controls",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                },
                "required": ["framework_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_get_document_requirements",
            description="Get document requirements for a framework (explicit and control-implied)",
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
                return _format_error("Not authenticated. Please run 'pretorin login' in the terminal first.")

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
    return _format_json(
        {
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
        }
    )


async def _handle_get_framework(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_framework tool."""
    framework_id = arguments.get("framework_id", "")
    framework = await client.get_framework(framework_id)
    return _format_json(
        {
            "id": framework.external_id,
            "title": framework.title,
            "version": framework.version,
            "oscal_version": framework.oscal_version,
            "description": framework.description,
            "tier": framework.tier,
            "category": framework.category,
            "published": framework.published,
            "last_modified": framework.last_modified,
            "ai_context": framework.ai_context,
        }
    )


async def _handle_list_control_families(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_control_families tool."""
    framework_id = arguments.get("framework_id", "")
    families = await client.list_control_families(framework_id)
    return _format_json(
        {
            "framework_id": framework_id,
            "total": len(families),
            "families": [
                {
                    "id": f.id,
                    "title": f.title,
                    "class": f.class_type,
                    "controls_count": f.controls_count,
                    "ai_context": f.ai_context,
                }
                for f in families
            ],
        }
    )


async def _handle_list_controls(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_controls tool."""
    framework_id = arguments.get("framework_id", "")
    family_id = arguments.get("family_id")
    controls = await client.list_controls(framework_id, family_id)
    return _format_json(
        {
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
        }
    )


async def _handle_get_control(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control tool."""
    framework_id = arguments.get("framework_id", "")
    control_id = arguments.get("control_id", "")
    control = await client.get_control(framework_id, control_id)
    return _format_json(
        {
            "id": control.id,
            "title": control.title,
            "class": control.class_type,
            "control_type": control.control_type,
            "parameters": control.params,
            "parts": control.parts,
            "enhancements_count": len(control.controls) if control.controls else 0,
            "ai_guidance": control.ai_guidance,
        }
    )


async def _handle_get_control_references(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_references tool."""
    framework_id = arguments.get("framework_id", "")
    control_id = arguments.get("control_id", "")
    refs = await client.get_control_references(framework_id, control_id)
    return _format_json(
        {
            "control_id": refs.control_id,
            "title": refs.title,
            "statement": refs.statement,
            "guidance": refs.guidance,
            "objectives": refs.objectives,
            "parameters": refs.parameters,
            "related_controls": [
                {"id": rc.id, "title": rc.title, "family_id": rc.family_id} for rc in refs.related_controls
            ],
        }
    )


async def _handle_get_document_requirements(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_document_requirements tool."""
    framework_id = arguments.get("framework_id", "")
    docs = await client.get_document_requirements(framework_id)
    return _format_json(
        {
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
        }
    )


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
