"""Handlers for evidence and narrative retrieval tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.client import PretorianClient
from pretorin.client.models import EvidenceBatchItemCreate
from pretorin.evidence.audit_metadata import build_agent_metadata, evidence_type_to_source_type
from pretorin.evidence.types import normalize_evidence_type
from pretorin.mcp.helpers import (
    format_error,
    format_json,
    require,
    resolve_execution_scope,
    safe_args,
)
from pretorin.utils import normalize_control_id
from pretorin.workflows.compliance_updates import upsert_evidence

logger = logging.getLogger(__name__)

# Alias for backward compatibility within this module.
_safe_args = safe_args

# Producer id for writes coming through the MCP server. The actual calling agent
# (Claude Code, Codex CLI, custom client) is not directly observable from inside
# the MCP handler today; "mcp-agent" identifies the channel rather than a specific
# agent. v1.5+ may extend this once MCP exposes calling-agent metadata.
_MCP_AGENT_ID = "mcp-agent"


async def handle_search_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the search_evidence tool."""
    logger.debug("handle_search_evidence called with %s", _safe_args(arguments))
    system_id, framework_id, normalized_control_id = await resolve_execution_scope(client, arguments)
    evidence = await client.list_evidence(
        system_id=system_id,
        framework_id=framework_id,
        control_id=normalized_control_id,
        limit=arguments.get("limit", 20),
    )
    return format_json(
        {
            "total": len(evidence),
            "system_id": system_id,
            "framework_id": framework_id,
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


async def handle_create_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the create_evidence tool."""
    logger.debug("handle_create_evidence called with %s", _safe_args(arguments))
    err = require(arguments, "name", "description", "evidence_type")
    if err:
        return format_error(err)

    # Issue #79: run AI-drift normalizer before the payload hits pydantic.
    # Canonical values pass straight through; aliases and typos are mapped.
    evidence_type = normalize_evidence_type(arguments.get("evidence_type")).value

    dedupe = arguments.get("dedupe", True)
    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        enforce_active_context=True,
    )
    code_context = {}
    for key in ("code_file_path", "code_line_numbers", "code_snippet", "code_repository", "code_commit_hash"):
        val = arguments.get(key)
        if val:
            code_context[key] = val

    description = arguments.get("description", "")
    # WS1b: stamp agent-driven audit metadata. source_uri is a file:// when the
    # caller supplied a code_file_path, else a pretorin:// sentinel for the
    # platform context.
    audit_source_uri = (
        f"file://{code_context['code_file_path']}"
        if "code_file_path" in code_context
        else (
            f"pretorin://systems/{system_id}/controls/{normalized_control_id}"
            if normalized_control_id
            else f"pretorin://systems/{system_id}/untargeted"
        )
    )
    audit = build_agent_metadata(
        body=description,
        source_uri=audit_source_uri,
        source_type=evidence_type_to_source_type(evidence_type),
        agent_id=_MCP_AGENT_ID,
        source_version=code_context.get("code_commit_hash"),
    )

    try:
        result = await upsert_evidence(
            client,
            system_id=system_id,
            name=arguments.get("name", ""),
            description=description,
            evidence_type=evidence_type,
            control_id=normalized_control_id,
            framework_id=framework_id,
            source="cli",
            dedupe=bool(dedupe),
            code_context=code_context or None,
            audit_metadata=audit,
        )
    except ValueError as e:
        return format_error(str(e))
    payload = result.to_dict()
    payload["id"] = result.evidence_id
    return format_json(payload)


async def handle_create_evidence_batch(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the create_evidence_batch tool."""
    logger.debug("handle_create_evidence_batch called with %s", _safe_args(arguments))
    err = require(arguments, "items")
    if err:
        return format_error(err)

    system_id, framework_id, _ = await resolve_execution_scope(
        client,
        arguments,
        enforce_active_context=True,
    )
    items = arguments.get("items", [])
    payload_items = []
    for item in items:
        # Issue #79: normalize possibly-AI-generated evidence_type (aliases
        # and typos -> canonical; unknown or missing -> "other"). Pydantic
        # then enum-validates as the last-line defense.
        evidence_type = normalize_evidence_type(item.get("evidence_type")).value
        item_control_id = normalize_control_id(item["control_id"])
        # WS1b: per-item agent audit metadata.
        item_audit_source_uri = (
            f"file://{item['code_file_path']}"
            if item.get("code_file_path")
            else f"pretorin://systems/{system_id}/controls/{item_control_id}"
        )
        item_audit = build_agent_metadata(
            body=item["description"],
            source_uri=item_audit_source_uri,
            source_type=evidence_type_to_source_type(evidence_type),
            agent_id=_MCP_AGENT_ID,
            source_version=item.get("code_commit_hash"),
        )
        payload_items.append(
            EvidenceBatchItemCreate(
                name=item["name"],
                description=item["description"],
                control_id=item_control_id,
                evidence_type=evidence_type,
                relevance_notes=item.get("relevance_notes"),
                code_file_path=item.get("code_file_path"),
                code_line_numbers=item.get("code_line_numbers"),
                code_snippet=item.get("code_snippet"),
                code_repository=item.get("code_repository"),
                code_commit_hash=item.get("code_commit_hash"),
                audit_metadata=item_audit,
            )
        )

    result = await client.create_evidence_batch(system_id, framework_id, payload_items)
    return format_json(result.model_dump() if hasattr(result, "model_dump") else result)


async def handle_link_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the link_evidence tool."""
    logger.debug("handle_link_evidence called with %s", _safe_args(arguments))
    err = require(arguments, "evidence_id", "control_id")
    if err:
        return format_error(err)

    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        control_required=True,
        enforce_active_context=True,
    )
    result = await client.link_evidence_to_control(
        evidence_id=arguments["evidence_id"],
        control_id=normalized_control_id or "",
        system_id=system_id,
        framework_id=framework_id,
    )
    return format_json(result)


async def handle_upload_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the upload_evidence tool."""
    logger.debug("handle_upload_evidence called with %s", _safe_args(arguments))
    err = require(arguments, "file_path", "name")
    if err:
        return format_error(err)

    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        enforce_active_context=True,
    )
    try:
        result = await client.upload_evidence(
            system_id=system_id,
            file_path=arguments["file_path"],
            name=arguments["name"],
            evidence_type=arguments.get("evidence_type", "other"),
            description=arguments.get("description"),
            control_id=normalized_control_id,
            framework_id=framework_id,
        )
    except (ValueError, OSError) as e:
        return format_error(str(e))
    return format_json(result)


async def handle_delete_evidence(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the delete_evidence tool."""
    logger.debug("handle_delete_evidence called with %s", _safe_args(arguments))
    err = require(arguments, "evidence_id")
    if err:
        return format_error(err)

    system_id, _framework_id, _ = await resolve_execution_scope(
        client,
        arguments,
        enforce_active_context=True,
    )
    evidence_id = arguments["evidence_id"]
    await client.delete_evidence(system_id=system_id, evidence_id=evidence_id)
    return format_json({"evidence_id": evidence_id, "deleted": True})


async def handle_get_narrative(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent] | CallToolResult:
    """Handle the get_narrative tool."""
    logger.debug("handle_get_narrative called with %s", _safe_args(arguments))
    err = require(arguments, "control_id")
    if err:
        return format_error(err)

    system_id, framework_id, normalized_control_id = await resolve_execution_scope(
        client,
        arguments,
        control_required=True,
        enforce_active_context=True,
    )
    narrative = await client.get_narrative(
        system_id=system_id,
        control_id=normalized_control_id or "",
        framework_id=framework_id,
    )
    return format_json(
        {
            "control_id": narrative.control_id,
            "framework_id": narrative.framework_id,
            "system_id": system_id,
            "narrative": narrative.narrative,
            "ai_confidence_score": narrative.ai_confidence_score,
            "status": narrative.status,
        }
    )
