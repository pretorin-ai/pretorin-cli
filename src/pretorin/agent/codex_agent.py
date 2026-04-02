"""Codex SDK session management with Pretorin isolation.

Wraps the openai-codex-sdk Python package to run compliance tasks through
a pinned, isolated Codex binary with Pretorin MCP tools auto-injected.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from rich import print as rprint

from pretorin.agent.codex_runtime import CodexRuntime
from pretorin.client.config import Config


def _patch_codex_exec_buffer_limit() -> None:
    """Raise the asyncio subprocess stdout buffer limit in the Codex SDK.

    The SDK uses ``asyncio.create_subprocess_exec`` with the default 64 KB
    line-read limit.  Compliance tool responses (e.g. control context JSON)
    routinely exceed that, causing ``ValueError: Separator is found, but
    chunk is longer than limit``.  We monkey-patch the SDK's ``run`` method
    to use a 16 MB limit instead.
    """
    try:
        from openai_codex_sdk.exec import CodexExec  # type: ignore[import-not-found,unused-ignore]
    except ImportError:
        return  # agent extras not installed — nothing to patch

    _original_run = CodexExec.run

    async def _patched_run(self: Any, args: Any) -> AsyncGenerator[str, None]:
        """Wrapper that increases the subprocess stdout buffer limit."""
        import asyncio as _aio

        from openai_codex_sdk.abort import (  # type: ignore[import-not-found,unused-ignore]
            AbortError,
            _format_abort_reason,
        )
        from openai_codex_sdk.errors import CodexExecError  # type: ignore[import-not-found,unused-ignore]

        if args.signal is not None and args.signal.aborted:
            raise AbortError(_format_abort_reason(args.signal.reason))

        command_args = self._build_command_args(args)
        env = self._build_env(args)

        proc = await _aio.create_subprocess_exec(
            self.executable_path,
            *command_args,
            stdin=_aio.subprocess.PIPE,
            stdout=_aio.subprocess.PIPE,
            stderr=_aio.subprocess.PIPE,
            env=env,
            limit=16 * 1024 * 1024,  # 16 MB line buffer
        )

        if proc.stdin is None or proc.stdout is None:
            try:
                proc.kill()
            finally:
                raise CodexExecError("Child process missing stdin/stdout")

        async def _read_all(stream: _aio.StreamReader | None) -> bytes:
            if stream is None:
                return b""
            chunks: list[bytes] = []
            while True:
                chunk = await stream.read(4096)
                if not chunk:
                    break
                chunks.append(chunk)
            return b"".join(chunks)

        stderr_task = _aio.create_task(_read_all(proc.stderr))
        abort_waiter = None
        if args.signal is not None:
            from openai_codex_sdk.exec import _wait_abort  # type: ignore[import-not-found,unused-ignore]

            abort_waiter = _aio.create_task(_wait_abort(args.signal))

        try:
            proc.stdin.write(args.input.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()

            while True:
                line_task = _aio.create_task(proc.stdout.readline())

                if abort_waiter is None:
                    done, _ = await _aio.wait({line_task}, return_when=_aio.FIRST_COMPLETED)
                else:
                    done, _ = await _aio.wait({line_task, abort_waiter}, return_when=_aio.FIRST_COMPLETED)

                if abort_waiter is not None and abort_waiter in done:
                    line_task.cancel()
                    await _aio.gather(line_task, return_exceptions=True)
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    await proc.wait()
                    raise AbortError(_format_abort_reason(args.signal.reason if args.signal else None))

                line = line_task.result()
                if not line:
                    break

                yield line.decode("utf-8").rstrip("\n")

            returncode = await proc.wait()
            stderr = await stderr_task

            if returncode != 0:
                raise CodexExecError(
                    f"Codex Exec exited with code {returncode}: {stderr.decode('utf-8', errors='replace')}"
                )
        finally:
            if abort_waiter is not None:
                abort_waiter.cancel()
                await _aio.gather(abort_waiter, return_exceptions=True)
            if proc.returncode is None:
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                try:
                    await proc.wait()
                except Exception:
                    pass
            stderr_task.cancel()
            await _aio.gather(stderr_task, return_exceptions=True)

    CodexExec.run = _patched_run  # type: ignore[assignment,unused-ignore]


_patch_codex_exec_buffer_limit()


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
        self._explicit_base_url = base_url is not None

        # Resolve model settings: explicit arg -> config -> defaults
        self.model = model or self._config.openai_model
        self.base_url = base_url or self._config.model_api_base_url
        self.api_key = api_key or self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        """Resolve model API key for the Codex subprocess.

        When using the platform model proxy (default), the platform API token
        from ``pretorin login`` is sent as the bearer key.  When the user
        explicitly overrides ``--base-url`` (e.g. to hit OpenAI directly), we
        fall back to ``OPENAI_API_KEY`` from the environment.
        """

        def _valid(value: object) -> str | None:
            return value.strip() if isinstance(value, str) and value.strip() else None

        # Explicit --base-url means the user wants a non-platform provider;
        # prefer the OPENAI_API_KEY env var in that case.
        if self._explicit_base_url:
            env_key = _valid(os.environ.get("OPENAI_API_KEY"))
            if env_key:
                return env_key
            # Fall through to config keys as a last resort.

        # Default path: use the platform API token (works with platform proxy).
        platform_key = _valid(getattr(self._config, "api_key", None))
        if platform_key:
            return platform_key

        # Fallback: raw OpenAI key from env or config.
        env_key = _valid(os.environ.get("OPENAI_API_KEY"))
        if env_key:
            return env_key
        config_key = _valid(getattr(self._config, "openai_api_key", None))
        if config_key:
            return config_key

        raise RuntimeError(
            "No API key found. Either run `pretorin login` to configure your\n"
            "platform API key, or export OPENAI_API_KEY in your shell."
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
            from openai_codex_sdk import Codex  # type: ignore[import-not-found,unused-ignore]
        except ImportError:
            raise RuntimeError(
                "Codex agent features are not installed.\n"
                "Run: pip install 'pretorin[builtin-agent]'"
            )

        codex = Codex(
            {
                "codex_path_override": str(binary_path),
                "env": env,
            }
        )

        thread = codex.start_thread(
            {
                "working_directory": str(working_directory or Path.cwd()),
                "sandbox_mode": "danger-full-access",
                "approval_policy": "never",
            }
        )

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
        usage: dict[str, int] | None = None

        async for event in streamed.events:
            if event.type == "text.delta":
                # Streaming text deltas (if supported by future SDK versions)
                rprint(event.text, end="")
                response_text += event.text
            elif event.type == "item.completed":
                items.append(event.item)
                item = event.item
                if getattr(item, "type", None) == "agent_message":
                    text = getattr(item, "text", "")
                    rprint(text)
                    response_text = text
                elif getattr(item, "type", None) == "mcp_tool_call":
                    tool = getattr(item, "tool", "unknown")
                    status = getattr(item, "status", "")
                    error = getattr(item, "error", None)
                    if error:
                        rprint(f"  [red]tool {tool}: {error.message}[/red]")
                    else:
                        rprint(f"  [dim]tool {tool}: {status}[/dim]")
                elif getattr(item, "type", None) == "command_execution":
                    cmd = getattr(item, "command", "")
                    rprint(f"  [dim]shell: {cmd[:80]}[/dim]")
            elif event.type == "turn.completed":
                if hasattr(event, "usage") and event.usage:
                    usage = {
                        "input_tokens": event.usage.input_tokens,
                        "output_tokens": event.usage.output_tokens,
                    }

        return AgentResult(response=response_text, items=items, usage=usage)

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
            "4. Return actionable output with evidence gaps and next steps.\n"
            "5. Do not hallucinate missing details; unknowns must be marked explicitly.\n"
            "6. Write auditor-ready markdown with no section headings.\n"
            "7. Narratives must include at least two rich markdown elements and at least one structural element.\n"
            "8. Evidence descriptions must include at least one rich markdown element.\n"
            "9. Rich markdown elements: fenced code blocks, tables, lists, and links.\n"
            "10. Do not include markdown images until platform-side image evidence upload support is available.\n"
            "11. For missing narrative details, insert this exact block:\n"
            "   [[PRETORIN_TODO]]\n"
            "   missing_item: <what is missing>\n"
            "   reason: Not observable from current workspace and connected MCP systems\n"
            "   required_manual_action: <what user must do on platform/integrations>\n"
            "   suggested_evidence_type: <policy_document|configuration|...>\n"
            "   [[/PRETORIN_TODO]]\n"
            "12. For every unresolved gap, add a control note in this exact format:\n"
            "   Gap: <short title>\n"
            "   Observed: <what was verifiably found>\n"
            "   Missing: <what could not be verified>\n"
            "   Why missing: <access/system limitation>\n"
            "   Manual next step: <explicit user/platform action>\n"
            "13. For narrative/evidence/note updates, always follow this sequence:\n"
            "   read current state -> collect observable facts -> draft updates -> "
            "push narrative -> upsert/link evidence -> add gap notes.\n\n"
        )

        if skill:
            skill_def = get_skill(skill)
            if skill_def:
                base += f"Skill: {skill_def.name}\n{skill_def.system_prompt}\n\n"

        return base + f"Task:\n{task}"
