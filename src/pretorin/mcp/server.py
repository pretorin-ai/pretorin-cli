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
            name="pretorin_whoami",
            description="Get information about the currently authenticated Pretorin user and organization",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="pretorin_check_content",
            description="Run a compliance check on text content. Returns any compliance issues found.",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "The text content to check for compliance issues",
                    },
                    "filename": {
                        "type": "string",
                        "description": "Optional filename to associate with the content",
                        "default": "document.txt",
                    },
                    "rules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific rule IDs to check against",
                    },
                },
                "required": ["content"],
            },
        ),
        Tool(
            name="pretorin_check_file",
            description="Run a compliance check on a file by path. Returns any compliance issues found.",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file to check",
                    },
                    "rules": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific rule IDs to check against",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="pretorin_list_reports",
            description="List compliance reports. Returns summaries of recent reports.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of reports to return",
                        "default": 20,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of reports to skip for pagination",
                        "default": 0,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_report",
            description="Get detailed information about a specific compliance report by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "report_id": {
                        "type": "string",
                        "description": "The ID of the report to retrieve",
                    },
                },
                "required": ["report_id"],
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

            if name == "pretorin_whoami":
                return await _handle_whoami(client)
            elif name == "pretorin_check_content":
                return await _handle_check_content(client, arguments)
            elif name == "pretorin_check_file":
                return await _handle_check_file(client, arguments)
            elif name == "pretorin_list_reports":
                return await _handle_list_reports(client, arguments)
            elif name == "pretorin_get_report":
                return await _handle_get_report(client, arguments)
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


async def _handle_whoami(client: PretorianClient) -> list[TextContent]:
    """Handle the whoami tool."""
    user_info = await client.get_user_info()
    return _format_json({
        "user_id": user_info.id,
        "email": user_info.email,
        "name": user_info.name,
        "organization": user_info.organization,
        "organization_id": user_info.organization_id,
    })


async def _handle_check_content(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the check_content tool."""
    content = arguments.get("content", "")
    filename = arguments.get("filename", "document.txt")
    rules = arguments.get("rules")

    result = await client.check_content(content, filename=filename, rules=rules)

    return _format_json({
        "check_id": result.id,
        "status": result.status.value,
        "file_name": result.file_name,
        "issues_count": len(result.issues),
        "issues": [
            {
                "id": issue.id,
                "rule_id": issue.rule_id,
                "rule_name": issue.rule_name,
                "severity": issue.severity.value,
                "message": issue.message,
                "location": issue.location,
                "suggestion": issue.suggestion,
            }
            for issue in result.issues
        ],
        "summary": result.summary,
    })


async def _handle_check_file(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the check_file tool."""
    file_path = arguments.get("file_path", "")
    rules = arguments.get("rules")

    result = await client.check_file(file_path, rules=rules)

    return _format_json({
        "check_id": result.id,
        "status": result.status.value,
        "file_name": result.file_name,
        "issues_count": len(result.issues),
        "issues": [
            {
                "id": issue.id,
                "rule_id": issue.rule_id,
                "rule_name": issue.rule_name,
                "severity": issue.severity.value,
                "message": issue.message,
                "location": issue.location,
                "suggestion": issue.suggestion,
            }
            for issue in result.issues
        ],
        "summary": result.summary,
    })


async def _handle_list_reports(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_reports tool."""
    limit = arguments.get("limit", 20)
    offset = arguments.get("offset", 0)

    reports = await client.list_reports(limit=limit, offset=offset)

    return _format_json({
        "count": len(reports),
        "reports": [
            {
                "id": report.id,
                "name": report.name,
                "status": report.status.value,
                "total_issues": report.total_issues,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ],
    })


async def _handle_get_report(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_report tool."""
    report_id = arguments.get("report_id", "")

    report = await client.get_report(report_id)

    return _format_json({
        "id": report.id,
        "name": report.name,
        "status": report.status.value,
        "created_at": report.created_at.isoformat(),
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        "total_issues": report.total_issues,
        "issues_by_severity": report.issues_by_severity,
        "checks": [
            {
                "id": check.id,
                "file_name": check.file_name,
                "status": check.status.value,
                "issues_count": len(check.issues),
            }
            for check in report.checks
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
