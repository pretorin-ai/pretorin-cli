"""Tests for src/pretorin/agent/mcp_config.py.

Covers MCPServerConfig and MCPConfigManager across stdio/http transports,
config file loading precedence, add/remove persistence, and SDK conversion.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from pretorin.agent.mcp_config import MCPConfigManager, MCPServerConfig

# ---------------------------------------------------------------------------
# MCPServerConfig – validation
# ---------------------------------------------------------------------------


class TestMCPServerConfigValidation:
    def test_stdio_with_command_validates(self) -> None:
        cfg = MCPServerConfig(name="srv", transport="stdio", command="echo")
        cfg.validate()  # must not raise

    def test_stdio_without_command_raises(self) -> None:
        cfg = MCPServerConfig(name="srv", transport="stdio")
        with pytest.raises(ValueError, match="stdio transport requires 'command'"):
            cfg.validate()

    def test_http_with_url_validates(self) -> None:
        cfg = MCPServerConfig(name="srv", transport="http", url="http://localhost:8080")
        cfg.validate()  # must not raise

    def test_http_without_url_raises(self) -> None:
        cfg = MCPServerConfig(name="srv", transport="http")
        with pytest.raises(ValueError, match="http transport requires 'url'"):
            cfg.validate()


# ---------------------------------------------------------------------------
# MCPServerConfig – to_sdk_server
# ---------------------------------------------------------------------------


class TestMCPServerConfigToSdkServer:
    def test_stdio_returns_stdio_server(self) -> None:
        mock_stdio = MagicMock()
        mock_http = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "agents": MagicMock(),
                "agents.mcp": MagicMock(MCPServerStdio=mock_stdio, MCPServerStreamableHttp=mock_http),
            },
        ):
            cfg = MCPServerConfig(name="my-stdio", transport="stdio", command="npx", args=["server"])
            cfg.to_sdk_server()
            mock_stdio.assert_called_once_with(
                name="my-stdio",
                params={"command": "npx", "args": ["server"]},
            )

    def test_stdio_includes_env_when_set(self) -> None:
        mock_stdio = MagicMock()
        mock_http = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "agents": MagicMock(),
                "agents.mcp": MagicMock(MCPServerStdio=mock_stdio, MCPServerStreamableHttp=mock_http),
            },
        ):
            cfg = MCPServerConfig(name="srv", transport="stdio", command="run", env={"TOKEN": "abc"})
            cfg.to_sdk_server()
            call_params = mock_stdio.call_args[1]["params"]
            assert call_params["env"] == {"TOKEN": "abc"}

    def test_http_returns_http_server(self) -> None:
        mock_stdio = MagicMock()
        mock_http = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "agents": MagicMock(),
                "agents.mcp": MagicMock(MCPServerStdio=mock_stdio, MCPServerStreamableHttp=mock_http),
            },
        ):
            cfg = MCPServerConfig(name="my-http", transport="http", url="http://localhost:9000")
            cfg.to_sdk_server()
            mock_http.assert_called_once_with(
                name="my-http",
                params={"url": "http://localhost:9000"},
            )

    def test_unknown_transport_raises_value_error(self) -> None:
        mock_stdio = MagicMock()
        mock_http = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "agents": MagicMock(),
                "agents.mcp": MagicMock(MCPServerStdio=mock_stdio, MCPServerStreamableHttp=mock_http),
            },
        ):
            cfg = MCPServerConfig(name="srv", transport="grpc", command="run")
            # validate() passes for non-stdio/http (no rule), but to_sdk_server must raise
            with pytest.raises(ValueError, match="Unknown transport"):
                cfg.to_sdk_server()

    def test_missing_agents_package_raises_import_error(self) -> None:
        import sys

        real_modules = {k: v for k, v in sys.modules.items() if k in ("agents", "agents.mcp")}
        sys.modules.pop("agents", None)
        sys.modules.pop("agents.mcp", None)

        # Patch the import inside to_sdk_server to raise ImportError
        cfg = MCPServerConfig(name="srv", transport="stdio", command="run")
        with patch.dict("sys.modules", {"agents": None, "agents.mcp": None}):
            with pytest.raises(ImportError, match="openai-agents"):
                cfg.to_sdk_server()

        # Restore
        sys.modules.update(real_modules)


# ---------------------------------------------------------------------------
# MCPConfigManager – loading
# ---------------------------------------------------------------------------


class TestMCPConfigManagerLoading:
    def test_loads_project_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_data = {"servers": [{"name": "test", "transport": "stdio", "command": "echo", "args": ["hello"]}]}
        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text(json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()

        assert len(mgr.servers) == 1
        assert mgr.servers[0].name == "test"
        assert mgr.servers[0].command == "echo"

    def test_loads_global_config(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        global_file = tmp_path / "global.json"
        global_file.write_text(
            json.dumps({"servers": [{"name": "global-srv", "transport": "stdio", "command": "python"}]})
        )
        empty_dir = tmp_path / "project"
        empty_dir.mkdir()
        monkeypatch.chdir(empty_dir)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", global_file)

        mgr = MCPConfigManager()

        assert len(mgr.servers) == 1
        assert mgr.servers[0].name == "global-srv"

    def test_project_takes_precedence_over_global(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Both have a server called "shared"; project should win.
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".pretorin-mcp.json").write_text(
            json.dumps({"servers": [{"name": "shared", "transport": "stdio", "command": "project-cmd"}]})
        )
        global_file = tmp_path / "global.json"
        global_file.write_text(
            json.dumps({"servers": [{"name": "shared", "transport": "stdio", "command": "global-cmd"}]})
        )
        monkeypatch.chdir(project_dir)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", global_file)

        mgr = MCPConfigManager()

        assert len(mgr.servers) == 1
        assert mgr.servers[0].command == "project-cmd"

    def test_invalid_json_handled_gracefully(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text("{ this is not valid JSON !!!")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()

        assert mgr.servers == []

    def test_missing_files_handled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "nonexistent.json")

        mgr = MCPConfigManager()

        assert mgr.servers == []

    def test_entry_missing_name_is_skipped(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_data = {
            "servers": [
                {"transport": "stdio", "command": "echo"},  # no 'name'
                {"name": "valid", "transport": "stdio", "command": "run"},
            ]
        }
        (tmp_path / ".pretorin-mcp.json").write_text(json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()

        assert len(mgr.servers) == 1
        assert mgr.servers[0].name == "valid"


# ---------------------------------------------------------------------------
# MCPConfigManager – add_server / remove_server
# ---------------------------------------------------------------------------


class TestMCPConfigManagerMutation:
    def test_add_server_project_scope_persists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(name="new-srv", transport="stdio", command="node")
        mgr.add_server(cfg, scope="project")

        saved = json.loads((tmp_path / ".pretorin-mcp.json").read_text())
        names = [s["name"] for s in saved["servers"]]
        assert "new-srv" in names

    def test_add_server_global_scope_persists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        global_file = tmp_path / "global.json"
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", global_file)

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(name="global-new", transport="http", url="http://example.com")
        mgr.add_server(cfg, scope="global")

        saved = json.loads(global_file.read_text())
        names = [s["name"] for s in saved["servers"]]
        assert "global-new" in names

    def test_add_server_replaces_existing_name(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()
        mgr.add_server(MCPServerConfig(name="dup", transport="stdio", command="v1"))
        mgr.add_server(MCPServerConfig(name="dup", transport="stdio", command="v2"))

        assert len(mgr.servers) == 1
        assert mgr.servers[0].command == "v2"

    def test_remove_server_that_exists(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        (tmp_path / ".pretorin-mcp.json").write_text(
            json.dumps({"servers": [{"name": "to-remove", "transport": "stdio", "command": "run"}]})
        )
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()
        removed = mgr.remove_server("to-remove")

        assert removed is True
        assert mgr.servers == []

    def test_remove_server_that_does_not_exist(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()
        removed = mgr.remove_server("ghost")

        assert removed is False


# ---------------------------------------------------------------------------
# MCPConfigManager – to_sdk_servers
# ---------------------------------------------------------------------------


class TestMCPConfigManagerToSdkServers:
    def test_to_sdk_servers_converts_all(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config_data = {
            "servers": [
                {"name": "a", "transport": "stdio", "command": "cmd-a"},
                {"name": "b", "transport": "stdio", "command": "cmd-b"},
            ]
        }
        (tmp_path / ".pretorin-mcp.json").write_text(json.dumps(config_data))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json")

        mgr = MCPConfigManager()
        mock_stdio = MagicMock(side_effect=lambda name, params: SimpleNamespace(name=name))
        mock_http = MagicMock()
        with patch.dict(
            "sys.modules",
            {
                "agents": MagicMock(),
                "agents.mcp": MagicMock(MCPServerStdio=mock_stdio, MCPServerStreamableHttp=mock_http),
            },
        ):
            sdk_servers = mgr.to_sdk_servers()

        assert len(sdk_servers) == 2
