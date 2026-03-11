"""MCP resource listing and reading."""

from __future__ import annotations

from urllib.parse import urlparse

from mcp.types import Resource

from pretorin.mcp.prompts import (
    format_control_analysis_prompt,
    get_artifact_schema,
    get_available_controls,
    get_control_summary,
    get_framework_guide,
)
from pretorin.utils import normalize_control_id

_FRAMEWORK_GUIDES = [
    ("fedramp-moderate", "FedRAMP Moderate"),
    ("nist-800-53-r5", "NIST 800-53 Rev 5"),
    ("nist-800-171-r3", "NIST 800-171 Rev 3"),
]


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

    for framework_id, title in _FRAMEWORK_GUIDES:
        resources.append(
            Resource(
                uri=f"analysis://guide/{framework_id}",
                name=f"{title} Analysis Guide",
                description=f"Analysis guidance for {title} framework",
                mimeType="text/markdown",
            )
        )

    for framework_id, title in _FRAMEWORK_GUIDES:
        for control_id in get_available_controls():
            summary = get_control_summary(control_id)
            resources.append(
                Resource(
                    uri=f"analysis://control/{framework_id}/{control_id}",
                    name=f"{title} {control_id.upper()} Analysis",
                    description=f"Analysis guidance for {summary} in {title}",
                    mimeType="text/markdown",
                )
            )

    return resources


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
        if len(path_parts) != 2:
            raise ValueError("Control resources require framework_id and control_id")
        framework_id = path_parts[0]
        control_id = normalize_control_id(path_parts[1])

        return format_control_analysis_prompt(framework_id, control_id)

    else:
        raise ValueError(f"Unknown resource type: {resource_type}")
