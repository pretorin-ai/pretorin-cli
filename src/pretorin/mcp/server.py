"""MCP server for Pretorin Compliance API."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
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
from pretorin.utils import normalize_control_id

ToolHandler = Callable[[PretorianClient, dict[str, Any]], Awaitable[list[TextContent]]]

# Create the MCP server instance
server = Server(
    "pretorin",
    instructions=(
        "Pretorin is currently in BETA. Framework and control reference tools "
        "(list_frameworks, get_control, etc.) work without restrictions. "
        "Platform write features (evidence, narratives, monitoring, control status) "
        "require a beta code. Users without a beta code can sign up for early access "
        "at https://pretorin.com/early-access/. If a platform write call fails with "
        "an authentication error, let the user know they may need a beta code."
    ),
)


def _format_error(message: str) -> list[TextContent]:
    """Format an error message for MCP response."""
    return [TextContent(type="text", text=f"Error: {message}")]


def _format_json(data: Any) -> list[TextContent]:
    """Format data as JSON for MCP response."""
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


_VALID_EVIDENCE_TYPES = {"documentation", "configuration", "screenshot", "log", "report", "policy", "code"}
_VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
_VALID_EVENT_TYPES = {"security_scan", "configuration_change", "access_review", "compliance_check"}
_VALID_CONTROL_STATUSES = {"implemented", "partial", "planned", "not_started", "not_applicable"}


def _require(arguments: dict[str, Any], *keys: str) -> str | None:
    """Validate that all keys are present and non-empty.

    Returns an error message string if validation fails, None if all ok.
    """
    missing = [k for k in keys if not arguments.get(k)]
    if missing:
        return f"Missing required parameter(s): {', '.join(missing)}"
    return None


def _validate_enum(value: str, valid: set[str], field_name: str) -> str | None:
    """Validate a value against allowed enum values.

    Returns an error message if invalid, None if ok.
    """
    if value not in valid:
        return f"Invalid {field_name}: {value!r}. Must be one of: {', '.join(sorted(valid))}"
    return None


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
            control_id = normalize_control_id(path_parts[0])
            framework_id = "fedramp-moderate"  # Default framework
        else:
            framework_id = path_parts[0]
            control_id = normalize_control_id(path_parts[1])

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
        # === System Tools ===
        Tool(
            name="pretorin_list_systems",
            description="List all systems in the user's organization",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_system",
            description=(
                "Get detailed information about a specific system including frameworks and security impact level"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_get_compliance_status",
            description="Get compliance status and framework progress for a system",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                },
                "required": ["system_id"],
            },
        ),
        # === Evidence Tools ===
        Tool(
            name="pretorin_search_evidence",
            description="Search evidence items, optionally filtered by control or framework",
            inputSchema={
                "type": "object",
                "properties": {
                    "control_id": {
                        "type": "string",
                        "description": "Optional: Filter by control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Filter by framework ID",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default 20)",
                        "default": 20,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="pretorin_create_evidence",
            description="Create a new evidence item on the platform",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "name": {
                        "type": "string",
                        "description": "Evidence name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Evidence description",
                    },
                    "evidence_type": {
                        "type": "string",
                        "description": "Type of evidence",
                        "default": "documentation",
                        "enum": sorted(_VALID_EVIDENCE_TYPES),
                    },
                    "control_id": {
                        "type": "string",
                        "description": "Optional: Associated control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Associated framework ID",
                    },
                },
                "required": ["system_id", "name", "description"],
            },
        ),
        Tool(
            name="pretorin_link_evidence",
            description="Link an existing evidence item to a control",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "evidence_id": {
                        "type": "string",
                        "description": "The evidence item ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID to link to",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework context for the link",
                    },
                },
                "required": ["system_id", "evidence_id", "control_id"],
            },
        ),
        # === Narrative Tools ===
        Tool(
            name="pretorin_get_narrative",
            description="Get an existing implementation narrative for a control in a system",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID filter",
                    },
                },
                "required": ["system_id", "control_id"],
            },
        ),
        # === Monitoring Tools ===
        Tool(
            name="pretorin_push_monitoring_event",
            description="Push a monitoring event to a system (security scan, config change, access review, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Event severity",
                        "default": "medium",
                        "enum": sorted(_VALID_SEVERITIES),
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type",
                        "default": "security_scan",
                        "enum": sorted(_VALID_EVENT_TYPES),
                    },
                    "control_id": {
                        "type": "string",
                        "description": "Optional: Associated control ID",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional: Detailed event description",
                    },
                },
                "required": ["system_id", "title"],
            },
        ),
        # === Control Context Tools ===
        Tool(
            name="pretorin_get_control_context",
            description=(
                "Get rich context for a control including AI guidance, statement,"
                " objectives, scope status, and implementation details"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID (e.g., ac-2)",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_scope",
            description="Get system scope/policy information including excluded controls and Q&A",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_update_narrative",
            description="Push a narrative text update for a control implementation",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID",
                    },
                    "narrative": {
                        "type": "string",
                        "description": "The narrative text to set",
                    },
                    "is_ai_generated": {
                        "type": "boolean",
                        "description": "Whether the narrative was AI-generated",
                        "default": False,
                    },
                },
                "required": ["system_id", "control_id", "framework_id", "narrative"],
            },
        ),
        Tool(
            name="pretorin_add_control_note",
            description=(
                "Add a note to a control implementation with suggestions such as"
                " connecting systems not directly available or manually adding evidence"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID",
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content (suggestions, manual steps, integration guidance)",
                    },
                },
                "required": ["system_id", "control_id", "framework_id", "content"],
            },
        ),
        # === Control Implementation Tools ===
        Tool(
            name="pretorin_update_control_status",
            description="Update the implementation status of a control in a system",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                    "status": {
                        "type": "string",
                        "description": "New implementation status",
                        "enum": sorted(_VALID_CONTROL_STATUSES),
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework context",
                    },
                },
                "required": ["system_id", "control_id", "status"],
            },
        ),
        Tool(
            name="pretorin_get_control_implementation",
            description=(
                "Get implementation details for a control in a system, including narrative, evidence count, and notes"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": {
                        "type": "string",
                        "description": "The system ID",
                    },
                    "control_id": {
                        "type": "string",
                        "description": "The control ID",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID filter",
                    },
                },
                "required": ["system_id", "control_id"],
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

            handler = _TOOL_HANDLERS.get(name)
            if handler:
                return await handler(client, arguments)
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


async def _handle_list_frameworks(client: PretorianClient, arguments: dict[str, Any]) -> list[TextContent]:
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
    control_id = normalize_control_id(arguments.get("control_id", ""))
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
    control_id = normalize_control_id(arguments.get("control_id", ""))
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


async def _handle_list_systems(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_systems tool."""
    systems = await client.list_systems()
    return _format_json(
        {
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
    )


async def _handle_get_system(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_system tool."""
    system_id = arguments.get("system_id", "")
    system = await client.get_system(system_id)
    return _format_json(
        {
            "id": system.id,
            "name": system.name,
            "description": system.description,
            "frameworks": system.frameworks,
            "security_impact_level": system.security_impact_level,
        }
    )


async def _handle_get_compliance_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_compliance_status tool."""
    system_id = arguments.get("system_id", "")
    status = await client.get_system_compliance_status(system_id)
    return _format_json(status)


async def _handle_search_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the search_evidence tool."""
    raw_control_id = arguments.get("control_id")
    evidence = await client.list_evidence(
        control_id=normalize_control_id(raw_control_id) if raw_control_id else None,
        framework_id=arguments.get("framework_id"),
        limit=arguments.get("limit", 20),
    )
    return _format_json(
        {
            "total": len(evidence),
            "evidence": [
                {
                    "id": e.id,
                    "name": e.name,
                    "description": e.description,
                    "evidence_type": e.evidence_type,
                    "status": e.status,
                    "collected_at": e.collected_at,
                }
                for e in evidence
            ],
        }
    )


async def _handle_create_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the create_evidence tool."""
    err = _require(arguments, "system_id")
    if err:
        return _format_error(err)

    from pretorin.client.models import EvidenceCreate

    evidence_type = arguments.get("evidence_type", "documentation")
    enum_err = _validate_enum(evidence_type, _VALID_EVIDENCE_TYPES, "evidence_type")
    if enum_err:
        return _format_error(enum_err)

    raw_control_id = arguments.get("control_id")
    evidence = EvidenceCreate(
        name=arguments.get("name", ""),
        description=arguments.get("description", ""),
        evidence_type=evidence_type,
        source="mcp",
        control_id=normalize_control_id(raw_control_id) if raw_control_id else None,
        framework_id=arguments.get("framework_id"),
    )
    result = await client.create_evidence(arguments["system_id"], evidence)
    return _format_json(result)


async def _handle_link_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the link_evidence tool."""
    err = _require(arguments, "system_id", "evidence_id", "control_id")
    if err:
        return _format_error(err)

    result = await client.link_evidence_to_control(
        evidence_id=arguments["evidence_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        system_id=arguments["system_id"],
        framework_id=arguments.get("framework_id"),
    )
    return _format_json(result)


async def _handle_get_narrative(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_narrative tool."""
    narrative = await client.get_narrative(
        system_id=arguments.get("system_id", ""),
        control_id=normalize_control_id(arguments.get("control_id", "")),
        framework_id=arguments.get("framework_id"),
    )
    return _format_json(
        {
            "control_id": narrative.control_id,
            "framework_id": narrative.framework_id,
            "narrative": narrative.narrative,
            "ai_confidence_score": narrative.ai_confidence_score,
            "status": narrative.status,
        }
    )


async def _handle_push_monitoring_event(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the push_monitoring_event tool."""
    err = _require(arguments, "system_id", "title")
    if err:
        return _format_error(err)

    from pretorin.client.models import MonitoringEventCreate

    event_type = arguments.get("event_type", "security_scan")
    severity = arguments.get("severity", "medium")
    enum_err = _validate_enum(event_type, _VALID_EVENT_TYPES, "event_type")
    if enum_err:
        return _format_error(enum_err)
    enum_err = _validate_enum(severity, _VALID_SEVERITIES, "severity")
    if enum_err:
        return _format_error(enum_err)

    raw_control_id = arguments.get("control_id")
    event = MonitoringEventCreate(
        event_type=event_type,
        title=arguments["title"],
        description=arguments.get("description", ""),
        severity=severity,
        control_id=normalize_control_id(raw_control_id) if raw_control_id else None,
        event_data={"source": "mcp"},
    )
    result = await client.create_monitoring_event(
        system_id=arguments["system_id"],
        event=event,
    )
    return _format_json(result)


async def _handle_get_control_context(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_context tool."""
    ctx = await client.get_control_context(
        system_id=arguments.get("system_id", ""),
        control_id=normalize_control_id(arguments.get("control_id", "")),
        framework_id=arguments.get("framework_id", ""),
    )
    return _format_json(ctx.model_dump())


async def _handle_get_scope(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_scope tool."""
    scope = await client.get_scope(
        system_id=arguments.get("system_id", ""),
    )
    return _format_json(scope.model_dump())


async def _handle_add_control_note(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the add_control_note tool."""
    err = _require(arguments, "system_id", "control_id", "framework_id", "content")
    if err:
        return _format_error(err)

    result = await client.add_control_note(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        content=arguments["content"],
        framework_id=arguments["framework_id"],
        source="mcp",
    )
    return _format_json(result)


async def _handle_update_narrative(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the update_narrative tool."""
    err = _require(arguments, "system_id", "control_id", "framework_id", "narrative")
    if err:
        return _format_error(err)

    result = await client.update_narrative(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
        narrative=arguments["narrative"],
        is_ai_generated=arguments.get("is_ai_generated", False),
    )
    return _format_json(result)


async def _handle_update_control_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the update_control_status tool."""
    err = _require(arguments, "system_id", "control_id", "status")
    if err:
        return _format_error(err)

    enum_err = _validate_enum(arguments["status"], _VALID_CONTROL_STATUSES, "status")
    if enum_err:
        return _format_error(enum_err)

    result = await client.update_control_status(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        status=arguments["status"],
        framework_id=arguments.get("framework_id"),
    )
    return _format_json(result)


async def _handle_get_control_implementation(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_implementation tool."""
    impl = await client.get_control_implementation(
        system_id=arguments.get("system_id", ""),
        control_id=normalize_control_id(arguments.get("control_id", "")),
        framework_id=arguments.get("framework_id"),
    )
    return _format_json(
        {
            "control_id": impl.control_id,
            "status": impl.status,
            "narrative": impl.narrative,
            "evidence_count": impl.evidence_count,
            "notes": impl.notes,
        }
    )


# Tool name → handler dispatch table
_TOOL_HANDLERS: dict[str, ToolHandler] = {
    "pretorin_list_frameworks": _handle_list_frameworks,
    "pretorin_get_framework": _handle_get_framework,
    "pretorin_list_control_families": _handle_list_control_families,
    "pretorin_list_controls": _handle_list_controls,
    "pretorin_get_control": _handle_get_control,
    "pretorin_get_control_references": _handle_get_control_references,
    "pretorin_get_document_requirements": _handle_get_document_requirements,
    "pretorin_list_systems": _handle_list_systems,
    "pretorin_get_system": _handle_get_system,
    "pretorin_get_compliance_status": _handle_get_compliance_status,
    "pretorin_search_evidence": _handle_search_evidence,
    "pretorin_create_evidence": _handle_create_evidence,
    "pretorin_link_evidence": _handle_link_evidence,
    "pretorin_get_narrative": _handle_get_narrative,
    "pretorin_push_monitoring_event": _handle_push_monitoring_event,
    "pretorin_add_control_note": _handle_add_control_note,
    "pretorin_update_control_status": _handle_update_control_status,
    "pretorin_get_control_implementation": _handle_get_control_implementation,
    "pretorin_get_control_context": _handle_get_control_context,
    "pretorin_get_scope": _handle_get_scope,
    "pretorin_update_narrative": _handle_update_narrative,
}


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
