"""Platform tools adapted for the OpenAI Agents SDK.

Wraps PretorianClient methods as FunctionTool instances that the agent can call.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from pretorin.client.api import PretorianClient


@dataclass
class ToolDefinition:
    """Local tool definition independent of any SDK."""

    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Coroutine[Any, Any, str]]


def to_function_tool(tool: ToolDefinition) -> Any:
    """Convert a ToolDefinition to an OpenAI Agents SDK FunctionTool.

    Raises:
        ImportError: If openai-agents is not installed.
    """
    try:
        from agents import FunctionTool
    except ImportError:
        raise ImportError(
            "openai-agents is required for agent tools. "
            "Install with: pip install pretorin[agent]"
        )

    async def wrapper(ctx: Any, args: str) -> str:
        parsed = json.loads(args) if args else {}
        return await tool.handler(**parsed)

    return FunctionTool(
        name=tool.name,
        description=tool.description,
        params_json_schema=tool.parameters,
        on_invoke_tool=wrapper,
    )


def create_platform_tools(client: PretorianClient) -> list[ToolDefinition]:
    """Create all platform tool definitions bound to a client instance.

    Args:
        client: Authenticated PretorianClient.

    Returns:
        List of ToolDefinition instances.
    """
    tools: list[ToolDefinition] = []

    # --- Systems ---

    async def list_systems() -> str:
        systems = await client.list_systems()
        return json.dumps(systems, default=str)

    tools.append(ToolDefinition(
        name="list_systems",
        description="List all systems in the organization",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=list_systems,
    ))

    async def get_system(system_id: str) -> str:
        system = await client.get_system(system_id)
        return json.dumps(system.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_system",
        description="Get details about a specific system",
        parameters={
            "type": "object",
            "properties": {"system_id": {"type": "string", "description": "System ID"}},
            "required": ["system_id"],
        },
        handler=get_system,
    ))

    async def get_compliance_status(system_id: str) -> str:
        status = await client.get_system_compliance_status(system_id)
        return json.dumps(status, default=str)

    tools.append(ToolDefinition(
        name="get_compliance_status",
        description="Get compliance status for a system across all frameworks",
        parameters={
            "type": "object",
            "properties": {"system_id": {"type": "string", "description": "System ID"}},
            "required": ["system_id"],
        },
        handler=get_compliance_status,
    ))

    # --- Frameworks ---

    async def list_frameworks() -> str:
        result = await client.list_frameworks()
        return json.dumps(result.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="list_frameworks",
        description="List available compliance frameworks",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=list_frameworks,
    ))

    async def get_control(framework_id: str, control_id: str) -> str:
        control = await client.get_control(framework_id, control_id)
        return json.dumps(control.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_control",
        description="Get detailed information about a specific control",
        parameters={
            "type": "object",
            "properties": {
                "framework_id": {"type": "string", "description": "Framework ID"},
                "control_id": {"type": "string", "description": "Control ID"},
            },
            "required": ["framework_id", "control_id"],
        },
        handler=get_control,
    ))

    # --- Evidence ---

    async def search_evidence(
        control_id: str | None = None,
        framework_id: str | None = None,
        limit: int = 20,
    ) -> str:
        evidence = await client.list_evidence(
            control_id=control_id, framework_id=framework_id, limit=limit,
        )
        return json.dumps([e.model_dump() for e in evidence], default=str)

    tools.append(ToolDefinition(
        name="search_evidence",
        description="Search evidence items by control or framework",
        parameters={
            "type": "object",
            "properties": {
                "control_id": {"type": "string", "description": "Control ID filter"},
                "framework_id": {"type": "string", "description": "Framework ID filter"},
                "limit": {"type": "integer", "description": "Max results", "default": 20},
            },
            "required": [],
        },
        handler=search_evidence,
    ))

    async def create_evidence(
        name: str,
        description: str,
        evidence_type: str = "documentation",
        control_id: str | None = None,
        framework_id: str | None = None,
    ) -> str:
        from pretorin.client.models import EvidenceCreate

        ev = EvidenceCreate(
            name=name, description=description, evidence_type=evidence_type,
            source="agent", control_id=control_id, framework_id=framework_id,
        )
        result = await client.create_evidence("", ev)
        return json.dumps(result, default=str)

    tools.append(ToolDefinition(
        name="create_evidence",
        description="Create a new evidence item on the platform",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Evidence name"},
                "description": {"type": "string", "description": "Evidence description"},
                "evidence_type": {"type": "string", "description": "Type of evidence"},
                "control_id": {"type": "string", "description": "Associated control"},
                "framework_id": {"type": "string", "description": "Associated framework"},
            },
            "required": ["name", "description"],
        },
        handler=create_evidence,
    ))

    # --- Narratives ---

    async def generate_narrative(
        system_id: str,
        control_id: str,
        framework_id: str,
        context: str | None = None,
    ) -> str:
        result = await client.generate_narrative(system_id, control_id, framework_id, context)
        return json.dumps(result, default=str)

    tools.append(ToolDefinition(
        name="generate_narrative",
        description="Generate an AI implementation narrative for a control (may take 30-60s)",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "framework_id": {"type": "string", "description": "Framework ID"},
                "context": {"type": "string", "description": "Additional context"},
            },
            "required": ["system_id", "control_id", "framework_id"],
        },
        handler=generate_narrative,
    ))

    async def get_narrative(
        system_id: str,
        control_id: str,
        framework_id: str | None = None,
    ) -> str:
        narrative = await client.get_narrative(system_id, control_id, framework_id)
        return json.dumps(narrative.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_narrative",
        description="Get an existing narrative for a control",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "framework_id": {"type": "string", "description": "Framework ID filter"},
            },
            "required": ["system_id", "control_id"],
        },
        handler=get_narrative,
    ))

    # --- Monitoring ---

    async def push_monitoring_event(
        system_id: str,
        title: str,
        severity: str = "medium",
        event_type: str = "security_scan",
        control_id: str | None = None,
        description: str = "",
    ) -> str:
        from pretorin.client.models import MonitoringEventCreate

        event = MonitoringEventCreate(
            event_type=event_type, title=title, description=description,
            severity=severity, control_id=control_id,
            event_data={"source": "agent"},
        )
        result = await client.create_monitoring_event(system_id, event)
        return json.dumps(result, default=str)

    tools.append(ToolDefinition(
        name="push_monitoring_event",
        description="Push a monitoring event to a system",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "title": {"type": "string", "description": "Event title"},
                "severity": {"type": "string", "description": "Severity level"},
                "event_type": {"type": "string", "description": "Event type"},
                "control_id": {"type": "string", "description": "Associated control"},
                "description": {"type": "string", "description": "Event description"},
            },
            "required": ["system_id", "title"],
        },
        handler=push_monitoring_event,
    ))

    # --- Control Implementation ---

    async def update_control_status(
        system_id: str,
        control_id: str,
        status: str,
        framework_id: str | None = None,
    ) -> str:
        result = await client.update_control_status(system_id, control_id, status, framework_id)
        return json.dumps(result, default=str)

    tools.append(ToolDefinition(
        name="update_control_status",
        description="Update the implementation status of a control",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "status": {"type": "string", "description": "New status"},
                "framework_id": {"type": "string", "description": "Framework context"},
            },
            "required": ["system_id", "control_id", "status"],
        },
        handler=update_control_status,
    ))

    async def get_control_implementation(
        system_id: str,
        control_id: str,
        framework_id: str | None = None,
    ) -> str:
        impl = await client.get_control_implementation(system_id, control_id, framework_id)
        return json.dumps(impl.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_control_implementation",
        description="Get implementation details for a control including narrative, evidence, and notes",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "framework_id": {"type": "string", "description": "Framework ID filter"},
            },
            "required": ["system_id", "control_id"],
        },
        handler=get_control_implementation,
    ))

    # --- Control Context ---

    async def get_control_context(
        system_id: str,
        control_id: str,
        framework_id: str,
    ) -> str:
        ctx = await client.get_control_context(system_id, control_id, framework_id)
        return json.dumps(ctx.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_control_context",
        description="Get rich context for a control: AI guidance, statement, objectives, and implementation",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "framework_id": {"type": "string", "description": "Framework ID"},
            },
            "required": ["system_id", "control_id", "framework_id"],
        },
        handler=get_control_context,
    ))

    # --- Scope ---

    async def get_scope(system_id: str) -> str:
        scope = await client.get_scope(system_id)
        return json.dumps(scope.model_dump(), default=str)

    tools.append(ToolDefinition(
        name="get_scope",
        description="Get system scope/policy information including excluded controls",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
            },
            "required": ["system_id"],
        },
        handler=get_scope,
    ))

    # --- Update Narrative ---

    async def update_narrative(
        system_id: str,
        control_id: str,
        framework_id: str,
        narrative: str,
        is_ai_generated: bool = False,
    ) -> str:
        result = await client.update_narrative(
            system_id, control_id, narrative, framework_id, is_ai_generated,
        )
        return json.dumps(result, default=str)

    tools.append(ToolDefinition(
        name="update_narrative",
        description="Push a narrative text update for a control implementation",
        parameters={
            "type": "object",
            "properties": {
                "system_id": {"type": "string", "description": "System ID"},
                "control_id": {"type": "string", "description": "Control ID"},
                "framework_id": {"type": "string", "description": "Framework ID"},
                "narrative": {"type": "string", "description": "Narrative text"},
                "is_ai_generated": {"type": "boolean", "description": "AI-generated flag"},
            },
            "required": ["system_id", "control_id", "framework_id", "narrative"],
        },
        handler=update_narrative,
    ))

    return tools
