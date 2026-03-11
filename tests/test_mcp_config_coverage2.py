"""Additional coverage tests for src/pretorin/agent/mcp_config.py.

Covers:
- _save_to_file lines 179-180: file exists but has JSON decode error
- _save_to_file line 194: config has args
- _save_to_file line 196: config has env
- _remove_from_file lines 212-213: file has JSON decode error
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pretorin.agent.mcp_config import MCPConfigManager, MCPServerConfig


class TestSaveToFileJsonDecodeError:
    """Cover _save_to_file when file exists but contains invalid JSON."""

    def test_save_to_file_with_corrupted_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the existing file has a JSON decode error, it should reset to empty."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        # Write invalid JSON to the project config file
        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text("{ this is not valid JSON !!!")

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(name="new-srv", transport="stdio", command="echo")
        mgr.add_server(cfg, scope="project")

        # The file should now contain valid JSON with the new server
        saved = json.loads(config_file.read_text())
        names = [s["name"] for s in saved["servers"]]
        assert "new-srv" in names

    def test_save_to_file_with_empty_existing_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """An empty file also triggers JSONDecodeError and should be handled."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text("")

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(name="recover-srv", transport="stdio", command="node")
        mgr.add_server(cfg, scope="project")

        saved = json.loads(config_file.read_text())
        assert len(saved["servers"]) == 1
        assert saved["servers"][0]["name"] == "recover-srv"


class TestSaveToFileWithArgsAndEnv:
    """Cover _save_to_file when config has args (line 194) and env (line 196)."""

    def test_save_includes_args(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config with args persists args field to JSON."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(
            name="with-args",
            transport="stdio",
            command="npx",
            args=["mcp-server-github", "--verbose"],
        )
        mgr.add_server(cfg, scope="project")

        saved = json.loads((tmp_path / ".pretorin-mcp.json").read_text())
        server_entry = saved["servers"][0]
        assert server_entry["args"] == ["mcp-server-github", "--verbose"]

    def test_save_includes_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config with env persists env field to JSON."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(
            name="with-env",
            transport="stdio",
            command="node",
            env={"GITHUB_TOKEN": "ghp_test123", "DEBUG": "true"},
        )
        mgr.add_server(cfg, scope="project")

        saved = json.loads((tmp_path / ".pretorin-mcp.json").read_text())
        server_entry = saved["servers"][0]
        assert server_entry["env"] == {"GITHUB_TOKEN": "ghp_test123", "DEBUG": "true"}

    def test_save_includes_both_args_and_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config with both args and env persists both fields."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(
            name="full-config",
            transport="stdio",
            command="npx",
            args=["server", "--port", "3000"],
            env={"NODE_ENV": "production"},
        )
        mgr.add_server(cfg, scope="project")

        saved = json.loads((tmp_path / ".pretorin-mcp.json").read_text())
        server_entry = saved["servers"][0]
        assert server_entry["args"] == ["server", "--port", "3000"]
        assert server_entry["env"] == {"NODE_ENV": "production"}
        assert server_entry["command"] == "npx"
        assert server_entry["transport"] == "stdio"

    def test_save_omits_empty_args_and_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Config without args/env should not include those keys in the JSON."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        mgr = MCPConfigManager()
        cfg = MCPServerConfig(
            name="minimal",
            transport="stdio",
            command="echo",
        )
        mgr.add_server(cfg, scope="project")

        saved = json.loads((tmp_path / ".pretorin-mcp.json").read_text())
        server_entry = saved["servers"][0]
        assert "args" not in server_entry
        assert "env" not in server_entry


class TestRemoveFromFileJsonDecodeError:
    """Cover _remove_from_file when file has JSON decode error (lines 212-213)."""

    def test_remove_from_corrupted_file_returns_gracefully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the config file has invalid JSON, _remove_from_file should return without error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        # First create a valid config with a server
        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text(
            json.dumps(
                {"servers": [{"name": "srv-to-remove", "transport": "stdio", "command": "echo"}]}
            )
        )

        mgr = MCPConfigManager()
        assert len(mgr.servers) == 1

        # Corrupt the file before removal
        config_file.write_text("NOT VALID JSON {{{")

        # remove_server should still succeed (removes from in-memory list,
        # _remove_from_file catches the JSON decode error)
        removed = mgr.remove_server("srv-to-remove")
        assert removed is True
        assert len(mgr.servers) == 0
        # The corrupted file should remain unchanged (not overwritten)
        assert config_file.read_text() == "NOT VALID JSON {{{"

    def test_remove_from_empty_file_returns_gracefully(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When the config file is empty, _remove_from_file returns without error."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "pretorin.agent.mcp_config.GLOBAL_CONFIG_FILE", tmp_path / "global.json"
        )

        # Create valid config first for in-memory loading
        config_file = tmp_path / ".pretorin-mcp.json"
        config_file.write_text(
            json.dumps(
                {"servers": [{"name": "test-srv", "transport": "stdio", "command": "run"}]}
            )
        )

        mgr = MCPConfigManager()

        # Now make the file empty (triggers JSONDecodeError in _remove_from_file)
        config_file.write_text("")

        removed = mgr.remove_server("test-srv")
        assert removed is True
