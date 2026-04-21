"""Shared helpers, constants, and validation for MCP tool handlers."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from pretorin.cli.context import resolve_execution_context
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.evidence.types import VALID_EVIDENCE_TYPES as VALID_EVIDENCE_TYPES
from pretorin.scope import ExecutionScope
from pretorin.utils import normalize_control_id
from pretorin.workflows.compliance_updates import resolve_system

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Validation constants
# ---------------------------------------------------------------------------

# VALID_EVIDENCE_TYPES is re-exported from pretorin.evidence.types (issue #79).
# Kept here for backward compatibility with existing imports; new code should
# import from pretorin.evidence.types directly.
VALID_SEVERITIES = {"critical", "high", "medium", "low", "info"}
VALID_EVENT_TYPES = {"security_scan", "configuration_change", "access_review", "compliance_check"}
VALID_CONTROL_STATUSES = {
    "implemented",
    "partially_implemented",
    "planned",
    "in_progress",
    "ready_to_approve",
    "not_started",
    "not_applicable",
    "inherited",
}

_CONTROL_ID_DESCRIPTION = (
    "The control ID. Use canonical IDs from list_controls. "
    "NIST/FedRAMP IDs are zero-padded (e.g., ac-02). "
    "CMMC IDs use dotted notation (e.g., AC.L2-3.1.1)."
)
_CONTROL_ID_EXAMPLES = ["ac-02", "sc-07", "AC.L2-3.1.1", "03.01.01"]


# ---------------------------------------------------------------------------
# Logging helpers
# ---------------------------------------------------------------------------


def safe_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return arguments with sensitive fields redacted for logging."""
    return {k: ("***" if k == "api_key" else v) for k, v in arguments.items()}


# ---------------------------------------------------------------------------
# JSON-schema property builders (used by tool definitions)
# ---------------------------------------------------------------------------


def control_id_property(*, optional: bool = False) -> dict[str, Any]:
    """Return a shared JSON schema field for control_id parameters."""
    description = _CONTROL_ID_DESCRIPTION if not optional else f"Optional: {_CONTROL_ID_DESCRIPTION}"
    return {
        "type": "string",
        "description": description,
        "examples": _CONTROL_ID_EXAMPLES,
    }


def system_id_property(*, optional: bool = False) -> dict[str, Any]:
    """Return a shared JSON schema field for system_id parameters."""
    description = "The system ID or name" if not optional else "Optional: The system ID or name"
    return {
        "type": "string",
        "description": description,
    }


def allow_scope_override_property() -> dict[str, Any]:
    """Return a shared JSON schema field for explicit scope overrides."""
    return {
        "type": "boolean",
        "description": (
            "Allow writes outside the active system/framework context. Defaults to false and should be used sparingly."
        ),
        "default": False,
    }


def allow_unverified_sources_property() -> dict[str, Any]:
    """Return a shared JSON schema field for source attestation overrides."""
    return {
        "type": "boolean",
        "description": ("Allow writes when source attestation shows a mismatch. Defaults to false."),
        "default": False,
    }


# ---------------------------------------------------------------------------
# Response formatters
# ---------------------------------------------------------------------------


def format_error(message: str) -> CallToolResult:
    """Format an error message for MCP response."""
    return CallToolResult(
        content=[TextContent(type="text", text=f"Error: {message}")],
        isError=True,
    )


def format_json(data: Any) -> list[TextContent]:
    """Format data as JSON for MCP response."""
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


# ---------------------------------------------------------------------------
# Parameter validation helpers
# ---------------------------------------------------------------------------


def require(arguments: dict[str, Any], *keys: str) -> str | None:
    """Validate that all keys are present and non-empty.

    Returns an error message string if validation fails, None if all ok.
    """
    missing = [k for k in keys if not arguments.get(k)]
    if missing:
        return f"Missing required parameter(s): {', '.join(missing)}"
    return None


def validate_enum(value: str, valid: set[str], field_name: str) -> str | None:
    """Validate a value against allowed enum values.

    Returns an error message if invalid, None if ok.
    """
    if value not in valid:
        return f"Invalid {field_name}: {value!r}. Must be one of: {', '.join(sorted(valid))}"
    return None


# ---------------------------------------------------------------------------
# Scope / system resolution
# ---------------------------------------------------------------------------


async def resolve_system_id(
    client: PretorianClient,
    arguments: dict[str, Any],
    *,
    required: bool = True,
) -> str | None:
    """Resolve MCP system_id arguments using the same name/ID rules as the CLI."""
    raw_system = arguments.get("system_id")
    if not raw_system:
        if required:
            raise PretorianClientError("system_id is required")
        return None
    system_id, _ = await resolve_system(client, str(raw_system))
    return system_id


async def resolve_execution_scope(
    client: PretorianClient,
    arguments: dict[str, Any],
    *,
    scope: ExecutionScope | None = None,
    control_required: bool = False,
    enforce_active_context: bool = False,
) -> tuple[str, str, str | None]:
    """Resolve one validated execution scope and optionally validate a control within it."""
    # Normalize control_id early so manifest evaluation can use it for
    # family-level requirement checking during resolve_execution_context.
    raw_control_id = arguments.get("control_id")
    normalized_control_id = normalize_control_id(raw_control_id) if raw_control_id else None

    system_id, framework_id = await resolve_execution_context(
        client,
        system=arguments.get("system_id"),
        framework=arguments.get("framework_id"),
        scope=scope,
        enforce_active_context=enforce_active_context,
        allow_scope_override=bool(arguments.get("allow_scope_override", False)),
        allow_unverified_sources=bool(arguments.get("allow_unverified_sources", False)),
        control_id=normalized_control_id,
    )
    if control_required and not normalized_control_id:
        raise PretorianClientError("control_id is required")
    # Validate control exists on the platform (needs framework_id from above)
    if normalized_control_id:
        await client.get_control(framework_id, normalized_control_id)
    logger.debug(
        "Resolved execution scope: system_id=%s, framework_id=%s, control_id=%s",
        system_id,
        framework_id,
        normalized_control_id,
    )
    return system_id, framework_id, normalized_control_id
