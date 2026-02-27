"""Agent runner using the OpenAI Agents SDK."""

from __future__ import annotations

import json
import sys
from typing import Any

from pretorin.client.api import PretorianClient


class ComplianceAgent:
    """Autonomous compliance agent backed by the OpenAI Agents SDK.

    Connects to the Pretorin platform via PretorianClient and optionally
    to external MCP servers (GitHub, AWS, etc.) for codebase/infra access.
    """

    def __init__(
        self,
        client: PretorianClient,
        model: str = "gpt-4o",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.client = client
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    @staticmethod
    def _coerce_output_text(value: object) -> str:
        """Normalize SDK output payloads to displayable text."""
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=str)
        return str(value)

    async def run(
        self,
        message: str,
        skill: str | None = None,
        mcp_servers: list[Any] | None = None,
        max_turns: int = 15,
        stream: bool = True,
    ) -> str:
        """Run the agent with a message and optional skill.

        Args:
            message: User message / task description.
            skill: Optional skill name for specialized behavior.
            mcp_servers: Optional list of MCP server instances (SDK objects).
            max_turns: Maximum agent loop turns.
            stream: Whether to stream output to stdout.

        Returns:
            Final agent output text.

        Raises:
            ImportError: If openai-agents is not installed.
        """
        try:
            from agents import Agent, RunConfig, Runner  # noqa: F401
        except ImportError:
            raise ImportError("openai-agents is required for agent features. Install with: pip install pretorin[agent]")

        from pretorin.agent.skills import get_skill
        from pretorin.agent.tools import create_platform_tools, to_function_tool

        # Build platform tools
        platform_tools = create_platform_tools(self.client)
        function_tools = [to_function_tool(t) for t in platform_tools]

        # Build system prompt
        system_prompt = (
            "You are a Pretorin compliance agent. You help organizations manage "
            "their security compliance by analyzing systems, generating narratives, "
            "collecting evidence, and monitoring compliance posture.\n\n"
            "You have access to the Pretorin platform tools and optionally to "
            "external MCP servers for accessing codebases and infrastructure."
        )

        if skill:
            skill_config = get_skill(skill)
            if skill_config:
                system_prompt = skill_config.system_prompt
                # Filter tools to skill's tool set if specified
                if skill_config.tool_names:
                    tool_names = set(skill_config.tool_names)
                    function_tools = [t for t in function_tools if t.name in tool_names]

        # Create the agent
        agent = Agent(
            name="pretorin-compliance-agent",
            instructions=system_prompt,
            tools=function_tools,
            mcp_servers=mcp_servers or [],
        )

        # Configure model provider
        run_config = RunConfig(
            model=self.model,
        )

        if stream:
            streamed_result = Runner.run_streamed(agent, input=message, run_config=run_config)
            output_parts: list[str] = []
            async for event in streamed_result.stream_events():
                if hasattr(event, "data") and hasattr(event.data, "delta"):
                    delta = self._coerce_output_text(event.data.delta)
                    sys.stdout.write(delta)
                    sys.stdout.flush()
                    output_parts.append(delta)
            sys.stdout.write("\n")
            return "".join(output_parts) if output_parts else self._coerce_output_text(streamed_result.final_output)
        else:
            result = await Runner.run(agent, input=message, run_config=run_config)
            return self._coerce_output_text(result.final_output)
