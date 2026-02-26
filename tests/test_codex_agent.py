"""Tests for Codex agent session management."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

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

        monkeypatch.setenv("PRETORIN_LLM_API_KEY", "sk-pretorin-test")
        agent = CodexAgent()
        assert agent.api_key == "sk-pretorin-test"

    @patch("pretorin.agent.codex_agent.Config")
    def test_resolves_api_key_from_openai_env(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config.openai_api_key = None
        mock_config_cls.return_value = mock_config

        monkeypatch.delenv("PRETORIN_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-test")
        agent = CodexAgent()
        assert agent.api_key == "sk-openai-test"

    @patch("pretorin.agent.codex_agent.Config")
    def test_raises_when_no_api_key(self, mock_config_cls: MagicMock, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_config = MagicMock()
        mock_config.openai_model = "gpt-4o"
        mock_config.model_api_base_url = "https://example.com/v1"
        mock_config.openai_api_key = None
        mock_config_cls.return_value = mock_config

        monkeypatch.delenv("PRETORIN_LLM_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="No API key found"):
            CodexAgent()

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
