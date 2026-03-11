"""Analysis prompts and templates for compliance control analysis.

This package contains the analysis guidance for the 5 core controls used in demos:
- ac-02: Access Control - Account Management
- au-02: Audit & Accountability - Audit Events
- ia-02: Identification & Authentication
- sc-07: System & Communications Protection - Boundary Protection
- cm-02: Configuration Management - Baseline Configuration
"""

from __future__ import annotations

from pretorin.mcp.prompts.control_prompts import CONTROL_ANALYSIS_PROMPTS
from pretorin.mcp.prompts.framework_guides import FRAMEWORK_GUIDES
from pretorin.mcp.prompts.schema import ARTIFACT_SCHEMA, ARTIFACT_SCHEMA_TEXT


def get_artifact_schema() -> str:
    """Return the artifact schema as formatted text."""
    return ARTIFACT_SCHEMA_TEXT


def get_framework_guide(framework_id: str) -> str | None:
    """Return the analysis guide for a framework."""
    # Normalize framework ID and check for matches
    framework_id_lower = framework_id.lower()

    # Direct match
    if framework_id_lower in FRAMEWORK_GUIDES:
        return FRAMEWORK_GUIDES[framework_id_lower]

    # Partial matches
    for key, guide in FRAMEWORK_GUIDES.items():
        if key in framework_id_lower or framework_id_lower in key:
            return guide

    return None


def get_control_prompt(control_id: str) -> dict[str, str] | None:
    """Return the analysis prompt for a control."""
    from pretorin.utils import normalize_control_id

    normalized = normalize_control_id(control_id)
    # Try normalized form first, then fall back to un-padded for legacy keys
    result = CONTROL_ANALYSIS_PROMPTS.get(normalized)
    if result is None:
        result = CONTROL_ANALYSIS_PROMPTS.get(control_id.lower())
    return result


def format_control_analysis_prompt(framework_id: str, control_id: str) -> str:
    """Format a complete analysis prompt for a control."""
    from pretorin.utils import normalize_control_id

    normalized_control_id = normalize_control_id(control_id)
    prompt_data = get_control_prompt(normalized_control_id)

    if not prompt_data:
        return f"""
# Control Analysis: {normalized_control_id.upper()}

No specific analysis guidance available for this control.

## General Approach

1. Review the control requirements using `pretorin_get_control_references`
2. Search the codebase for relevant implementations
3. Document evidence with file paths and line numbers
4. Assess implementation status based on findings

## Output Format

Use the schema from `analysis://schema` to format your artifact.
"""

    return f"""
# Control Analysis: {normalized_control_id.upper()} - {prompt_data["title"]}

**Family:** {prompt_data["family"]}

## Overview
{prompt_data["summary"]}

{prompt_data["what_to_look_for"]}

{prompt_data["evidence_examples"]}

{prompt_data["implementation_status_guidance"]}

## Output Format

Produce a JSON artifact following the schema from `analysis://schema`.
Set the framework_id to `{framework_id}` and control_id to `{normalized_control_id}`.

"""


def get_available_controls() -> list[str]:
    """Return list of controls with analysis prompts."""
    return list(CONTROL_ANALYSIS_PROMPTS.keys())


def get_control_summary(control_id: str) -> str | None:
    """Return a brief summary for a control."""
    prompt_data = get_control_prompt(control_id)
    if prompt_data:
        return f"{prompt_data['title']} - {prompt_data['family']}"
    return None


__all__ = [
    "ARTIFACT_SCHEMA",
    "ARTIFACT_SCHEMA_TEXT",
    "CONTROL_ANALYSIS_PROMPTS",
    "FRAMEWORK_GUIDES",
    "format_control_analysis_prompt",
    "get_artifact_schema",
    "get_available_controls",
    "get_control_prompt",
    "get_control_summary",
    "get_framework_guide",
]
