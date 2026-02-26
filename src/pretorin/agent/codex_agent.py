"""Codex SDK session management with Pretorin isolation.

Wraps the openai-codex-sdk Python package to run compliance tasks through
a pinned, isolated Codex binary with Pretorin MCP tools auto-injected.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich import print as rprint

from pretorin.agent.codex_runtime import CodexRuntime
from pretorin.client.config import Config


@dataclass
class AgentResult:
    """Result from a Codex agent session."""

    response: str
    items: list[Any] = field(default_factory=list)
    usage: dict[str, int] | None = None
    evidence_created: list[str] = field(default_factory=list)


class CodexAgent:
    """Manages Codex SDK sessions with Pretorin isolation."""

    def __init__(
        self,
        runtime: CodexRuntime | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.runtime = runtime or CodexRuntime()
        self._config = Config()

        # Resolve model settings: explicit arg -> config -> defaults
        self.model = model or self._config.openai_model
        self.base_url = base_url or self._config.model_api_base_url
        self.api_key = api_key or self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        """Resolve API key: PRETORIN_LLM_API_KEY -> OPENAI_API_KEY -> config."""
        key = os.environ.get("PRETORIN_LLM_API_KEY")
        if key:
            return key
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            return key
        config_key = self._config.openai_api_key
        if config_key:
            return config_key
        raise RuntimeError(
            "No API key found. Set PRETORIN_LLM_API_KEY, OPENAI_API_KEY, "
            "or configure openai_api_key in ~/.pretorin/config.json"
        )

    async def run(
        self,
        task: str,
        working_directory: Path | None = None,
        skill: str | None = None,
        stream: bool = True,
    ) -> AgentResult:
        """Execute a compliance task via Codex.

        1. Ensures pinned binary is installed
        2. Writes isolated config.toml
        3. Spawns Codex via SDK with codex_path_override
        4. Injects Pretorin MCP server for compliance tools
        5. Streams events (tool calls, text output, errors)
        6. Captures findings for evidence creation
        """
        binary_path = self.runtime.ensure_installed()
        env = self.runtime.build_env(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Write isolated config with model settings
        self.runtime.write_config(
            model=self.model,
            provider_name="pretorin",
            base_url=self.base_url,
            env_key="OPENAI_API_KEY",
        )

        try:
            from openai_codex_sdk import Codex  # type: ignore[import-not-found]
        except ImportError:
            raise RuntimeError(
                "openai-codex-sdk is required for Codex agent features.\n"
                "Install with: pip install pretorin[agent]"
            )

        codex = Codex({
            "codex_path_override": str(binary_path),
            "env": env,
        })

        thread = codex.start_thread({
            "working_directory": str(working_directory or Path.cwd()),
        })

        prompt = self._build_prompt(task, skill)

        if stream:
            return await self._run_streamed(thread, prompt)
        else:
            turn = await thread.run(prompt)
            return AgentResult(
                response=turn.final_response,
                items=turn.items,
            )

    async def _run_streamed(self, thread: Any, prompt: str) -> AgentResult:
        """Stream events with real-time output and evidence capture."""
        streamed = await thread.run_streamed(prompt)
        items: list[Any] = []
        response_text = ""

        async for event in streamed.events:
            if event.type == "text.delta":
                rprint(event.text, end="")
                response_text += event.text
            elif event.type == "item.completed":
                items.append(event.item)
            elif event.type == "turn.completed":
                # Token usage could be captured here
                pass

        return AgentResult(response=response_text, items=items)

    def _build_prompt(self, task: str, skill: str | None) -> str:
        """Build compliance-focused prompt, optionally with skill guidance."""
        from pretorin.agent.skills import get_skill

        base = (
            "You are a compliance-focused coding assistant operating through Pretorin.\n"
            "You have access to Pretorin MCP tools for querying frameworks, controls, "
            "evidence, and narratives.\n\n"
            "Rules:\n"
            "1. Use Pretorin MCP tools to get authoritative compliance data.\n"
            "2. Reference framework/control IDs explicitly (e.g., AC-02, SC-07).\n"
            "3. Use zero-padded control IDs (ac-02 not ac-2).\n"
            "4. Return actionable output with evidence gaps and next steps.\n\n"
        )

        if skill:
            skill_def = get_skill(skill)
            if skill_def:
                base += f"Skill: {skill_def.name}\n{skill_def.system_prompt}\n\n"

        return base + f"Task:\n{task}"
