"""Coverage tests for src/pretorin/cli/agent.py.

Covers: _check_agent_deps, _check_codex_deps, agent_run (codex + legacy paths),
_run_codex_agent, _run_legacy_agent, agent_doctor, agent_install, agent_version,
agent_skills, mcp_list, mcp_add, mcp_remove.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_runtime(
    version: str = "test-v1",
    binary_path: Path = Path("/tmp/test/bin/codex-test-v1"),
    is_installed: bool = True,
    codex_home: Path = Path("/tmp/test/codex"),
) -> MagicMock:
    mock = MagicMock()
    mock.version = version
    mock.binary_path = binary_path
    mock.is_installed = is_installed
    mock.codex_home = codex_home
    return mock


def _make_mcp_manager(servers=None) -> MagicMock:
    mgr = MagicMock()
    mgr.servers = servers if servers is not None else []
    mgr.add_server = MagicMock()
    mgr.remove_server = MagicMock(return_value=True)
    return mgr


# ---------------------------------------------------------------------------
# _check_agent_deps
# ---------------------------------------------------------------------------


class TestCheckAgentDeps:
    """Test the _check_agent_deps guard via commands that call it."""

    def test_agent_deps_missing_exits_1(self) -> None:
        """--legacy flag calls _check_agent_deps; missing agents package exits 1."""
        with patch.dict("sys.modules", {"agents": None}):
            # Also stop asyncio.run from being called (it won't be reached)
            result = runner.invoke(app, ["agent", "run", "test task", "--legacy"])
        assert result.exit_code == 1

    def test_codex_deps_missing_exits_1(self) -> None:
        """Default (non-legacy) run calls _check_codex_deps; missing package exits 1."""
        with patch.dict("sys.modules", {"openai_codex_sdk": None}):
            result = runner.invoke(app, ["agent", "run", "test task"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# agent run – Codex path
# ---------------------------------------------------------------------------


class TestAgentRunCodexPath:
    """Tests for 'pretorin agent run' using the default Codex runtime."""

    def _codex_sdk_mock(self) -> MagicMock:
        return MagicMock()

    def test_run_codex_success_no_stream(self) -> None:
        """Successful non-streaming Codex run prints response text."""
        agent_result = SimpleNamespace(response="All controls passing.", evidence_created=[])
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(return_value=agent_result)

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--no-stream"])

        assert result.exit_code == 0
        assert "All controls passing." in result.output

    def test_run_codex_success_json_mode(self) -> None:
        """JSON mode emits a structured payload with response and evidence_created."""
        agent_result = SimpleNamespace(response="Done.", evidence_created=["ev-001"])
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(return_value=agent_result)

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            result = runner.invoke(app, ["--json", "agent", "run", "test task", "--no-stream"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["response"] == "Done."
        assert payload["evidence_created"] == ["ev-001"]

    def test_run_codex_constructor_runtime_error(self) -> None:
        """RuntimeError from CodexAgent constructor exits 1."""
        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", side_effect=RuntimeError("No API key")),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--no-stream"])

        assert result.exit_code == 1
        assert "No API key" in result.output

    def test_run_codex_agent_run_runtime_error(self) -> None:
        """RuntimeError from agent.run exits 1."""
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(side_effect=RuntimeError("Codex crashed"))

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--no-stream"])

        assert result.exit_code == 1
        assert "Codex crashed" in result.output

    def test_run_codex_agent_run_generic_exception(self) -> None:
        """Non-RuntimeError exception from agent.run also exits 1."""
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(side_effect=ValueError("Unexpected"))

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--no-stream"])

        assert result.exit_code == 1
        assert "Unexpected" in result.output

    def test_run_codex_with_skill_no_stream(self) -> None:
        """--skill flag is forwarded correctly to agent.run."""
        agent_result = SimpleNamespace(response="Gap report.", evidence_created=[])
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(return_value=agent_result)

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            result = runner.invoke(
                app, ["agent", "run", "Analyze gaps", "--skill", "gap-analysis", "--no-stream"]
            )

        assert result.exit_code == 0
        mock_agent.run.assert_called_once()
        call_kwargs = mock_agent.run.call_args[1]
        assert call_kwargs.get("skill") == "gap-analysis"

    def test_run_codex_streaming_returns_none_result(self) -> None:
        """When stream=True, agent.run returns None (streaming) – no JSON output."""
        mock_agent = MagicMock()
        mock_agent.model = "gpt-4o"
        mock_agent.run = AsyncMock(return_value=None)

        with (
            patch.dict("sys.modules", {"openai_codex_sdk": self._codex_sdk_mock()}),
            patch("pretorin.agent.codex_agent.CodexAgent", return_value=mock_agent),
        ):
            # Without --no-stream, stream=True; result is None so nothing extra printed
            result = runner.invoke(app, ["agent", "run", "stream task"])

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# agent run – legacy path
# ---------------------------------------------------------------------------


class TestAgentRunLegacyPath:
    """Tests for 'pretorin agent run --legacy'."""

    def _agents_mock(self) -> MagicMock:
        return MagicMock()

    def _make_client(self, *, is_configured: bool = True) -> AsyncMock:
        client = AsyncMock()
        client.is_configured = is_configured
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=None)
        return client

    def test_legacy_no_api_key_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing OPENAI_API_KEY with no config key exits 1."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)
        mock_config.openai_base_url = None

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--legacy"])

        assert result.exit_code == 1
        assert "No model API key" in result.output

    def test_legacy_client_not_configured_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Client.is_configured=False exits 1."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)
        client = self._make_client(is_configured=False)

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
        ):
            result = runner.invoke(app, ["agent", "run", "test task", "--legacy"])

        assert result.exit_code == 1
        assert "Not configured" in result.output

    def test_legacy_success_no_stream(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Successful legacy run prints agent result."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        mock_compliance_agent = MagicMock()
        mock_compliance_agent.run = AsyncMock(return_value="Compliance report text")

        client = self._make_client(is_configured=True)

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
            patch("pretorin.agent.runner.ComplianceAgent", return_value=mock_compliance_agent),
            patch("pretorin.agent.mcp_config.MCPConfigManager") as MockMCPMgr,
        ):
            MockMCPMgr.return_value.servers = []
            result = runner.invoke(app, ["agent", "run", "test", "--legacy", "--no-stream"])

        assert result.exit_code == 0
        assert "Compliance report text" in result.output

    def test_legacy_pretorin_client_error_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """PretorianClientError from agent.run exits 1 with error message."""
        from pretorin.client.api import PretorianClientError

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        mock_compliance_agent = MagicMock()
        mock_compliance_agent.run = AsyncMock(
            side_effect=PretorianClientError("Service unavailable", status_code=503)
        )

        client = self._make_client(is_configured=True)

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
            patch("pretorin.agent.runner.ComplianceAgent", return_value=mock_compliance_agent),
            patch("pretorin.agent.mcp_config.MCPConfigManager") as MockMCPMgr,
        ):
            MockMCPMgr.return_value.servers = []
            result = runner.invoke(app, ["agent", "run", "test", "--legacy", "--no-stream"])

        assert result.exit_code == 1
        assert "Service unavailable" in result.output

    def test_legacy_generic_exception_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Generic exception from agent.run exits 1."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        mock_compliance_agent = MagicMock()
        mock_compliance_agent.run = AsyncMock(side_effect=ValueError("Something broke"))

        client = self._make_client(is_configured=True)

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
            patch("pretorin.agent.runner.ComplianceAgent", return_value=mock_compliance_agent),
            patch("pretorin.agent.mcp_config.MCPConfigManager") as MockMCPMgr,
        ):
            MockMCPMgr.return_value.servers = []
            result = runner.invoke(app, ["agent", "run", "test", "--legacy", "--no-stream"])

        assert result.exit_code == 1
        assert "Something broke" in result.output

    def test_legacy_with_mcp_servers(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """When MCP servers are configured, they are forwarded to agent.run."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        mock_compliance_agent = MagicMock()
        mock_compliance_agent.run = AsyncMock(return_value="done")

        client = self._make_client(is_configured=True)

        mock_server = MagicMock()
        mock_mgr = MagicMock()
        mock_mgr.servers = [MagicMock()]
        mock_mgr.to_sdk_servers = MagicMock(return_value=[mock_server])

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
            patch("pretorin.agent.runner.ComplianceAgent", return_value=mock_compliance_agent),
            patch("pretorin.agent.mcp_config.MCPConfigManager", return_value=mock_mgr),
        ):
            result = runner.invoke(app, ["agent", "run", "test", "--legacy", "--no-stream"])

        assert result.exit_code == 0
        call_kwargs = mock_compliance_agent.run.call_args[1]
        assert call_kwargs.get("mcp_servers") == [mock_server]

    def test_legacy_no_mcp_flag_skips_mcp(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """--no-mcp flag causes mcp_servers=None regardless of config."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        mock_compliance_agent = MagicMock()
        mock_compliance_agent.run = AsyncMock(return_value="done")

        client = self._make_client(is_configured=True)

        with (
            patch.dict("sys.modules", {"agents": self._agents_mock()}),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
            patch("pretorin.client.api.PretorianClient", return_value=client),
            patch("pretorin.agent.runner.ComplianceAgent", return_value=mock_compliance_agent),
        ):
            result = runner.invoke(app, ["agent", "run", "test", "--legacy", "--no-stream", "--no-mcp"])

        assert result.exit_code == 0
        call_kwargs = mock_compliance_agent.run.call_args[1]
        assert call_kwargs.get("mcp_servers") is None


# ---------------------------------------------------------------------------
# agent doctor
# ---------------------------------------------------------------------------


class TestAgentDoctor:
    """Tests for 'pretorin agent doctor'."""

    def test_doctor_installed_with_config_and_api_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """All green: binary installed, config.toml exists, API key set."""
        codex_home = tmp_path / "codex"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text("# config")

        mock_runtime = _mock_runtime(is_installed=True, codex_home=codex_home)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "doctor"])

        assert result.exit_code == 0
        assert "ready" in result.output.lower()

    def test_doctor_not_installed_exits_1(self) -> None:
        """Missing binary causes exit 1 and error message."""
        mock_runtime = _mock_runtime(is_installed=False)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "doctor"])

        assert result.exit_code == 1

    def test_doctor_missing_config_toml_shows_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing config.toml emits a warning but does not fail if binary is installed."""
        codex_home = tmp_path / "codex"
        codex_home.mkdir()
        # No config.toml written

        mock_runtime = _mock_runtime(is_installed=True, codex_home=codex_home)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "doctor"])

        assert result.exit_code == 0
        assert "config.toml" in result.output

    def test_doctor_missing_api_key_shows_warning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Missing API key emits a warning but does not cause exit 1."""
        codex_home = tmp_path / "codex"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text("# config")

        mock_runtime = _mock_runtime(is_installed=True, codex_home=codex_home)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("PRETORIN_API_KEY", raising=False)

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        with (
            patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime),
            patch("pretorin.cli.agent.Config", return_value=mock_config),
        ):
            result = runner.invoke(app, ["agent", "doctor"])

        assert result.exit_code == 0
        assert "API key" in result.output

    def test_doctor_json_mode_ok(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON mode emits structured payload when everything is healthy."""
        codex_home = tmp_path / "codex"
        codex_home.mkdir()
        (codex_home / "config.toml").write_text("# config")

        mock_runtime = _mock_runtime(is_installed=True, codex_home=codex_home)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "doctor"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert "info" in payload

    def test_doctor_json_mode_errors(self) -> None:
        """JSON mode exits 1 and includes errors list when binary not installed."""
        mock_runtime = _mock_runtime(is_installed=False)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "doctor"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert len(payload["errors"]) > 0


# ---------------------------------------------------------------------------
# agent install
# ---------------------------------------------------------------------------


class TestAgentInstall:
    """Tests for 'pretorin agent install'."""

    def test_install_success(self, tmp_path: Path) -> None:
        """Successful install prints binary path."""
        installed_path = tmp_path / "bin" / "codex-test-v1"
        mock_runtime = _mock_runtime(version="test-v1")
        mock_runtime.ensure_installed.return_value = installed_path

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "install"])

        assert result.exit_code == 0
        assert "installed" in result.output.lower()

    def test_install_failure_exits_1(self) -> None:
        """RuntimeError from ensure_installed exits 1."""
        mock_runtime = _mock_runtime()
        mock_runtime.ensure_installed.side_effect = RuntimeError("Download failed: 404")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "install"])

        assert result.exit_code == 1
        assert "failed" in result.output.lower()

    def test_install_success_json_mode(self, tmp_path: Path) -> None:
        """JSON mode emits installed=True with path and version."""
        installed_path = tmp_path / "bin" / "codex-test-v1"
        mock_runtime = _mock_runtime(version="test-v1")
        mock_runtime.ensure_installed.return_value = installed_path

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "install"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["installed"] is True
        assert "path" in payload
        assert payload["version"] == "test-v1"

    def test_install_failure_json_mode(self) -> None:
        """JSON mode emits installed=False with error on failure."""
        mock_runtime = _mock_runtime()
        mock_runtime.ensure_installed.side_effect = RuntimeError("checksum mismatch")

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "install"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["installed"] is False
        assert "checksum mismatch" in payload["error"]


# ---------------------------------------------------------------------------
# agent version
# ---------------------------------------------------------------------------


class TestAgentVersion:
    """Tests for 'pretorin agent version'."""

    def test_version_installed(self) -> None:
        """Installed binary shows version and 'installed' status."""
        mock_runtime = _mock_runtime(version="rust-v0.88.0", is_installed=True)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "version"])

        assert result.exit_code == 0
        assert "rust-v0.88.0" in result.output
        assert "installed" in result.output

    def test_version_not_installed(self) -> None:
        """Not-installed binary shows 'not installed' and install hint."""
        mock_runtime = _mock_runtime(version="rust-v0.88.0", is_installed=False)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["agent", "version"])

        assert result.exit_code == 0
        assert "not installed" in result.output
        assert "install" in result.output.lower()

    def test_version_json_mode(self) -> None:
        """JSON mode emits codex_version, binary_path, and status fields."""
        mock_runtime = _mock_runtime(version="rust-v0.88.0", is_installed=True)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "version"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["codex_version"] == "rust-v0.88.0"
        assert payload["status"] == "installed"
        assert "binary_path" in payload

    def test_version_json_mode_not_installed(self) -> None:
        """JSON mode status is 'not installed' when binary absent."""
        mock_runtime = _mock_runtime(version="rust-v0.88.0", is_installed=False)

        with patch("pretorin.agent.codex_runtime.CodexRuntime", return_value=mock_runtime):
            result = runner.invoke(app, ["--json", "agent", "version"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["status"] == "not installed"


# ---------------------------------------------------------------------------
# agent skills
# ---------------------------------------------------------------------------


class TestAgentSkills:
    """Tests for 'pretorin agent skills'."""

    def _fake_skills(self):
        return [
            SimpleNamespace(name="gap-analysis", description="Find gaps", max_turns=20),
            SimpleNamespace(name="narrative-generation", description="Write narratives", max_turns=15),
        ]

    def test_skills_table_output(self) -> None:
        """Normal mode prints skill names and descriptions in a table."""
        with patch("pretorin.agent.skills.list_skills", return_value=self._fake_skills()):
            result = runner.invoke(app, ["agent", "skills"])

        assert result.exit_code == 0
        assert "gap-analysis" in result.output
        assert "narrative-generation" in result.output

    def test_skills_json_mode(self) -> None:
        """JSON mode emits a list of skill objects."""
        with patch("pretorin.agent.skills.list_skills", return_value=self._fake_skills()):
            result = runner.invoke(app, ["--json", "agent", "skills"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert isinstance(payload, list)
        assert len(payload) == 2
        names = [s["name"] for s in payload]
        assert "gap-analysis" in names
        assert payload[0]["max_turns"] == 20

    def test_skills_shows_usage_hint(self) -> None:
        """Normal mode shows usage hint for --skill flag."""
        with patch("pretorin.agent.skills.list_skills", return_value=self._fake_skills()):
            result = runner.invoke(app, ["agent", "skills"])

        assert result.exit_code == 0
        assert "--skill" in result.output


# ---------------------------------------------------------------------------
# mcp-list
# ---------------------------------------------------------------------------


class TestMcpList:
    """Tests for 'pretorin agent mcp-list'."""

    def test_mcp_list_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No servers shows empty/informational message."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-list"])

        assert result.exit_code == 0
        assert "No MCP servers" in result.output

    def test_mcp_list_with_servers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Servers are displayed in a table with name and transport."""
        import json as _json

        config_data = {"servers": [{"name": "gh", "transport": "stdio", "command": "uvx", "args": ["mcp-server-github"]}]}
        (tmp_path / ".pretorin-mcp.json").write_text(_json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-list"])

        assert result.exit_code == 0
        assert "gh" in result.output

    def test_mcp_list_json_mode_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON mode returns empty list when no servers configured."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["--json", "agent", "mcp-list"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload == []

    def test_mcp_list_json_mode_with_servers(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON mode emits list of server objects."""
        import json as _json

        config_data = {"servers": [{"name": "aws", "transport": "http", "url": "http://localhost:9000"}]}
        (tmp_path / ".pretorin-mcp.json").write_text(_json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["--json", "agent", "mcp-list"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert len(payload) == 1
        assert payload[0]["name"] == "aws"
        assert payload[0]["transport"] == "http"


# ---------------------------------------------------------------------------
# mcp-add
# ---------------------------------------------------------------------------


class TestMcpAdd:
    """Tests for 'pretorin agent mcp-add'."""

    def test_mcp_add_stdio_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid stdio server is added and confirmed."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-add", "myserver", "stdio", "uvx"])

        assert result.exit_code == 0
        assert "myserver" in result.output

    def test_mcp_add_http_success(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Valid http server is added and confirmed."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-add", "myhttp", "http", "http://localhost:8080"])

        assert result.exit_code == 0
        assert "myhttp" in result.output

    def test_mcp_add_invalid_stdio_no_command_exits_1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """stdio transport without command_or_url being a real command fails validation.

        Note: the command_or_url arg is required by typer so will always be present.
        An invalid transport value like 'bad' causes validate() to fail on http (url missing)
        but actually the real validation failure for stdio is if no command is passed.
        We test via a mock to trigger the ValueError branch.
        """
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        # Patch MCPServerConfig.validate to raise ValueError
        with patch("pretorin.agent.mcp_config.MCPServerConfig.validate", side_effect=ValueError("validation failed")):
            result = runner.invoke(app, ["agent", "mcp-add", "bad", "stdio", "cmd"])

        assert result.exit_code == 1
        assert "validation failed" in result.output

    def test_mcp_add_with_scope_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """--scope global persists to the global config file."""
        global_file = tmp_path / "global.json"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", global_file)

        result = runner.invoke(
            app, ["agent", "mcp-add", "gserver", "stdio", "node", "--scope", "global"]
        )

        assert result.exit_code == 0
        assert global_file.exists()
        saved = json.loads(global_file.read_text())
        names = [s["name"] for s in saved["servers"]]
        assert "gserver" in names


# ---------------------------------------------------------------------------
# mcp-remove
# ---------------------------------------------------------------------------


class TestMcpRemove:
    """Tests for 'pretorin agent mcp-remove'."""

    def test_mcp_remove_existing_server(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removing an existing server prints confirmation."""
        import json as _json

        config_data = {"servers": [{"name": "remove-me", "transport": "stdio", "command": "echo"}]}
        (tmp_path / ".pretorin-mcp.json").write_text(_json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-remove", "remove-me"])

        assert result.exit_code == 0
        assert "remove-me" in result.output
        assert "Removed" in result.output

    def test_mcp_remove_nonexistent_server(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Removing a server that does not exist prints a warning but exits 0."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        result = runner.invoke(app, ["agent", "mcp-remove", "ghost"])

        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "ghost" in result.output
