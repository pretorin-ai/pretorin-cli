"""Tests for Codex agent session management."""

from __future__ import annotations

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pretorin.agent.codex_agent import AgentResult, CodexAgent


class TestAgentResult:
    """AgentResult dataclass tests."""

    def test_default_fields(self) -> None:
        result = AgentResult(response="test")
        assert result.response == "test"
        assert result.items == []
        assert result.usage is None
        assert result.evidence_created == []

    def test_with_all_fields(self) -> None:
        result = AgentResult(
            response="done",
            items=[{"type": "text"}],
            usage={"input_tokens": 100, "output_tokens": 50},
            evidence_created=["ev-001"],
        )
        assert result.usage == {"input_tokens": 100, "output_tokens": 50}
        assert result.evidence_created == ["ev-001"]


class TestCodexAgent:
    """CodexAgent initialization and prompt building tests."""

    @patch("pretorin.agent.codex_agent.Config")
    def test_resolves_api_key_from_env(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        agent = CodexAgent()
        assert agent.api_key == "sk-openai-test"

    @patch("pretorin.agent.codex_agent.Config")
    def test_resolves_api_key_from_openai_config(
        self,
        mock_config_cls: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config.api_key = None
        mock_config.openai_api_key = "sk-config-openai"
        mock_config_cls.return_value = mock_config

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        agent = CodexAgent()
        assert agent.api_key == "sk-config-openai"

    @patch("pretorin.agent.codex_agent.Config")
    def test_raises_when_no_api_key(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config.openai_api_key = None
        mock_config_cls.return_value = mock_config

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="No API key found"):
            CodexAgent()

    @patch("pretorin.agent.codex_agent.Config")
    def test_resolves_api_key_from_platform_config(
        self,
        mock_config_cls: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config.api_key = "ptn-platform-key"
        mock_config.openai_api_key = None
        mock_config_cls.return_value = mock_config

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        agent = CodexAgent()
        assert agent.api_key == "ptn-platform-key"

    @patch("pretorin.agent.codex_agent.Config")
    def test_model_override(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        agent = CodexAgent(model="gpt-4o-mini")
        assert agent.model == "gpt-4o-mini"

    @patch("pretorin.agent.codex_agent.Config")
    def test_base_url_override(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://default.example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        agent = CodexAgent(base_url="https://custom.example.com/v1")
        assert agent.base_url == "https://custom.example.com/v1"

    @patch("pretorin.agent.codex_agent.Config")
    def test_build_prompt_basic(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        agent = CodexAgent()
        prompt = agent._build_prompt("Check AC-02 compliance", skill=None)

        assert "compliance-focused coding assistant" in prompt
        assert "zero-padded control IDs" in prompt
        assert "Task:\nCheck AC-02 compliance" in prompt

    @patch("pretorin.agent.codex_agent.Config")
    def test_build_prompt_with_skill(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        agent = CodexAgent()
        prompt = agent._build_prompt("Analyze gaps", skill="gap-analysis")

        assert "Skill: gap-analysis" in prompt
        assert "Task:\nAnalyze gaps" in prompt

    @patch("pretorin.agent.codex_agent.Config")
    def test_build_prompt_with_invalid_skill(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        agent = CodexAgent()
        prompt = agent._build_prompt("Do something", skill="nonexistent-skill")

        # Should not crash, just skip the skill section
        assert "Skill:" not in prompt
        assert "Task:\nDo something" in prompt

    @patch("pretorin.agent.codex_agent.Config")
    def test_api_key_explicit_override(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config

        monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
        agent = CodexAgent(api_key="sk-explicit")
        assert agent.api_key == "sk-explicit"


def _make_agent(monkeypatch: pytest.MonkeyPatch) -> CodexAgent:
    """Helper to create a CodexAgent with mocked config and env."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with patch("pretorin.agent.codex_agent.Config") as mock_config_cls:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config_cls.return_value = mock_config
        runtime = MagicMock()
        return CodexAgent(runtime=runtime)


class TestCodexAgentRun:
    """Tests for CodexAgent.run() method (lines 228-268)."""

    async def test_run_raises_when_sdk_not_installed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = _make_agent(monkeypatch)
        agent.runtime.ensure_installed.return_value = "/fake/bin/codex"
        agent.runtime.build_env.return_value = {"OPENAI_API_KEY": "sk-test"}

        # Simulate openai_codex_sdk not being importable
        with patch.dict(sys.modules, {"openai_codex_sdk": None}):
            with pytest.raises(RuntimeError, match="Codex agent features are not installed"):
                await agent.run("test task")

    async def test_run_non_streamed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = _make_agent(monkeypatch)
        agent.runtime.ensure_installed.return_value = "/fake/bin/codex"
        agent.runtime.build_env.return_value = {"OPENAI_API_KEY": "sk-test"}

        # Build a mock SDK module
        mock_sdk = types.ModuleType("openai_codex_sdk")
        mock_codex_cls = MagicMock()
        mock_sdk.Codex = mock_codex_cls  # type: ignore[attr-defined]

        mock_thread = MagicMock()
        mock_turn = MagicMock()
        mock_turn.final_response = "compliance analysis complete"
        mock_turn.items = [{"type": "text", "content": "result"}]
        mock_thread.run = AsyncMock(return_value=mock_turn)
        mock_codex_cls.return_value.start_thread.return_value = mock_thread

        with patch.dict(sys.modules, {"openai_codex_sdk": mock_sdk}):
            result = await agent.run("analyze compliance", stream=False)

        assert result.response == "compliance analysis complete"
        assert result.items == [{"type": "text", "content": "result"}]
        agent.runtime.ensure_installed.assert_called_once()
        agent.runtime.build_env.assert_called_once_with(
            api_key="sk-test",
            base_url="https://example.com/v1",
        )
        agent.runtime.write_config.assert_called_once()

    async def test_run_streamed_delegates_to_run_streamed(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = _make_agent(monkeypatch)
        agent.runtime.ensure_installed.return_value = "/fake/bin/codex"
        agent.runtime.build_env.return_value = {"OPENAI_API_KEY": "sk-test"}

        mock_sdk = types.ModuleType("openai_codex_sdk")
        mock_codex_cls = MagicMock()
        mock_sdk.Codex = mock_codex_cls  # type: ignore[attr-defined]

        mock_thread = MagicMock()
        mock_codex_cls.return_value.start_thread.return_value = mock_thread

        expected_result = AgentResult(response="streamed result")

        with patch.dict(sys.modules, {"openai_codex_sdk": mock_sdk}):
            with patch.object(agent, "_run_streamed", new_callable=AsyncMock, return_value=expected_result):
                result = await agent.run("analyze compliance", stream=True)

        assert result.response == "streamed result"

    async def test_run_with_working_directory(self, monkeypatch: pytest.MonkeyPatch, tmp_path: object) -> None:
        agent = _make_agent(monkeypatch)
        agent.runtime.ensure_installed.return_value = "/fake/bin/codex"
        agent.runtime.build_env.return_value = {"OPENAI_API_KEY": "sk-test"}

        mock_sdk = types.ModuleType("openai_codex_sdk")
        mock_codex_cls = MagicMock()
        mock_sdk.Codex = mock_codex_cls  # type: ignore[attr-defined]

        mock_thread = MagicMock()
        mock_turn = MagicMock()
        mock_turn.final_response = "done"
        mock_turn.items = []
        mock_thread.run = AsyncMock(return_value=mock_turn)
        mock_codex_cls.return_value.start_thread.return_value = mock_thread

        with patch.dict(sys.modules, {"openai_codex_sdk": mock_sdk}):
            result = await agent.run("task", working_directory=tmp_path, stream=False)  # type: ignore[arg-type]

        assert result.response == "done"
        # Verify the working_directory was passed to start_thread
        call_args = mock_codex_cls.return_value.start_thread.call_args[0][0]
        assert call_args["working_directory"] == str(tmp_path)

    async def test_run_with_skill(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = _make_agent(monkeypatch)
        agent.runtime.ensure_installed.return_value = "/fake/bin/codex"
        agent.runtime.build_env.return_value = {"OPENAI_API_KEY": "sk-test"}

        mock_sdk = types.ModuleType("openai_codex_sdk")
        mock_codex_cls = MagicMock()
        mock_sdk.Codex = mock_codex_cls  # type: ignore[attr-defined]

        mock_thread = MagicMock()
        mock_turn = MagicMock()
        mock_turn.final_response = "gap analysis done"
        mock_turn.items = []
        mock_thread.run = AsyncMock(return_value=mock_turn)
        mock_codex_cls.return_value.start_thread.return_value = mock_thread

        with patch.dict(sys.modules, {"openai_codex_sdk": mock_sdk}):
            result = await agent.run("find gaps", skill="gap-analysis", stream=False)

        assert result.response == "gap analysis done"
        # Verify _build_prompt was called with skill by checking thread.run prompt
        prompt_arg = mock_thread.run.call_args[0][0]
        assert "Skill: gap-analysis" in prompt_arg


class TestRunStreamed:
    """Tests for CodexAgent._run_streamed() method (lines 275-310)."""

    async def _make_streamed_agent(self, monkeypatch: pytest.MonkeyPatch) -> CodexAgent:
        return _make_agent(monkeypatch)

    async def test_text_delta_event(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "text.delta"
        event.text = "Hello "

        event2 = MagicMock()
        event2.type = "text.delta"
        event2.text = "World"

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event
            yield event2

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint"):
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert result.response == "Hello World"
        assert result.items == []
        assert result.usage is None

    async def test_item_completed_agent_message(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "item.completed"
        event.item = MagicMock()
        event.item.type = "agent_message"
        event.item.text = "Analysis complete"

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint"):
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert result.response == "Analysis complete"
        assert len(result.items) == 1

    async def test_item_completed_mcp_tool_call_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "item.completed"
        event.item = MagicMock()
        event.item.type = "mcp_tool_call"
        event.item.tool = "get_control"
        event.item.status = "completed"
        event.item.error = None

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint") as mock_rprint:
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert len(result.items) == 1
        # Verify the success message was printed (not the error path)
        mock_rprint.assert_called_with("  [dim]tool get_control: completed[/dim]")

    async def test_item_completed_mcp_tool_call_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "item.completed"
        event.item = MagicMock()
        event.item.type = "mcp_tool_call"
        event.item.tool = "get_control"
        event.item.status = "failed"
        mock_error = MagicMock()
        mock_error.message = "control not found"
        event.item.error = mock_error

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint") as mock_rprint:
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert len(result.items) == 1
        mock_rprint.assert_called_with("  [red]tool get_control: control not found[/red]")

    async def test_item_completed_command_execution(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "item.completed"
        event.item = MagicMock()
        event.item.type = "command_execution"
        event.item.command = "ls -la /some/path"

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint") as mock_rprint:
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert len(result.items) == 1
        mock_rprint.assert_called_with("  [dim]shell: ls -la /some/path[/dim]")

    async def test_turn_completed_with_usage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock()
        event.type = "turn.completed"
        event.usage = MagicMock()
        event.usage.input_tokens = 500
        event.usage.output_tokens = 200

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint"):
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert result.usage == {"input_tokens": 500, "output_tokens": 200}

    async def test_turn_completed_without_usage(self, monkeypatch: pytest.MonkeyPatch) -> None:
        agent = await self._make_streamed_agent(monkeypatch)

        event = MagicMock(spec=[])  # No attributes at all
        event.type = "turn.completed"

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            yield event

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint"):
            result = await agent._run_streamed(mock_thread, "test prompt")

        assert result.usage is None

    async def test_mixed_events_full_session(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test a realistic sequence of mixed events."""
        agent = await self._make_streamed_agent(monkeypatch)

        # 1. Text delta
        ev_text = MagicMock()
        ev_text.type = "text.delta"
        ev_text.text = "Analyzing..."

        # 2. MCP tool call (success)
        ev_tool = MagicMock()
        ev_tool.type = "item.completed"
        ev_tool.item = MagicMock()
        ev_tool.item.type = "mcp_tool_call"
        ev_tool.item.tool = "get_compliance_status"
        ev_tool.item.status = "completed"
        ev_tool.item.error = None

        # 3. Command execution
        ev_cmd = MagicMock()
        ev_cmd.type = "item.completed"
        ev_cmd.item = MagicMock()
        ev_cmd.item.type = "command_execution"
        ev_cmd.item.command = "grep -r 'auth' ."

        # 4. Agent message
        ev_msg = MagicMock()
        ev_msg.type = "item.completed"
        ev_msg.item = MagicMock()
        ev_msg.item.type = "agent_message"
        ev_msg.item.text = "Final report: all controls satisfied"

        # 5. Turn completed with usage
        ev_turn = MagicMock()
        ev_turn.type = "turn.completed"
        ev_turn.usage = MagicMock()
        ev_turn.usage.input_tokens = 1000
        ev_turn.usage.output_tokens = 500

        mock_thread = MagicMock()
        mock_streamed = MagicMock()

        async def fake_events() -> object:
            for ev in [ev_text, ev_tool, ev_cmd, ev_msg, ev_turn]:
                yield ev

        mock_streamed.events = fake_events()
        mock_thread.run_streamed = AsyncMock(return_value=mock_streamed)

        with patch("pretorin.agent.codex_agent.rprint"):
            result = await agent._run_streamed(mock_thread, "full analysis")

        # agent_message overwrites response_text
        assert result.response == "Final report: all controls satisfied"
        assert len(result.items) == 3  # tool, cmd, msg (not text.delta or turn.completed)
        assert result.usage == {"input_tokens": 1000, "output_tokens": 500}


class TestPatchCodexExecBufferLimit:
    """Tests for _patch_codex_exec_buffer_limit() and the _patched_run generator (lines 35-139)."""

    def test_patch_noop_when_sdk_not_installed(self) -> None:
        """When openai_codex_sdk.exec is not importable, patching is a no-op."""
        from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit

        # Should not raise when the import fails (the default path)
        _patch_codex_exec_buffer_limit()

    def test_patch_replaces_run_method(self) -> None:
        """When the SDK is available, CodexExec.run is replaced."""
        mock_exec_cls = MagicMock()
        mock_exec_cls.run = MagicMock()
        original_run = mock_exec_cls.run

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

        # The run method should have been replaced
        assert mock_exec_cls.run is not original_run

    async def test_patched_run_aborts_when_signal_already_aborted(self) -> None:
        """If args.signal.aborted is True, raise AbortError immediately."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]
        mock_exec_module._wait_abort = MagicMock()  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            # Now call the patched run
            instance = mock_exec_cls()
            args = MagicMock()
            args.signal = MagicMock()
            args.signal.aborted = True
            args.signal.reason = "user cancelled"

            gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
            with pytest.raises(FakeAbortError, match="aborted: user cancelled"):
                await gen.__anext__()

    async def test_patched_run_success_no_signal(self) -> None:
        """Test the happy path: stdin written, lines yielded, process exits 0."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        # Create mock subprocess
        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        # stdout returns two lines then empty
        stdout_lines = [b"line one\n", b"line two\n", b""]
        line_idx = 0

        async def mock_readline() -> bytes:
            nonlocal line_idx
            if line_idx < len(stdout_lines):
                val = stdout_lines[line_idx]
                line_idx += 1
                return val
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_stderr = MagicMock()

        async def mock_stderr_read(n: int) -> bytes:
            return b""

        mock_stderr.read = mock_stderr_read

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.returncode = 0
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.kill = MagicMock()

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=["--flag"])
            instance._build_env = MagicMock(return_value={"PATH": "/usr/bin"})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = "hello"

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                lines = []
                async for line in gen:
                    lines.append(line)

        assert lines == ["line one", "line two"]
        mock_stdin.write.assert_called_once_with(b"hello")

    async def test_patched_run_nonzero_exit(self) -> None:
        """Test that non-zero exit code raises CodexExecError."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        async def mock_readline() -> bytes:
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_stderr = MagicMock()

        stderr_reads = iter([b"something went wrong", b""])

        async def mock_stderr_read(n: int) -> bytes:
            return next(stderr_reads)

        mock_stderr.read = mock_stderr_read

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.returncode = 1
        mock_proc.wait = AsyncMock(return_value=1)
        mock_proc.kill = MagicMock()

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = ""

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                with pytest.raises(FakeCodexExecError, match="exited with code 1"):
                    async for _ in gen:
                        pass

    async def test_patched_run_missing_stdin_stdout(self) -> None:
        """Test that missing stdin/stdout kills proc and raises CodexExecError."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_proc = MagicMock()
        mock_proc.stdin = None
        mock_proc.stdout = None
        mock_proc.stderr = MagicMock()
        mock_proc.returncode = None
        mock_proc.kill = MagicMock()
        mock_proc.wait = AsyncMock(return_value=0)

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = ""

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                with pytest.raises(FakeCodexExecError, match="missing stdin/stdout"):
                    await gen.__anext__()

            mock_proc.kill.assert_called_once()

    async def test_patched_run_with_signal_abort_during_read(self) -> None:
        """Test that abort signal during readline kills proc and raises AbortError."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        # stdout readline that blocks until cancelled
        async def mock_readline() -> bytes:
            await asyncio.sleep(10)
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_stderr = MagicMock()

        async def mock_stderr_read(n: int) -> bytes:
            return b""

        mock_stderr.read = mock_stderr_read

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.returncode = None
        mock_proc.wait = AsyncMock(return_value=-9)
        mock_proc.kill = MagicMock()

        # Create a mock _wait_abort that resolves immediately
        async def mock_wait_abort(signal: object) -> None:
            return

        mock_exec_module._wait_abort = mock_wait_abort  # type: ignore[attr-defined]

        args = MagicMock()
        args.signal = MagicMock()
        args.signal.aborted = False
        args.signal.reason = "user requested abort"
        args.input = "test"

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                with pytest.raises(FakeAbortError, match="aborted: user requested abort"):
                    async for _ in gen:
                        pass

    async def test_patched_run_read_all_with_none_stream(self) -> None:
        """Test the _read_all inner function handles None stream correctly."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock()
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        async def mock_readline() -> bytes:
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = None  # stderr is None => triggers _read_all(None) -> b""
        mock_proc.returncode = 0
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.kill = MagicMock()

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = ""

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                lines = []
                async for line in gen:
                    lines.append(line)

        # Should complete without error even with None stderr
        assert lines == []

    async def test_patched_run_cleanup_kills_running_process(self) -> None:
        """Test finally block kills process if returncode is None."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock(side_effect=OSError("broken pipe"))
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        async def mock_readline() -> bytes:
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_stderr = MagicMock()

        async def mock_stderr_read(n: int) -> bytes:
            return b""

        mock_stderr.read = mock_stderr_read

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.returncode = None  # Process still running
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.kill = MagicMock()

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = "test"

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                with pytest.raises(OSError, match="broken pipe"):
                    async for _ in gen:
                        pass

            # Process should have been killed in the finally block
            mock_proc.kill.assert_called()

    async def test_patched_run_cleanup_process_lookup_error(self) -> None:
        """Test finally block handles ProcessLookupError when killing process."""
        mock_exec_cls = type("CodexExec", (), {"run": None})

        mock_exec_module = types.ModuleType("openai_codex_sdk.exec")
        mock_exec_module.CodexExec = mock_exec_cls  # type: ignore[attr-defined]

        mock_abort_module = types.ModuleType("openai_codex_sdk.abort")

        class FakeAbortError(Exception):
            pass

        mock_abort_module.AbortError = FakeAbortError  # type: ignore[attr-defined]
        mock_abort_module._format_abort_reason = lambda reason: f"aborted: {reason}"  # type: ignore[attr-defined]

        mock_errors_module = types.ModuleType("openai_codex_sdk.errors")

        class FakeCodexExecError(Exception):
            pass

        mock_errors_module.CodexExecError = FakeCodexExecError  # type: ignore[attr-defined]

        mock_sdk = types.ModuleType("openai_codex_sdk")

        mock_stdin = MagicMock()
        mock_stdin.write = MagicMock(side_effect=OSError("broken"))
        mock_stdin.drain = AsyncMock()
        mock_stdin.close = MagicMock()

        async def mock_readline() -> bytes:
            return b""

        mock_stdout = MagicMock()
        mock_stdout.readline = mock_readline

        mock_stderr = MagicMock()

        async def mock_stderr_read(n: int) -> bytes:
            return b""

        mock_stderr.read = mock_stderr_read

        mock_proc = MagicMock()
        mock_proc.stdin = mock_stdin
        mock_proc.stdout = mock_stdout
        mock_proc.stderr = mock_stderr
        mock_proc.returncode = None
        mock_proc.wait = AsyncMock(return_value=0)
        mock_proc.kill = MagicMock(side_effect=ProcessLookupError())

        with patch.dict(sys.modules, {
            "openai_codex_sdk": mock_sdk,
            "openai_codex_sdk.exec": mock_exec_module,
            "openai_codex_sdk.abort": mock_abort_module,
            "openai_codex_sdk.errors": mock_errors_module,
        }):
            from pretorin.agent.codex_agent import _patch_codex_exec_buffer_limit
            _patch_codex_exec_buffer_limit()

            instance = mock_exec_cls()
            instance._build_command_args = MagicMock(return_value=[])
            instance._build_env = MagicMock(return_value={})
            instance.executable_path = "/fake/codex"

            args = MagicMock()
            args.signal = None
            args.input = "test"

            with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock, return_value=mock_proc):
                gen = mock_exec_cls.run(instance, args)  # type: ignore[misc]
                # Should handle the ProcessLookupError gracefully in finally
                with pytest.raises(OSError, match="broken"):
                    async for _ in gen:
                        pass
