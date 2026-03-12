"""MCP tool schema definitions."""

from __future__ import annotations

from mcp.types import Tool

from pretorin.mcp.helpers import (
    VALID_CONTROL_STATUSES,
    VALID_EVENT_TYPES,
    VALID_EVIDENCE_TYPES,
    VALID_SEVERITIES,
    control_id_property,
    system_id_property,
)


async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        # === Framework / Control Reference Tools ===
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
                    "control_id": control_id_property(),
                },
                "required": ["framework_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_get_controls_batch",
            description="Get detailed control data for many controls in a single framework-scoped request",
            inputSchema={
                "type": "object",
                "properties": {
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5)",
                    },
                    "control_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional: list of control IDs to retrieve; omit to retrieve all controls",
                    },
                },
                "required": ["framework_id"],
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
                    "control_id": control_id_property(),
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
                    "system_id": system_id_property(),
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
                    "system_id": system_id_property(),
                },
                "required": ["system_id"],
            },
        ),
        # === Evidence Tools ===
        Tool(
            name="pretorin_search_evidence",
            description="Search evidence items within exactly one active system/framework scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
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
            description=(
                "Upsert an evidence item on the platform (find-or-create by default) "
                "using auditor-ready markdown descriptions within one active system/framework scope"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "name": {
                        "type": "string",
                        "description": "Evidence name",
                    },
                    "description": {
                        "type": "string",
                        "description": (
                            "Evidence description in markdown with no headings and at least one rich element "
                            "(code block, table, list, or link). Images are not allowed yet."
                        ),
                    },
                    "evidence_type": {
                        "type": "string",
                        "description": "Type of evidence",
                        "default": "policy_document",
                        "enum": sorted(VALID_EVIDENCE_TYPES),
                    },
                    "control_id": control_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Associated framework ID; defaults to active scope",
                    },
                    "dedupe": {
                        "type": "boolean",
                        "description": "Whether to reuse exact-matching org evidence before creating",
                        "default": True,
                    },
                },
                "required": ["name", "description"],
            },
        ),
        Tool(
            name="pretorin_create_evidence_batch",
            description="Create and link multiple evidence items within exactly one active system/framework scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "items": {
                        "type": "array",
                        "description": "Scoped evidence items to create and link",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "control_id": control_id_property(),
                                "evidence_type": {
                                    "type": "string",
                                    "enum": sorted(VALID_EVIDENCE_TYPES),
                                },
                                "relevance_notes": {"type": "string"},
                            },
                            "required": ["name", "description", "control_id"],
                        },
                    },
                },
                "required": ["items"],
            },
        ),
        Tool(
            name="pretorin_link_evidence",
            description="Link an existing evidence item to a control within exactly one active system/framework scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "evidence_id": {
                        "type": "string",
                        "description": "The evidence item ID",
                    },
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework context for the link; defaults to active scope",
                    },
                },
                "required": ["evidence_id", "control_id"],
            },
        ),
        # === Narrative Tools ===
        Tool(
            name="pretorin_get_narrative",
            description="Get an existing implementation narrative for a control in a system",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (required for narrative lookup)",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_generate_control_artifacts",
            description=(
                "Generate read-only AI drafts for a control narrative and evidence-gap assessment "
                "using the same Codex agent workflow as the CLI"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID",
                    },
                    "working_directory": {
                        "type": "string",
                        "description": "Optional: local workspace path for code-aware drafting",
                    },
                    "model": {
                        "type": "string",
                        "description": "Optional: model override for the Codex agent",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        # === Monitoring Tools ===
        Tool(
            name="pretorin_push_monitoring_event",
            description="Push a monitoring event within exactly one active system/framework scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "title": {
                        "type": "string",
                        "description": "Event title",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Event severity",
                        "default": "medium",
                        "enum": sorted(VALID_SEVERITIES),
                    },
                    "event_type": {
                        "type": "string",
                        "description": "Event type",
                        "default": "security_scan",
                        "enum": sorted(VALID_EVENT_TYPES),
                    },
                    "control_id": control_id_property(optional=True),
                    "description": {
                        "type": "string",
                        "description": "Optional: Detailed event description",
                    },
                },
                "required": ["title"],
            },
        ),
        # === Control Context Tools ===
        Tool(
            name="pretorin_get_control_context",
            description=(
                "Get rich context for a control including AI guidance, statement,"
                " objectives, scope status, and implementation details within one active system/framework scope"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                },
                "required": ["control_id"],
            },
        ),
        Tool(
            name="pretorin_get_scope",
            description="Get system scope/policy information including excluded controls and Q&A",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5, fedramp-moderate, soc2)",
                    },
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_update_narrative",
            description="Push a narrative text update for a control implementation",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID",
                    },
                    "narrative": {
                        "type": "string",
                        "description": (
                            "Narrative markdown with no headings, at least two rich elements, and at least one "
                            "structural element (code block, table, or list). Images are not allowed yet."
                        ),
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
                " connecting systems not directly available or manually adding evidence."
                " Notes are append-only. Content is plain text (no markdown validation required)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
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
        Tool(
            name="pretorin_get_control_notes",
            description="Get notes for a control implementation within exactly one active system/framework scope",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                },
                "required": ["control_id"],
            },
        ),
        # === Control Implementation Tools ===
        Tool(
            name="pretorin_update_control_status",
            description=(
                "Update the implementation status of a control within exactly one active system/framework scope"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "status": {
                        "type": "string",
                        "description": "New implementation status",
                        "enum": sorted(VALID_CONTROL_STATUSES),
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                },
                "required": ["control_id", "status"],
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
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (required for control lookup)",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
    ]
