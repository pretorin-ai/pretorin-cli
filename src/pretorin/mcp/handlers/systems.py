"""Handlers for system management tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import TextContent

from pretorin.cli.version_check import get_update_status
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.mcp.helpers import format_json, resolve_system_id

logger = logging.getLogger(__name__)


def _safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments with sensitive fields redacted."""
    return {k: ("***" if k == "api_key" else v) for k, v in arguments.items()}


async def handle_list_systems(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_systems tool."""
    logger.debug("handle_list_systems called with %s", _safe_args(arguments))
    systems = await client.list_systems()
    result: dict[str, Any] = {
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
    if not systems:
        result["note"] = (
            "No systems found. Systems can only be created on the Pretorin platform "
            "(https://platform.pretorin.com) with a beta code. Pretorin is currently "
            "in closed beta — the user can sign up for early access at "
            "https://pretorin.com/early-access/. Without a system, framework and "
            "control browsing tools still work."
        )
    return format_json(result)


async def handle_get_system(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_system tool."""
    logger.debug("handle_get_system called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    system = await client.get_system(system_id)
    return format_json(
        {
            "id": system.id,
            "name": system.name,
            "description": system.description,
            "frameworks": system.frameworks,
            "security_impact_level": system.security_impact_level,
        }
    )


async def handle_get_compliance_status(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_compliance_status tool."""
    logger.debug("handle_get_compliance_status called with %s", _safe_args(arguments))
    system_id = await resolve_system_id(client, arguments)
    if system_id is None:
        raise PretorianClientError("system_id is required")
    status = await client.get_system_compliance_status(system_id)
    return format_json(status)


async def handle_get_source_manifest(
    client: PretorianClient | None,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_source_manifest tool."""
    from pretorin.attestation import evaluate_manifest, load_manifest, load_snapshot
    from pretorin.client.config import Config

    logger.debug("handle_get_source_manifest called with %s", _safe_args(arguments))

    config = Config()
    system_id = arguments.get("system_id") or config.active_system_id
    if not system_id:
        raise PretorianClientError(
            "No system_id provided and no active context set. Run 'pretorin context set' or pass system_id."
        )

    manifest = load_manifest(system_id)
    if manifest is None:
        return format_json(
            {
                "system_id": system_id,
                "manifest": None,
                "message": (
                    "No source manifest found. Create .pretorin/source-manifest.json "
                    "in your repo root, or set the PRETORIN_SOURCE_MANIFEST env var."
                ),
            }
        )

    result: dict[str, Any] = {
        "system_id": system_id,
        "version": manifest.version,
        "system_sources": [
            {"source_type": r.source_type, "level": r.level.value, "description": r.description}
            for r in manifest.system_sources
        ],
        "family_sources": {
            k: [{"source_type": r.source_type, "level": r.level.value} for r in v]
            for k, v in manifest.family_sources.items()
        },
    }

    # Evaluate against current snapshot if available
    framework_id = config.active_framework_id
    if framework_id:
        snap = load_snapshot(system_id, framework_id)
        if snap:
            m_result = evaluate_manifest(manifest, snap.sources)
            result["evaluation"] = {
                "status": m_result.status.value,
                "satisfied": [r.source_type for r in m_result.satisfied],
                "missing_required": [r.source_type for r in m_result.missing_required],
                "missing_recommended": [r.source_type for r in m_result.missing_recommended],
            }
        else:
            result["evaluation"] = {
                "status": "no_snapshot",
                "message": "Run 'pretorin context verify' to detect sources and evaluate the manifest.",
            }

    return format_json(result)


async def handle_get_cli_status(
    _client: PretorianClient | None,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_cli_status tool."""
    logger.debug("handle_get_cli_status called with %s", _safe_args(arguments))
    return format_json(get_update_status(force=bool(arguments.get("force", False))))
