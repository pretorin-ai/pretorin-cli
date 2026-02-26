"""Tests for agent CLI commands (Codex integration)."""

from __future__ import annotations

import stat
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli import agent as agent_cli

runner = CliRunner()


def _mock_runtime(
    version: str = "test-v1",
    binary_path: Path = Path("/tmp/test/bin/codex-test-v1"),
    is_installed: bool = True,
    codex_home: Path = Path("/tmp/test/codex"),
) -> MagicMock:
    """Create a mock CodexRuntime with common defaults."""
    mock = MagicMock()
    mock.version = version
    mock.binary_path = binary_path
    mock.is_installed = is_installed
    mock.codex_home = codex_home
    return mock


class TestAgentVersion:
    """Tests for 'pretorin agent version' command."""

    def test_shows_version_and_status_installed(self) -> None:
        mock_runtime = _mock_runtime(version="test-v1.0.0", is_installed=True)
        mock_cls = MagicMock(return_value=mock_runtime)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["version"])
        assert result.exit_code == 0
        assert "test-v1.0.0" in result.stdout
        assert "installed" in result.stdout

    def test_shows_not_installed(self) -> None:
        mock_runtime = _mock_runtime(version="test-v1.0.0", is_installed=False)
        mock_cls = MagicMock(return_value=mock_runtime)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["version"])
        assert result.exit_code == 0
        assert "not installed" in result.stdout


class TestAgentDoctor:
    """Tests for 'pretorin agent doctor' command."""

    def test_doctor_reports_missing_binary(self) -> None:
        mock_runtime = _mock_runtime(is_installed=False)
        mock_cls = MagicMock(return_value=mock_runtime)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["doctor"])
        assert result.exit_code == 1

    def test_doctor_succeeds_with_installed_binary(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        codex_home = tmp_path / "codex"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text("# config")

        mock_runtime = _mock_runtime(is_installed=True, codex_home=codex_home)
        mock_cls = MagicMock(return_value=mock_runtime)

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["doctor"])
        assert result.exit_code == 0
        assert "ready" in result.stdout.lower()


class TestAgentInstall:
    """Tests for 'pretorin agent install' command."""

    def test_install_succeeds(self, tmp_path: Path) -> None:
        mock_runtime = _mock_runtime()
        mock_runtime.ensure_installed.return_value = tmp_path / "bin" / "codex-test-v1"
        mock_cls = MagicMock(return_value=mock_runtime)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["install"])
        assert result.exit_code == 0
        assert "installed" in result.stdout.lower()

    def test_install_failure(self) -> None:
        mock_runtime = _mock_runtime()
        mock_runtime.ensure_installed.side_effect = RuntimeError("Download failed")
        mock_cls = MagicMock(return_value=mock_runtime)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", mock_cls):
            result = runner.invoke(agent_cli.app, ["install"])
        assert result.exit_code == 1
        assert "failed" in result.stdout.lower()


class TestAgentRunCLI:
    """Tests for 'pretorin agent run' command argument parsing."""

    def test_run_requires_message(self) -> None:
        result = runner.invoke(agent_cli.app, ["run"])
        assert result.exit_code != 0

    def test_run_default_uses_codex(self) -> None:
        with (
            patch.object(agent_cli, "_check_codex_deps"),
            patch("pretorin.cli.agent.asyncio") as mock_asyncio,
        ):
            result = runner.invoke(agent_cli.app, ["run", "test task"])
            mock_asyncio.run.assert_called_once()

    def test_run_legacy_flag_uses_agents_sdk(self) -> None:
        with (
            patch.object(agent_cli, "_check_agent_deps"),
            patch("pretorin.cli.agent.asyncio") as mock_asyncio,
        ):
            result = runner.invoke(agent_cli.app, ["run", "test task", "--legacy"])
            mock_asyncio.run.assert_called_once()


class TestHarnessDeprecation:
    """Tests for harness deprecation warnings."""

    def test_harness_app_is_deprecated(self) -> None:
        from pretorin.cli import harness as harness_cli

        assert harness_cli.app.info.deprecated is True

    def test_harness_run_shows_deprecation_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from pretorin.cli import harness as harness_cli
        import shutil

        config_path = tmp_path / "config.toml"
        monkeypatch.setattr(harness_cli, "HARNESS_CONFIG_FILE", config_path)

        # Write a valid config so it gets past initial checks
        config_path.write_text(
            'model_provider = "pretorin"\n\n'
            "[model_providers.pretorin]\n"
            'base_url = "https://example.com/v1"\n'
            'env_key = "PRETORIN_LLM_API_KEY"\n\n'
            "[mcp_servers.pretorin]\n"
            'command = "pretorin"\n'
            'args = ["mcp-serve"]\n'
        )
        monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")

        result = runner.invoke(harness_cli.app, ["run", "test task", "--dry-run"])
        assert "deprecated" in result.stdout.lower()
