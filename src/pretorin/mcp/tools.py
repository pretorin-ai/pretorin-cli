"""MCP tool schema definitions."""

from __future__ import annotations

from typing import Any

from mcp.types import Tool

from pretorin.mcp.helpers import (
    VALID_CONTROL_STATUSES,
    VALID_EVENT_TYPES,
    VALID_EVIDENCE_TYPES,
    VALID_SEVERITIES,
    allow_scope_override_property,
    allow_unverified_sources_property,
    control_id_property,
    system_id_property,
)


async def list_tools() -> list[Tool]:
    """List available MCP tools.

    Static tools are declared inline; per-recipe-script tools are appended
    dynamically from the recipe registry (Phase C). Each script in each loaded
    recipe contributes one MCP tool named ``pretorin_recipe_<safe_id>__<tool>``
    with ``inputSchema`` derived from the script's ``ScriptDecl.params``.
    """
    static_tools = _static_tools()
    dynamic_tools = _recipe_script_tools()
    return static_tools + dynamic_tools


def _static_tools() -> list[Tool]:
    """Return the always-present built-in MCP tools."""
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
            name="pretorin_get_cli_status",
            description=(
                "Return the local Pretorin CLI version status, including update availability "
                "and upgrade guidance for MCP hosts and agents"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Bypass the local cache and re-check PyPI for the latest version",
                        "default": False,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_source_manifest",
            description=(
                "Get the resolved source manifest for a system and evaluate it against "
                "currently detected sources. Shows which external sources (git, cloud, "
                "HRIS, etc.) are required, recommended, or optional, and whether each "
                "is currently satisfied. Returns null manifest if none is configured."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                },
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
                        "description": "Type of evidence (required, must be one of the canonical values)",
                        "enum": sorted(VALID_EVIDENCE_TYPES),
                    },
                    "control_id": control_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Associated framework ID; defaults to active scope",
                    },
                    "code_file_path": {
                        "type": "string",
                        "description": "Path to source file (relative to workspace root)",
                    },
                    "code_line_numbers": {
                        "type": "string",
                        "description": "Line range (e.g., '10-25')",
                    },
                    "code_snippet": {
                        "type": "string",
                        "description": "Relevant code excerpt",
                    },
                    "code_repository": {
                        "type": "string",
                        "description": "Git repository URL",
                    },
                    "code_commit_hash": {
                        "type": "string",
                        "description": "Git commit hash",
                    },
                    "dedupe": {
                        "type": "boolean",
                        "description": "Whether to reuse exact-matching org evidence before creating",
                        "default": True,
                    },
                    "recipe_context_id": {
                        "type": "string",
                        "description": (
                            "Optional. When supplied (caller has an active recipe execution context "
                            "from pretorin_start_recipe), the resulting evidence is stamped "
                            "producer_kind='recipe' with the context's recipe id and version "
                            "automatically. Without it, evidence is stamped producer_kind='agent'."
                        ),
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["name", "description", "evidence_type"],
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
                                    "description": (
                                        "Type of evidence. Required; must be one of the canonical values. "
                                        "Non-canonical strings that slip through are normalized server-side "
                                        "(aliases like audit_log -> log_file) but well-behaved clients should "
                                        "pick a canonical value from the enum."
                                    ),
                                },
                                "relevance_notes": {"type": "string"},
                                "code_file_path": {"type": "string", "description": "Path to source file"},
                                "code_line_numbers": {"type": "string", "description": "Line range (e.g., '10-25')"},
                                "code_snippet": {"type": "string", "description": "Relevant code excerpt"},
                                "code_repository": {"type": "string", "description": "Git repository URL"},
                                "code_commit_hash": {"type": "string", "description": "Git commit hash"},
                            },
                            "required": ["name", "description", "control_id", "evidence_type"],
                        },
                    },
                    "recipe_context_id": {
                        "type": "string",
                        "description": (
                            "Optional. When supplied (caller has an active recipe execution context "
                            "from pretorin_start_recipe), every item in the batch is stamped "
                            "producer_kind='recipe'. All items share the same context — per-item "
                            "context variation is not supported in v1."
                        ),
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
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
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["evidence_id", "control_id"],
            },
        ),
        Tool(
            name="pretorin_upload_evidence",
            description="Upload a file as evidence to the platform (system-scoped, requires WRITE access)",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the file to upload",
                    },
                    "name": {
                        "type": "string",
                        "description": "Evidence name",
                    },
                    "evidence_type": {
                        "type": "string",
                        "description": "Type of evidence",
                        "default": "other",
                        "enum": sorted(VALID_EVIDENCE_TYPES),
                    },
                    "description": {
                        "type": "string",
                        "description": "Evidence description",
                    },
                    "control_id": control_id_property(optional=True),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["file_path", "name"],
            },
        ),
        Tool(
            name="pretorin_delete_evidence",
            description="Delete an evidence item from the platform (system-scoped, requires WRITE access)",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "evidence_id": {
                        "type": "string",
                        "description": "The evidence item ID to delete",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                },
                "required": ["evidence_id"],
            },
        ),
        # === Narrative Tools ===
        Tool(
            name="pretorin_get_narrative",
            description="Get an existing implementation narrative for a control in a system",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["control_id"],
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
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
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
        # === Scope & Policy Questionnaire Tools ===
        Tool(
            name="pretorin_patch_scope_qa",
            description=(
                "Update scope questionnaire answers for a system/framework. "
                "Accepts a list of question_id/answer pairs to apply as partial updates. "
                "IMPORTANT: Before drafting answers, research the local workspace — read "
                "source code, infrastructure config, and documentation to ground answers "
                "in observable facts. Ask the user for clarification on anything that "
                "cannot be determined from the workspace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "The framework ID (e.g., nist-800-53-r5, fedramp-moderate, soc2)",
                    },
                    "updates": {
                        "type": "array",
                        "description": "List of question/answer updates to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {
                                    "type": "string",
                                    "description": "The scope question ID (e.g., sd-1, ab-1, sc-1)",
                                },
                                "answer": {
                                    "type": "string",
                                    "description": "The updated answer text",
                                },
                            },
                            "required": ["question_id", "answer"],
                        },
                    },
                },
                "required": ["system_id", "framework_id", "updates"],
            },
        ),
        Tool(
            name="pretorin_list_org_policies",
            description="List organization policies available for questionnaire work",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_org_policy_questionnaire",
            description=(
                "Get the canonical questionnaire state for one organization policy, "
                "including template sections, questions, and saved answers"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {
                        "type": "string",
                        "description": "The organization policy ID",
                    },
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_patch_org_policy_qa",
            description=(
                "Update organization policy questionnaire answers. "
                "Accepts a list of question_id/answer pairs to apply as partial updates. "
                "IMPORTANT: Before drafting answers, research the local workspace — read "
                "source code, config files, existing policy documents, and infrastructure "
                "definitions to ground answers in observable facts. Do not invent "
                "organizational facts or procedures. Ask the user for clarification "
                "on anything that cannot be determined from the workspace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {
                        "type": "string",
                        "description": "The organization policy ID",
                    },
                    "updates": {
                        "type": "array",
                        "description": "List of question/answer updates to apply",
                        "items": {
                            "type": "object",
                            "properties": {
                                "question_id": {
                                    "type": "string",
                                    "description": "The policy question ID",
                                },
                                "answer": {
                                    "type": "string",
                                    "description": "The updated answer text",
                                },
                            },
                            "required": ["question_id", "answer"],
                        },
                    },
                },
                "required": ["policy_id", "updates"],
            },
        ),
        Tool(
            name="pretorin_update_narrative",
            description="Push a narrative text update for a control implementation",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
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
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["control_id", "narrative"],
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
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "content": {
                        "type": "string",
                        "description": "Note content (suggestions, manual steps, integration guidance)",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["control_id", "content"],
            },
        ),
        Tool(
            name="pretorin_resolve_control_note",
            description=(
                "Resolve, unresolve, or update an existing control note."
                " Use this to clear blocking notes so control status can advance."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "note_id": {
                        "type": "string",
                        "description": "ID of the note to resolve or update",
                    },
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "is_resolved": {
                        "type": "boolean",
                        "description": "Whether to mark the note resolved (true) or reopen it (false)",
                        "default": True,
                    },
                    "content": {
                        "type": "string",
                        "description": "Optional: updated note content",
                    },
                    "is_pinned": {
                        "type": "boolean",
                        "description": "Optional: whether the note is pinned",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["control_id", "note_id"],
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
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
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
                    "system_id": system_id_property(optional=True),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Optional: Framework ID; defaults to active scope",
                    },
                    "allow_scope_override": allow_scope_override_property(),
                    "allow_unverified_sources": allow_unverified_sources_property(),
                },
                "required": ["control_id"],
            },
        ),
        # === Agentic Workflow Tools ===
        Tool(
            name="pretorin_get_workflow_state",
            description=(
                "Use this FIRST when starting a compliance workflow. Returns the lifecycle state "
                "for a system+framework: which stage needs work (scope, policies, controls, evidence), "
                "what the next action is, and progress counts. Lightweight — no content, just status."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID for this workflow context"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_pending_scope_questions",
            description=(
                "Use this to see which scope questions still need answers. Returns only unanswered "
                "questions — much smaller than the full scope dump. Call get_scope_question_detail "
                "for guidance on a specific question.\n\n"
                "WORKFLOW: After fetching pending questions, explore the local workspace (source code, "
                "config files, infrastructure definitions, documentation) to gather evidence. Answer as "
                "many questions as possible from workspace evidence WITHOUT asking the user. Only use "
                "interview mode (see answer_scope_question) for genuine gaps that require organizational "
                "knowledge not present in the workspace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_scope_question_detail",
            description=(
                "Use this BEFORE answering a specific scope question. Returns guidance, tips, "
                "example responses, and the current answer for ONE question. Pull only when ready to answer."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "question_id": {"type": "string", "description": "Question ID from the pending list"},
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "question_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_answer_scope_question",
            description=(
                "Answer one scope question. IMPORTANT: Before answering, you MUST "
                "(1) call get_scope_question_detail for guidance, and "
                "(2) research the local workspace — read source code, config files, "
                "infrastructure definitions, and documentation to ground your answer in "
                "observable facts. Do not invent organizational facts, system names, "
                "network topologies, or boundaries.\n\n"
                "ANSWER-FIRST MODE — answer as many questions as possible directly from workspace "
                "evidence without involving the user. Submit these answers silently.\n\n"
                "INTERVIEW MODE — only for questions that require organizational knowledge not "
                "present in the workspace (e.g., role assignments, review frequencies, policy "
                "decisions, org-specific processes). Do NOT ask about things you can observe in "
                "code, config, CI, or docs. When you must ask, use this format:\n\n"
                "── Scope Question [N of TOTAL] ──────────────────\n"
                "[Short clarifying question — what you specifically need to know]\n\n"
                "  Context: [1 sentence on what you already found]\n\n"
                "  Suggested answers:\n"
                "    a) [likely option]\n"
                "    b) [alternative]\n"
                "    c) Other\n"
                "──────────────────────────────────────────────────\n\n"
                "Present ONE clarifying question at a time. Wait for the user's response, "
                "compose the final answer combining their input with workspace evidence, "
                "submit it, then move on."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "question_id": {"type": "string", "description": "Question ID to answer"},
                    "answer": {"type": "string", "description": "The answer text. Set to null to clear."},
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "question_id", "answer", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_trigger_scope_generation",
            description=(
                "Trigger AI generation of the scope document from answered questions. Returns a job ID "
                "for polling. Use AFTER answering scope questions. Poll get_scope_review_results with the "
                "job_id until status is 'succeeded'."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_trigger_scope_review",
            description=(
                "Trigger AI review of scope answers. Returns a job ID for polling. "
                "Use to check answer quality BEFORE or AFTER generation. "
                "Poll get_scope_review_results with the job_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_scope_review_results",
            description=(
                "Poll for scope generation or review results. Returns structured findings with "
                "severity, affected question IDs, and recommended fixes. Status will be 'queued', "
                "'running', 'succeeded', or 'failed'. Poll every 2 seconds until done."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "job_id": {
                        "type": "string",
                        "description": "Job ID from trigger_scope_generation or trigger_scope_review",
                    },
                },
                "required": ["system_id", "job_id"],
            },
        ),
        Tool(
            name="pretorin_get_pending_policy_questions",
            description=(
                "Use this to see which policy questions still need answers. Returns only unanswered "
                "questions — much smaller than the full policy questionnaire dump.\n\n"
                "WORKFLOW: After fetching pending questions, explore the local workspace (source code, "
                "config files, existing policy documents, infrastructure definitions, documentation) to "
                "gather evidence. Answer as many questions as possible from workspace evidence WITHOUT "
                "asking the user. Only use gap questions (see answer_policy_question) for genuine gaps "
                "that require organizational knowledge not present in the workspace."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_get_policy_question_detail",
            description=(
                "Use this BEFORE answering a specific policy question. Returns guidance, tips, "
                "and the current answer for ONE question."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                    "question_id": {"type": "string", "description": "Question ID from the pending list"},
                },
                "required": ["policy_id", "question_id"],
            },
        ),
        Tool(
            name="pretorin_answer_policy_question",
            description=(
                "Answer one policy question. IMPORTANT: Before answering, you MUST "
                "(1) call get_policy_question_detail for guidance, and "
                "(2) research the local workspace — read source code, config files, existing "
                "policy documents, infrastructure definitions, and documentation to ground "
                "your answer in observable facts. Do not invent organizational facts, role "
                "titles, URLs, procedures, or policies.\n\n"
                "ANSWER-FIRST MODE — answer as many questions as possible directly from workspace "
                "evidence without involving the user. Submit these answers silently.\n\n"
                "GAP QUESTIONS — only for questions that require organizational knowledge not "
                "present in the workspace (e.g., role assignments, review frequencies, policy "
                "decisions, org-specific processes). Do NOT ask about things you can observe in "
                "code, config, CI, or docs. When you must ask, use this format:\n\n"
                "── Gap Question [N of TOTAL gaps] ──────────────────\n"
                "[Short clarifying question — what you specifically need to know]\n\n"
                "  Context: [1 sentence on what you already found]\n\n"
                "  Suggested answers:\n"
                "    a) [likely option]\n"
                "    b) [alternative]\n"
                "    c) Other\n"
                "──────────────────────────────────────────────────\n\n"
                "Present ONE gap question at a time. Wait for the user's response, "
                "compose the final answer combining their input with workspace evidence, "
                "submit it, then move on."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                    "question_id": {"type": "string", "description": "Question ID to answer"},
                    "answer": {"type": "string", "description": "The answer text. Set to null to clear."},
                },
                "required": ["policy_id", "question_id", "answer"],
            },
        ),
        Tool(
            name="pretorin_trigger_policy_generation",
            description=(
                "Trigger AI generation of the policy document from answered questions. Returns a job ID. "
                "Use AFTER answering policy questions. Optionally provide system_id for scope context."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                    "system_id": {"type": "string", "description": "Optional: system ID for scope context"},
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_trigger_policy_review",
            description=(
                "Trigger AI review of policy answers/document. Returns a job ID for polling. "
                "Poll get_policy_review_results with the job_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_get_policy_review_results",
            description=(
                "Poll for policy generation or review results. Returns structured findings. "
                "Status: 'queued', 'running', 'succeeded', or 'failed'. Poll every 2 seconds."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                    "job_id": {
                        "type": "string",
                        "description": "Job ID from trigger_policy_generation or trigger_policy_review",
                    },
                },
                "required": ["policy_id", "job_id"],
            },
        ),
        Tool(
            name="pretorin_get_policy_workflow_state",
            description=(
                "Get per-policy workflow state: how many questions answered, whether the document "
                "is generated, review status, and the recommended next action."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_get_pending_families",
            description=(
                "Get control families that need work. Returns family IDs with counts of pending "
                "vs total controls. Use to decide which family to work on next."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_family_bundle",
            description=(
                "Get all controls in a family with their status, narrative presence, evidence presence, "
                "and notes count. Use to understand the state of a family before working on it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "family_id": {
                        "type": "string",
                        "description": (
                            "Canonical control family ID for this framework "
                            "(e.g. 'access-control' for NIST/FedRAMP, 'CC6' for SOC 2, "
                            "'access-control-level-2' for CMMC). Use "
                            "`pretorin_list_control_families` to list valid values."
                        ),
                    },
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "family_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_trigger_family_review",
            description=(
                "Trigger AI review for all controls in a family. Reviews each control sequentially "
                "and returns aggregated findings. May take 2-4 minutes for large families. "
                "Poll get_family_review_results with the job_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "family_id": {
                        "type": "string",
                        "description": (
                            "Canonical control family ID for this framework "
                            "(e.g. 'access-control' for NIST/FedRAMP, 'CC6' for SOC 2). "
                            "Use `pretorin_list_control_families` to list valid values."
                        ),
                    },
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "family_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_family_review_results",
            description=(
                "Poll for family review results. Returns per-control findings with severity, "
                "affected control IDs, and recommended fixes."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "job_id": {"type": "string", "description": "Job ID from trigger_family_review"},
                },
                "required": ["system_id", "job_id"],
            },
        ),
        Tool(
            name="pretorin_get_analytics_summary",
            description=(
                "Get a full system progress snapshot: scope completion, policy completion, "
                "control narrative/evidence coverage, and evidence gaps. Lightweight — "
                "returns counts only, no content. Use to decide what needs attention."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_family_analytics",
            description=(
                "Get per-family breakdown: narrative coverage, evidence coverage, open notes, "
                "status distribution for each control family in scope."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "framework_id": {"type": "string", "description": "Framework ID"},
                },
                "required": ["system_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_policy_analytics",
            description=(
                "Get per-policy analytics: question completion, document generation status, "
                "review status. Use to understand one policy's progress."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "policy_id": {"type": "string", "description": "Organization policy ID"},
                },
                "required": ["policy_id"],
            },
        ),
        Tool(
            name="pretorin_prepare_campaign",
            description=(
                "Prepare a workflow-aligned campaign run and create or attach to a local checkpoint "
                "that external agents can use for drafting, submission, and apply operations."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "enum": ["controls", "policy", "scope"]},
                    "mode": {"type": "string", "description": "Campaign mode for the selected domain"},
                    "apply": {"type": "boolean", "default": False},
                    "output": {"type": "string", "enum": ["auto", "live", "compact", "json"], "default": "json"},
                    "checkpoint_path": {"type": "string", "description": "Optional local checkpoint file path"},
                    "working_directory": {"type": "string", "description": "Optional working directory for executors"},
                    "concurrency": {"type": "integer", "default": 4},
                    "max_retries": {"type": "integer", "default": 2},
                    "system_id": system_id_property(optional=True),
                    "framework_id": {"type": "string", "description": "Optional framework ID"},
                    "family_id": {
                        "type": "string",
                        "description": (
                            "Optional control family selector. Accepts canonical ID or abbreviation "
                            "(case-insensitive). e.g. 'AC' or 'access-control' for NIST/FedRAMP, "
                            "'CC6' for SOC 2, 'AC-L2' for CMMC. "
                            "Use `pretorin_list_control_families` to list valid values per framework."
                        ),
                    },
                    "control_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit control IDs",
                    },
                    "all_controls": {"type": "boolean", "default": False},
                    "artifacts": {"type": "string", "enum": ["narratives", "evidence", "both"], "default": "both"},
                    "review_job": {"type": "string", "description": "Family review job id for controls review-fix"},
                    "policy_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional explicit policy IDs",
                    },
                    "all_incomplete": {"type": "boolean", "default": False},
                },
                "required": ["domain", "mode"],
            },
        ),
        Tool(
            name="pretorin_claim_campaign_items",
            description=(
                "Claim prepared campaign items for drafting. Use leases to safely fan out work "
                "across multiple external agents or subagents."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string", "description": "Local campaign checkpoint path"},
                    "max_items": {"type": "integer", "default": 1},
                    "lease_owner": {"type": "string", "description": "Stable identifier for the claiming agent"},
                    "lease_ttl_seconds": {"type": "integer", "default": 300},
                },
                "required": ["checkpoint_path"],
            },
        ),
        Tool(
            name="pretorin_get_campaign_item_context",
            description=(
                "Fetch one claimed campaign item's full platform context and drafting instructions "
                "for an external agent to produce a proposal."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string", "description": "Local campaign checkpoint path"},
                    "item_id": {"type": "string", "description": "Campaign item id to inspect"},
                },
                "required": ["checkpoint_path", "item_id"],
            },
        ),
        Tool(
            name="pretorin_submit_campaign_proposal",
            description=("Persist one external-agent proposal onto a prepared campaign item without applying it yet."),
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string", "description": "Local campaign checkpoint path"},
                    "item_id": {"type": "string", "description": "Campaign item id to update"},
                    "proposal": {"type": "object", "description": "Campaign proposal payload"},
                },
                "required": ["checkpoint_path", "item_id", "proposal"],
            },
        ),
        Tool(
            name="pretorin_apply_campaign",
            description=(
                "Apply stored campaign proposals back into Pretorin workflow records using the platform "
                "as the source of truth."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string", "description": "Local campaign checkpoint path"},
                    "item_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional subset of item ids to apply",
                    },
                },
                "required": ["checkpoint_path"],
            },
        ),
        Tool(
            name="pretorin_get_campaign_status",
            description=(
                "Return structured campaign counts, recent events, active claims, failures, and a stable "
                "plain-text snapshot suitable for agent transcripts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "checkpoint_path": {"type": "string", "description": "Local campaign checkpoint path"},
                },
                "required": ["checkpoint_path"],
            },
        ),
        # === Vendor Management Tools ===
        Tool(
            name="pretorin_list_vendors",
            description="List all vendor/provider entities for the organization.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="pretorin_create_vendor",
            description=(
                "Create a new vendor entity. Required: name, provider_type"
                " (csp, saas, managed_service, internal). Optional: description, authorization_level."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Vendor name",
                    },
                    "provider_type": {
                        "type": "string",
                        "enum": ["csp", "saas", "managed_service", "internal"],
                        "description": "Type of provider",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional vendor description",
                    },
                    "authorization_level": {
                        "type": "string",
                        "description": "Optional authorization level (e.g., FedRAMP High P-ATO)",
                    },
                },
                "required": ["name", "provider_type"],
            },
        ),
        Tool(
            name="pretorin_get_vendor",
            description="Get detailed information about a specific vendor.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID",
                    },
                },
                "required": ["vendor_id"],
            },
        ),
        Tool(
            name="pretorin_update_vendor",
            description="Update vendor fields (name, description, provider_type, authorization_level).",
            inputSchema={
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID",
                    },
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "provider_type": {
                        "type": "string",
                        "enum": ["csp", "saas", "managed_service", "internal"],
                    },
                    "authorization_level": {"type": "string"},
                },
                "required": ["vendor_id"],
            },
        ),
        Tool(
            name="pretorin_delete_vendor",
            description="Delete a vendor entity.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID",
                    },
                },
                "required": ["vendor_id"],
            },
        ),
        Tool(
            name="pretorin_upload_vendor_document",
            description=(
                "Upload a vendor evidence document (SOC 2 report, CRM, FedRAMP package, etc)."
                " Provide the file_path on the local filesystem."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Local file path to upload",
                    },
                    "name": {
                        "type": "string",
                        "description": "Document display name",
                    },
                    "description": {
                        "type": "string",
                        "description": "Document description",
                    },
                    "attestation_type": {
                        "type": "string",
                        "enum": ["self_attested", "third_party_attestation", "vendor_provided"],
                        "description": "Default: vendor_provided",
                    },
                },
                "required": ["vendor_id", "file_path"],
            },
        ),
        Tool(
            name="pretorin_list_vendor_documents",
            description="List evidence documents linked to a vendor.",
            inputSchema={
                "type": "object",
                "properties": {
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID",
                    },
                },
                "required": ["vendor_id"],
            },
        ),
        Tool(
            name="pretorin_link_evidence_to_vendor",
            description="Link existing evidence to a vendor. Set vendor_id to null to unlink.",
            inputSchema={
                "type": "object",
                "properties": {
                    "evidence_id": {
                        "type": "string",
                        "description": "Evidence item ID",
                    },
                    "vendor_id": {
                        "type": "string",
                        "description": "Vendor ID (null to unlink)",
                    },
                    "attestation_type": {
                        "type": "string",
                        "enum": ["self_attested", "third_party_attestation", "vendor_provided"],
                    },
                },
                "required": ["evidence_id"],
            },
        ),
        Tool(
            name="pretorin_get_control_responsibility",
            description=(
                "Get the inheritance/responsibility edge for a control."
                " Shows if it's inherited, shared, or system-specific."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Framework ID",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_set_control_responsibility",
            description=(
                "Create or update an inheritance edge for a control."
                " Set responsibility_mode to 'inherited' or 'shared',"
                " with source_type and optional vendor_id."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Framework ID",
                    },
                    "responsibility_mode": {
                        "type": "string",
                        "enum": ["inherited", "shared"],
                        "description": "How this control is handled",
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["provider", "internal", "hybrid"],
                        "description": "Source of the inheritance",
                    },
                    "vendor_id": {
                        "type": "string",
                        "description": "Optional: vendor providing the inherited control",
                    },
                },
                "required": ["system_id", "control_id", "framework_id", "responsibility_mode"],
            },
        ),
        Tool(
            name="pretorin_remove_control_responsibility",
            description="Remove an inheritance edge, making the control system-specific.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Framework ID",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        Tool(
            name="pretorin_get_stale_edges",
            description=(
                "List controls with stale inheritance — the source narrative changed"
                " but the inherited control hasn't been updated."
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
            name="pretorin_sync_stale_edges",
            description="Bulk sync all stale inherited controls from their source narratives.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_generate_inheritance_narrative",
            description=(
                "AI-generate a grounded inheritance narrative for a control,"
                " using the vendor's evidence and documentation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "control_id": control_id_property(),
                    "framework_id": {
                        "type": "string",
                        "description": "Framework ID",
                    },
                },
                "required": ["system_id", "control_id", "framework_id"],
            },
        ),
        # === STIG / CCI Tools ===
        Tool(
            name="pretorin_list_stigs",
            description="List STIG benchmarks with optional filters by technology area or product.",
            inputSchema={
                "type": "object",
                "properties": {
                    "technology_area": {
                        "type": "string",
                        "description": "Filter by technology area",
                    },
                    "product": {
                        "type": "string",
                        "description": "Filter by product name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_stig",
            description="Get single STIG benchmark detail by ID including title, version, and release info.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stig_id": {
                        "type": "string",
                        "description": "The STIG benchmark ID",
                    },
                },
                "required": ["stig_id"],
            },
        ),
        Tool(
            name="pretorin_list_stig_rules",
            description="List rules for a STIG benchmark with optional severity and CCI filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stig_id": {
                        "type": "string",
                        "description": "The STIG benchmark ID",
                    },
                    "severity": {
                        "type": "string",
                        "description": "Filter by severity (high, medium, low)",
                    },
                    "cci_id": {
                        "type": "string",
                        "description": "Filter by CCI identifier",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0,
                    },
                },
                "required": ["stig_id"],
            },
        ),
        Tool(
            name="pretorin_get_stig_rule",
            description="Get full detail for a single STIG rule including CCIs, check text, and fix text.",
            inputSchema={
                "type": "object",
                "properties": {
                    "stig_id": {
                        "type": "string",
                        "description": "The STIG benchmark ID",
                    },
                    "rule_id": {
                        "type": "string",
                        "description": "The STIG rule ID",
                    },
                },
                "required": ["stig_id", "rule_id"],
            },
        ),
        Tool(
            name="pretorin_list_ccis",
            description="List CCI items with optional filters by NIST control ID or status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "nist_control_id": {
                        "type": "string",
                        "description": "Filter by NIST control ID (e.g., AC-2)",
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by CCI status",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results to return",
                        "default": 100,
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0,
                    },
                },
                "required": [],
            },
        ),
        Tool(
            name="pretorin_get_cci",
            description="Get CCI detail with linked SRGs and STIG rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "cci_id": {
                        "type": "string",
                        "description": "The CCI identifier (e.g., CCI-000015)",
                    },
                },
                "required": ["cci_id"],
            },
        ),
        Tool(
            name="pretorin_get_cci_chain",
            description="Get full traceability chain for a NIST control: Control -> CCIs -> SRGs -> STIG rules.",
            inputSchema={
                "type": "object",
                "properties": {
                    "nist_control_id": {
                        "type": "string",
                        "description": "The NIST control ID (e.g., AC-2)",
                    },
                },
                "required": ["nist_control_id"],
            },
        ),
        Tool(
            name="pretorin_get_test_manifest",
            description="Get the test manifest for CLI scan execution against a system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "stig_id": {
                        "type": "string",
                        "description": "Optional STIG benchmark ID to scope the manifest",
                    },
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_submit_test_results",
            description="Upload STIG scan results from a CLI scan run.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "cli_run_id": {
                        "type": "string",
                        "description": "The CLI scan run identifier",
                    },
                    "results": {
                        "type": "array",
                        "description": "Array of test result objects",
                        "items": {
                            "type": "object",
                        },
                    },
                    "cli_version": {
                        "type": "string",
                        "description": "Optional CLI version string",
                    },
                },
                "required": ["system_id", "cli_run_id", "results"],
            },
        ),
        Tool(
            name="pretorin_get_stig_applicability",
            description="Get which STIGs apply to a system based on its profile.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_get_cci_status",
            description="Get CCI-level compliance rollup for a system, optionally filtered by NIST control.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                    "nist_control_id": {
                        "type": "string",
                        "description": "Optional NIST control ID to filter (e.g., AC-2)",
                    },
                },
                "required": ["system_id"],
            },
        ),
        Tool(
            name="pretorin_infer_stigs",
            description="AI-infer applicable STIGs from a system's profile.",
            inputSchema={
                "type": "object",
                "properties": {
                    "system_id": system_id_property(),
                },
                "required": ["system_id"],
            },
        ),
        # Recipe execution context lifecycle (recipe-implementation WS2 Phase B)
        Tool(
            name="pretorin_start_recipe",
            description=(
                "Open a recipe execution context. Returns a context_id the caller passes "
                "on subsequent platform-API write tool calls so audit metadata is stamped "
                "with producer_kind='recipe' automatically. One recipe per session at a "
                "time (nesting forbidden in v1). Contexts auto-expire after 1 hour of "
                "inactivity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "Recipe id (must be loadable from the registry)",
                    },
                    "recipe_version": {
                        "type": "string",
                        "description": (
                            "Recipe version the caller intends to run. Cross-checked "
                            "against the loaded recipe; mismatch is an error."
                        ),
                    },
                    "params": {
                        "type": "object",
                        "description": (
                            "Inputs the calling agent supplies, validated against the recipe's params schema."
                        ),
                    },
                    "selection": {
                        "type": "object",
                        "description": (
                            "Structured RecipeSelection record from the engagement layer. "
                            "Stored on the context for the eventual RecipeResult."
                        ),
                    },
                },
                "required": ["recipe_id", "recipe_version"],
            },
        ),
        Tool(
            name="pretorin_end_recipe",
            description=(
                "Close a recipe execution context and return the RecipeResult summary "
                "(status, evidence and narrative counts, errors, elapsed time). "
                "Must be called once the recipe's work is complete; failure to call "
                "leaves the context in place until the 1-hour expiry sweep."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "context_id": {
                        "type": "string",
                        "description": "Context id returned by pretorin_start_recipe",
                    },
                    "status": {
                        "type": "string",
                        "enum": ["pass", "fail", "needs_input"],
                        "description": "Caller-supplied disposition (defaults to 'pass')",
                        "default": "pass",
                    },
                },
                "required": ["context_id"],
            },
        ),
        Tool(
            name="pretorin_list_recipes",
            description=(
                "List loaded recipes with their summary metadata (id, name, tier, "
                "description, use_when, produces). Filter by tier and/or produces. "
                "Use this to discover which recipes are available, then call "
                "pretorin_get_recipe(id) to read the full body."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "tier": {
                        "type": "string",
                        "enum": ["official", "partner", "community"],
                        "description": "Filter to one tier",
                    },
                    "produces": {
                        "type": "string",
                        "enum": ["evidence", "narrative", "both", "answers"],
                        "description": "Filter by what the recipe produces",
                    },
                },
            },
        ),
        Tool(
            name="pretorin_get_recipe",
            description=(
                "Return one recipe's full manifest and body. The body is the markdown "
                "playbook the calling agent reads to understand the procedure."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "recipe_id": {
                        "type": "string",
                        "description": "Recipe id to fetch",
                    },
                },
                "required": ["recipe_id"],
            },
        ),
        Tool(
            name="pretorin_list_workflows",
            description=(
                "List loaded workflow playbooks (single-control, scope-question, "
                "policy-question, campaign). Each workflow describes how to iterate "
                "items in its domain and which recipes to pick per item. Use this "
                "before picking a recipe so the agent works at the right granularity."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "iterates_over": {
                        "type": "string",
                        "enum": [
                            "single_control",
                            "scope_questions",
                            "policy_questions",
                            "campaign_items",
                        ],
                        "description": "Filter to one item-iteration shape",
                    },
                },
            },
        ),
        Tool(
            name="pretorin_get_workflow",
            description=(
                "Return one workflow's full manifest and body. The body is the markdown "
                "playbook the calling agent reads to know how to iterate items and "
                "pick recipes per item in this workflow's domain."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "Workflow id to fetch",
                    },
                },
                "required": ["workflow_id"],
            },
        ),
        Tool(
            name="pretorin_start_task",
            description=(
                "Route a user prompt to the right workflow. Call this FIRST whenever "
                "the user references compliance work (a control, system, framework, "
                "questionnaire, or campaign). The calling agent extracts entities "
                "from the user prompt and supplies them as structured args; pretorin "
                "applies deterministic rules to pick a workflow and bundles the "
                "platform read-state (workflow_state, compliance_status, pending "
                "items) into the response. The agent then reads the selected "
                "workflow's body via pretorin_get_workflow and follows it."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "entities": {
                        "type": "object",
                        "description": (
                            "Structured entities extracted from the user prompt. "
                            "intent_verb and raw_prompt are required; everything "
                            "else is optional and only populated when the user "
                            "actually named it."
                        ),
                        "properties": {
                            "intent_verb": {
                                "type": "string",
                                "enum": [
                                    "work_on",
                                    "collect_evidence",
                                    "draft_narrative",
                                    "answer",
                                    "campaign",
                                    "inspect_status",
                                ],
                                "description": ("What the user wants to do at a high level."),
                            },
                            "raw_prompt": {
                                "type": "string",
                                "description": "Original user prompt verbatim, for audit.",
                            },
                            "system_id": {
                                "type": "string",
                                "description": ("System name or id the user named (None if absent)."),
                            },
                            "framework_id": {
                                "type": "string",
                                "description": ("Framework id the user named, e.g. 'nist-800-53-r5'."),
                            },
                            "control_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": (
                                    "Explicit control ids the user mentioned, "
                                    "lowercase normalized (e.g., ['ac-2', 'ac-3'])."
                                ),
                            },
                            "scope_question_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific scope question ids if named.",
                            },
                            "policy_question_ids": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific policy question ids if named.",
                            },
                        },
                        "required": ["intent_verb", "raw_prompt"],
                    },
                    "active_system_id": {
                        "type": "string",
                        "description": (
                            "The user's active CLI context system_id, if any. "
                            "Used to detect cross-system writes — when the resolved "
                            "system doesn't match this, the response is ambiguous."
                        ),
                    },
                    "skip_inspect": {
                        "type": "boolean",
                        "description": (
                            "Skip the server-side platform reads. Use when the calling agent already has fresh state."
                        ),
                        "default": False,
                    },
                },
                "required": ["entities"],
            },
        ),
    ]


def _recipe_script_tools() -> list[Tool]:
    """Generate one MCP Tool per script across every loaded recipe.

    Per Phase C: each ``ScriptDecl`` in each recipe's manifest becomes a
    callable MCP tool named ``pretorin_recipe_<safe_id>__<tool_name>`` with
    ``inputSchema`` built from the script's declared params.

    Tools are listed regardless of whether a recipe context is currently
    active — calling one without an active matching context returns a clear
    error from ``handle_run_recipe_script``.
    """
    # Local import: this module is imported at MCP startup but the recipe
    # registry walks the filesystem, which we don't want at import time.
    from pretorin.recipes.registry import RecipeRegistry, script_tool_name

    tools: list[Tool] = []
    registry = RecipeRegistry()
    for entry in registry.entries():
        manifest = entry.active.manifest
        for script_name, script_decl in manifest.scripts.items():
            tool_name = script_tool_name(manifest.id, script_name)
            input_schema = _params_to_input_schema(script_decl.params)
            tools.append(
                Tool(
                    name=tool_name,
                    description=(
                        f"[Recipe {manifest.id} ({manifest.tier})] {script_decl.description}\n\n"
                        "Requires an active recipe execution context for this recipe "
                        "(call pretorin_start_recipe first)."
                    ),
                    inputSchema=input_schema,
                )
            )
    return tools


def _params_to_input_schema(params: dict[str, Any]) -> dict[str, Any]:
    """Convert a ``ScriptDecl.params`` mapping to a JSON Schema inputSchema.

    Each ``RecipeParam`` declares ``type`` (string / array / boolean / integer
    / number), an optional ``items`` for arrays, ``description``, ``default``,
    and ``required``. The MCP ``inputSchema`` mirrors that.
    """
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    for name, param in params.items():
        # ``param`` is a RecipeParam pydantic model; serialise to dict for
        # JSON Schema. Drop None-valued optional keys for cleanliness.
        param_dict = param.model_dump() if hasattr(param, "model_dump") else dict(param)
        prop: dict[str, Any] = {"type": param_dict["type"]}
        if param_dict.get("items"):
            prop["items"] = param_dict["items"]
        if param_dict.get("description"):
            prop["description"] = param_dict["description"]
        if param_dict.get("default") is not None:
            prop["default"] = param_dict["default"]
        properties[name] = prop
        if param_dict.get("required"):
            required.append(name)
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema
