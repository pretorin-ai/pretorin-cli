"""Coverage tests for src/pretorin/agent/runner.py.

Covers: ComplianceAgent.__init__, _coerce_output_text, and run method
(non-streaming, streaming, skill filtering, ImportError).
"""

from __future__ import annotations

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import pretorin.agent.skills  # noqa: F401  — force into sys.modules before patch.dict
import pretorin.agent.tools  # noqa: F401  — force into sys.modules before patch.dict
from pretorin.agent.runner import ComplianceAgent


# ---------------------------------------------------------------------------
# _coerce_output_text – static method
# ---------------------------------------------------------------------------


class TestCoerceOutputText:
    """Unit tests for ComplianceAgent._coerce_output_text."""

    def test_coerce_none_returns_empty_string(self) -> None:
        assert ComplianceAgent._coerce_output_text(None) == ""

    def test_coerce_string_returns_as_is(self) -> None:
        assert ComplianceAgent._coerce_output_text("hello") == "hello"

    def test_coerce_empty_string(self) -> None:
        assert ComplianceAgent._coerce_output_text("") == ""

    def test_coerce_dict_returns_json_string(self) -> None:
        result = ComplianceAgent._coerce_output_text({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result

    def test_coerce_list_returns_json_string(self) -> None:
        result = ComplianceAgent._coerce_output_text([1, 2, 3])
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_coerce_integer_returns_str(self) -> None:
        assert ComplianceAgent._coerce_output_text(42) == "42"

    def test_coerce_float_returns_str(self) -> None:
        assert ComplianceAgent._coerce_output_text(3.14) == "3.14"

    def test_coerce_nested_dict(self) -> None:
        result = ComplianceAgent._coerce_output_text({"nested": {"inner": True}})
        assert "nested" in result
        assert "inner" in result


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


class TestComplianceAgentInit:
    """Tests for ComplianceAgent.__init__."""

    def test_stores_client_model_api_key_and_base_url(self) -> None:
        mock_client = MagicMock()
        agent = ComplianceAgent(
            client=mock_client,
            model="gpt-4o-mini",
            api_key="sk-test",
            base_url="https://example.com/v1",
        )

        assert agent.client is mock_client
        assert agent.model == "gpt-4o-mini"
        assert agent.api_key == "sk-test"
        assert agent.base_url == "https://example.com/v1"

    def test_defaults_model_to_gpt4o(self) -> None:
        agent = ComplianceAgent(client=MagicMock())
        assert agent.model == "gpt-4o"

    def test_defaults_api_key_and_base_url_to_none(self) -> None:
        agent = ComplianceAgent(client=MagicMock())
        assert agent.api_key is None
        assert agent.base_url is None


# ---------------------------------------------------------------------------
# run – ImportError when agents not installed
# ---------------------------------------------------------------------------


class TestComplianceAgentRunImportError:
    """Test run raises ImportError when the agents package is missing."""

    @pytest.mark.asyncio
    async def test_run_raises_import_error_without_agents(self) -> None:
        # Ensure the agents module appears absent inside the run method
        with patch.dict("sys.modules", {"agents": None}):
            agent = ComplianceAgent(client=MagicMock(), model="gpt-4o", api_key="sk-test")
            with pytest.raises(ImportError, match="Agent features are not installed"):
                await agent.run("test message", stream=False)


# ---------------------------------------------------------------------------
# run – non-streaming
# ---------------------------------------------------------------------------


class TestComplianceAgentRunNonStreaming:
    """Tests for ComplianceAgent.run with stream=False."""

    def _build_mock_agents(self, final_output: Any = "Final answer") -> MagicMock:
        """Return a mock agents module whose Runner.run returns final_output."""
        mock_result = MagicMock()
        mock_result.final_output = final_output

        mock_agents = MagicMock()
        mock_agents.Runner.run = AsyncMock(return_value=mock_result)
        return mock_agents

    @pytest.mark.asyncio
    async def test_run_returns_final_output_string(self) -> None:
        mock_agents = self._build_mock_agents("Compliance is good.")

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock(name="tool")),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            result = await agent.run("test message", stream=False)

        assert result == "Compliance is good."

    @pytest.mark.asyncio
    async def test_run_returns_coerced_dict_output(self) -> None:
        """When final_output is a dict, it is JSON-serialised."""
        mock_agents = self._build_mock_agents({"status": "ok"})

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock(name="tool")),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            result = await agent.run("test", stream=False)

        assert '"status"' in result
        assert '"ok"' in result

    @pytest.mark.asyncio
    async def test_run_passes_message_to_runner(self) -> None:
        """Runner.run is called with the message as input."""
        mock_result = MagicMock()
        mock_result.final_output = "done"
        mock_agents = MagicMock()
        mock_agents.Runner.run = AsyncMock(return_value=mock_result)

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock(name="tool")),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            await agent.run("my compliance task", stream=False)

        call_kwargs = mock_agents.Runner.run.call_args[1]
        assert call_kwargs.get("input") == "my compliance task"

    @pytest.mark.asyncio
    async def test_run_with_skill_filters_tools(self) -> None:
        """When a skill specifies tool_names, only matching tools are used."""
        mock_result = MagicMock()
        mock_result.final_output = "gap report"
        mock_agents = MagicMock()
        mock_agents.Runner.run = AsyncMock(return_value=mock_result)

        # Build two mock function tools with distinct names
        tool_a = MagicMock()
        tool_a.name = "list_systems"
        tool_b = MagicMock()
        tool_b.name = "get_control"

        mock_skill = MagicMock()
        mock_skill.system_prompt = "gap analysis prompt"
        mock_skill.tool_names = ["list_systems"]  # only tool_a should pass filter

        captured_agent_args: dict = {}

        def _capture_agent(*args: Any, **kwargs: Any) -> MagicMock:
            captured_agent_args.update(kwargs)
            return MagicMock()

        mock_agents.Agent.side_effect = _capture_agent

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[MagicMock(), MagicMock()]),
            patch(
                "pretorin.agent.tools.to_function_tool",
                side_effect=[tool_a, tool_b],
            ),
            patch("pretorin.agent.skills.get_skill", return_value=mock_skill),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            await agent.run("find gaps", skill="gap-analysis", stream=False)

        # Only tool_a (list_systems) should be in the tools list
        assert captured_agent_args.get("tools") == [tool_a]

    @pytest.mark.asyncio
    async def test_run_with_unknown_skill_uses_default_prompt(self) -> None:
        """When get_skill returns None, default system prompt is used (no crash)."""
        mock_result = MagicMock()
        mock_result.final_output = "done"
        mock_agents = MagicMock()
        mock_agents.Runner.run = AsyncMock(return_value=mock_result)

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock()),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            result = await agent.run("task", skill="nonexistent", stream=False)

        assert result == "done"

    @pytest.mark.asyncio
    async def test_run_with_mcp_servers(self) -> None:
        """mcp_servers are forwarded to the Agent constructor."""
        mock_result = MagicMock()
        mock_result.final_output = "done"
        mock_agents = MagicMock()
        mock_agents.Runner.run = AsyncMock(return_value=mock_result)

        mock_server = MagicMock(name="mock_mcp_server")
        captured_agent_kwargs: dict = {}

        def _capture(**kwargs: Any) -> MagicMock:
            captured_agent_kwargs.update(kwargs)
            return MagicMock()

        mock_agents.Agent.side_effect = _capture

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock()),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            await agent.run("task", mcp_servers=[mock_server], stream=False)

        assert captured_agent_kwargs.get("mcp_servers") == [mock_server]


# ---------------------------------------------------------------------------
# run – streaming
# ---------------------------------------------------------------------------


class TestComplianceAgentRunStreaming:
    """Tests for ComplianceAgent.run with stream=True."""

    @pytest.mark.asyncio
    async def test_run_streaming_returns_joined_deltas(self) -> None:
        """Streamed delta events are joined and returned."""
        # Build events with delta text
        event1 = MagicMock()
        event1.data = MagicMock()
        event1.data.delta = "Hello "

        event2 = MagicMock()
        event2.data = MagicMock()
        event2.data.delta = "world"

        async def _stream_events():
            yield event1
            yield event2

        mock_streamed = MagicMock()
        mock_streamed.stream_events = _stream_events
        mock_streamed.final_output = "Hello world"

        mock_agents = MagicMock()
        mock_agents.Runner.run_streamed = MagicMock(return_value=mock_streamed)

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock()),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            result = await agent.run("stream task", stream=True)

        assert result == "Hello world"

    @pytest.mark.asyncio
    async def test_run_streaming_no_deltas_falls_back_to_final_output(self) -> None:
        """When no delta events are emitted, final_output is returned."""
        async def _stream_events():
            # Yield an event without delta attribute to exercise the hasattr check
            event = MagicMock(spec=[])  # no 'data' attribute
            yield event

        mock_streamed = MagicMock()
        mock_streamed.stream_events = _stream_events
        mock_streamed.final_output = "Fallback answer"

        mock_agents = MagicMock()
        mock_agents.Runner.run_streamed = MagicMock(return_value=mock_streamed)

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock()),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            result = await agent.run("stream task", stream=True)

        assert result == "Fallback answer"

    @pytest.mark.asyncio
    async def test_run_streaming_calls_run_streamed(self) -> None:
        """Runner.run_streamed is called (not Runner.run) when stream=True."""
        async def _stream_events():
            return
            yield  # make it an async generator

        mock_streamed = MagicMock()
        mock_streamed.stream_events = _stream_events
        mock_streamed.final_output = None

        mock_agents = MagicMock()
        mock_agents.Runner.run_streamed = MagicMock(return_value=mock_streamed)
        mock_agents.Runner.run = AsyncMock()  # should NOT be called

        with (
            patch.dict("sys.modules", {"agents": mock_agents}),
            patch("pretorin.agent.tools.create_platform_tools", return_value=[]),
            patch("pretorin.agent.tools.to_function_tool", return_value=MagicMock()),
            patch("pretorin.agent.skills.get_skill", return_value=None),
        ):
            client = AsyncMock()
            agent = ComplianceAgent(client=client, model="gpt-4o", api_key="sk-key")
            await agent.run("task", stream=True)

        mock_agents.Runner.run_streamed.assert_called_once()
        mock_agents.Runner.run.assert_not_called()
