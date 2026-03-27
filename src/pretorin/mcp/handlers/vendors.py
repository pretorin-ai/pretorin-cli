"""Handlers for vendor management and control responsibility tools."""

from __future__ import annotations

import logging
from typing import Any

from mcp.types import TextContent

from pretorin.client import PretorianClient
from pretorin.mcp.helpers import format_error, format_json, require
from pretorin.utils import normalize_control_id

logger = logging.getLogger(__name__)


async def handle_list_vendors(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_vendors tool."""
    vendors = await client.list_vendors()
    return format_json({"total": len(vendors), "vendors": vendors})


async def handle_create_vendor(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the create_vendor tool."""
    err = require(arguments, "name", "provider_type")
    if err:
        return format_error(err)
    result = await client.create_vendor(
        name=arguments["name"],
        provider_type=arguments["provider_type"],
        description=arguments.get("description"),
        authorization_level=arguments.get("authorization_level"),
    )
    return format_json(result)


async def handle_get_vendor(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_vendor tool."""
    err = require(arguments, "vendor_id")
    if err:
        return format_error(err)
    result = await client.get_vendor(arguments["vendor_id"])
    return format_json(result)


async def handle_update_vendor(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the update_vendor tool."""
    err = require(arguments, "vendor_id")
    if err:
        return format_error(err)
    vendor_id = arguments["vendor_id"]
    fields: dict[str, Any] = {}
    for key in ("name", "description", "provider_type", "authorization_level"):
        if key in arguments:
            fields[key] = arguments[key]
    result = await client.update_vendor(vendor_id, **fields)
    return format_json(result)


async def handle_delete_vendor(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the delete_vendor tool."""
    err = require(arguments, "vendor_id")
    if err:
        return format_error(err)
    await client.delete_vendor(arguments["vendor_id"])
    return format_json({"status": "deleted", "vendor_id": arguments["vendor_id"]})


async def handle_upload_vendor_document(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the upload_vendor_document tool."""
    err = require(arguments, "vendor_id", "file_path")
    if err:
        return format_error(err)
    result = await client.upload_vendor_document(
        vendor_id=arguments["vendor_id"],
        file_path=arguments["file_path"],
        name=arguments.get("name"),
        description=arguments.get("description"),
        attestation_type=arguments.get("attestation_type", "vendor_provided"),
    )
    return format_json(result)


async def handle_list_vendor_documents(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the list_vendor_documents tool."""
    err = require(arguments, "vendor_id")
    if err:
        return format_error(err)
    documents = await client.list_vendor_documents(arguments["vendor_id"])
    return format_json({"total": len(documents), "documents": documents})


async def handle_link_evidence_to_vendor(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the link_evidence_to_vendor tool."""
    err = require(arguments, "evidence_id")
    if err:
        return format_error(err)
    result = await client.link_evidence_to_vendor(
        evidence_id=arguments["evidence_id"],
        vendor_id=arguments.get("vendor_id"),
        attestation_type=arguments.get("attestation_type"),
    )
    return format_json(result)


async def handle_get_control_responsibility(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_control_responsibility tool."""
    err = require(arguments, "system_id", "control_id", "framework_id")
    if err:
        return format_error(err)
    result = await client.get_control_responsibility(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
    )
    return format_json(result)


async def handle_set_control_responsibility(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the set_control_responsibility tool."""
    err = require(arguments, "system_id", "control_id", "framework_id", "responsibility_mode")
    if err:
        return format_error(err)
    result = await client.set_control_responsibility(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
        responsibility_mode=arguments["responsibility_mode"],
        source_type=arguments.get("source_type"),
        vendor_id=arguments.get("vendor_id"),
    )
    return format_json(result)


async def handle_remove_control_responsibility(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the remove_control_responsibility tool."""
    err = require(arguments, "system_id", "control_id", "framework_id")
    if err:
        return format_error(err)
    await client.remove_control_responsibility(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
    )
    return format_json({
        "status": "removed",
        "system_id": arguments["system_id"],
        "control_id": arguments["control_id"],
    })


async def handle_get_stale_edges(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the get_stale_edges tool."""
    err = require(arguments, "system_id")
    if err:
        return format_error(err)
    edges = await client.get_stale_edges(arguments["system_id"])
    return format_json({"total": len(edges), "stale_edges": edges})


async def handle_sync_stale_edges(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the sync_stale_edges tool."""
    err = require(arguments, "system_id")
    if err:
        return format_error(err)
    result = await client.sync_stale_edges(arguments["system_id"])
    return format_json(result)


async def handle_generate_inheritance_narrative(
    client: PretorianClient,
    arguments: dict[str, Any],
) -> list[TextContent]:
    """Handle the generate_inheritance_narrative tool."""
    err = require(arguments, "system_id", "control_id", "framework_id")
    if err:
        return format_error(err)
    result = await client.generate_inheritance_narrative(
        system_id=arguments["system_id"],
        control_id=normalize_control_id(arguments["control_id"]),
        framework_id=arguments["framework_id"],
    )
    return format_json(result)
