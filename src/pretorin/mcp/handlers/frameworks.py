"""Handlers for framework and control reference tools (read-only)."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import format_json
from pretorin.utils import normalize_control_id

logger = logging.getLogger(__name__)


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments with sensitive fields redacted."""
    return {k: ("***" if k == "api_key" else v) for k, v in arguments.items()}


async def handle_list_frameworks(client: PretorianClient, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle the list_frameworks tool."""
    logger.debug("handle_list_frameworks called with %s", _safe_args(arguments))
    result = await client.list_frameworks()
    return format_json(
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


async def handle_get_framework(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_framework tool."""
    logger.debug("handle_get_framework called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    framework = await client.get_framework(framework_id)
    return format_json(
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


async def handle_list_control_families(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_control_families tool."""
    logger.debug("handle_list_control_families called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    families = await client.list_control_families(framework_id)
    return format_json(
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


async def handle_list_controls(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_controls tool."""
    logger.debug("handle_list_controls called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    family_id = arguments.get("family_id")
    controls = await client.list_controls(framework_id, family_id)
    return format_json(
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


async def handle_get_control(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control tool."""
    logger.debug("handle_get_control called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    control_id = normalize_control_id(arguments.get("control_id", ""))
    control = await client.get_control(framework_id, control_id)
    return format_json(
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


async def handle_get_controls_batch(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_controls_batch tool."""
    logger.debug("handle_get_controls_batch called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    control_ids = arguments.get("control_ids")
    normalized_control_ids = [normalize_control_id(control_id) for control_id in control_ids] if control_ids else None
    controls = await client.get_controls_batch(framework_id, normalized_control_ids)
    return format_json(controls.model_dump() if hasattr(controls, "model_dump") else controls)


async def handle_get_control_references(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_references tool."""
    logger.debug("handle_get_control_references called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    control_id = normalize_control_id(arguments.get("control_id", ""))
    refs = await client.get_control_references(framework_id, control_id)
    return format_json(
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


async def handle_get_document_requirements(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_document_requirements tool."""
    logger.debug("handle_get_document_requirements called with %s", _safe_args(arguments))
    framework_id = arguments.get("framework_id", "")
    docs = await client.get_document_requirements(framework_id)
    return format_json(
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
