"""MCP tool handler dispatch table."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.handlers.compliance import (
    handle_add_control_note,
    handle_generate_control_artifacts,
    handle_get_control_context,
    handle_get_control_implementation,
    handle_get_control_notes,
    handle_get_scope,
    handle_push_monitoring_event,
    handle_update_control_status,
    handle_update_narrative,
)
from pretorin.mcp.handlers.evidence import (
    handle_create_evidence,
    handle_create_evidence_batch,
    handle_get_narrative,
    handle_link_evidence,
    handle_search_evidence,
)
from pretorin.mcp.handlers.frameworks import (
    handle_get_control,
    handle_get_control_references,
    handle_get_controls_batch,
    handle_get_document_requirements,
    handle_get_framework,
    handle_list_control_families,
    handle_list_controls,
    handle_list_frameworks,
)
from pretorin.mcp.handlers.systems import (
    handle_get_compliance_status,
    handle_get_system,
    handle_list_systems,
)

ToolHandler = Callable[[PretorianClient, dict[str, Any]], Awaitable[list[TextContent] | CallToolResult]]

TOOL_HANDLERS: dict[str, ToolHandler] = {
    "pretorin_list_frameworks": handle_list_frameworks,
    "pretorin_get_framework": handle_get_framework,
    "pretorin_list_control_families": handle_list_control_families,
    "pretorin_list_controls": handle_list_controls,
    "pretorin_get_control": handle_get_control,
    "pretorin_get_controls_batch": handle_get_controls_batch,
    "pretorin_get_control_references": handle_get_control_references,
    "pretorin_get_document_requirements": handle_get_document_requirements,
    "pretorin_list_systems": handle_list_systems,
    "pretorin_get_system": handle_get_system,
    "pretorin_get_compliance_status": handle_get_compliance_status,
    "pretorin_search_evidence": handle_search_evidence,
    "pretorin_create_evidence": handle_create_evidence,
    "pretorin_create_evidence_batch": handle_create_evidence_batch,
    "pretorin_link_evidence": handle_link_evidence,
    "pretorin_get_narrative": handle_get_narrative,
    "pretorin_generate_control_artifacts": handle_generate_control_artifacts,
    "pretorin_push_monitoring_event": handle_push_monitoring_event,
    "pretorin_add_control_note": handle_add_control_note,
    "pretorin_get_control_notes": handle_get_control_notes,
    "pretorin_update_control_status": handle_update_control_status,
    "pretorin_get_control_implementation": handle_get_control_implementation,
    "pretorin_get_control_context": handle_get_control_context,
    "pretorin_get_scope": handle_get_scope,
    "pretorin_update_narrative": handle_update_narrative,
}
