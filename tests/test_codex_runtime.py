"""Tests for Codex runtime binary management."""

from __future__ import annotations

import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from pretorin.agent.codex_runtime import CodexRuntime, _detect_platform


class TestDetectPlatform:
    """Platform detection tests."""

    def test_darwin_arm64(self) -> None:
        with patch("pretorin.agent.codex_runtime.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            mock_platform.machine.return_value = "arm64"
            assert _detect_platform() == "darwin-arm64"

    def test_darwin_x64(self) -> None:
        with patch("pretorin.agent.codex_runtime.platform") as mock_platform:
            mock_platform.system.return_value = "Darwin"
            mock_platform.machine.return_value = "x86_64"
            assert _detect_platform() == "darwin-x64"

    def test_linux_x64(self) -> None:
        with patch("pretorin.agent.codex_runtime.platform") as mock_platform:
            mock_platform.system.return_value = "Linux"
            mock_platform.machine.return_value = "x86_64"
            assert _detect_platform() == "linux-x64"

    def test_unsupported_platform_raises(self) -> None:
        with patch("pretorin.agent.codex_runtime.platform") as mock_platform:
            mock_platform.system.return_value = "Windows"
            mock_platform.machine.return_value = "AMD64"
            with pytest.raises(RuntimeError, match="Unsupported platform"):
                _detect_platform()


class TestCodexRuntime:
    """CodexRuntime lifecycle tests."""

    def test_binary_path_includes_version(self, tmp_path: Path) -> None:
        runtime = CodexRuntime(version="test-v1.0.0")
        runtime.bin_dir = tmp_path / "bin"
        assert runtime.binary_path == tmp_path / "bin" / "codex-test-v1.0.0"

    def test_is_installed_false_when_missing(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.bin_dir = tmp_path / "bin"
        assert not runtime.is_installed

    def test_is_installed_true_when_executable(self, tmp_path: Path) -> None:
        runtime = CodexRuntime(version="test-v1")
        runtime.bin_dir = tmp_path / "bin"
        runtime.bin_dir.mkdir(parents=True)
        binary = runtime.binary_path
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)
        assert runtime.is_installed

    def test_is_installed_false_when_not_executable(self, tmp_path: Path) -> None:
        runtime = CodexRuntime(version="test-v1")
        runtime.bin_dir = tmp_path / "bin"
        runtime.bin_dir.mkdir(parents=True)
        binary = runtime.binary_path
        binary.write_text("not executable")
        binary.chmod(stat.S_IRUSR | stat.S_IWUSR)
        assert not runtime.is_installed

    def test_build_env_isolates_codex_home(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.codex_home = tmp_path / "codex"
        env = runtime.build_env(api_key="sk-test", base_url="https://example.com/v1")

        assert env["CODEX_HOME"] == str(tmp_path / "codex")
        assert env["OPENAI_API_KEY"] == "sk-test"
        assert env["OPENAI_BASE_URL"] == "https://example.com/v1"
        assert "PATH" in env
        assert "HOME" in env

    def test_build_env_accepts_extra_vars(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.codex_home = tmp_path / "codex"
        env = runtime.build_env(
            api_key="sk-test",
            base_url="https://example.com/v1",
            CUSTOM_VAR="custom_value",
        )
        assert env["CUSTOM_VAR"] == "custom_value"

    def test_write_config_creates_isolated_toml(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.codex_home = tmp_path / "codex"

        config_path = runtime.write_config(
            model="gpt-4o",
            provider_name="pretorin",
            base_url="https://platform.pretorin.com/v1",
            env_key="OPENAI_API_KEY",
        )

        assert config_path == tmp_path / "codex" / "config.toml"
        assert config_path.exists()

        content = config_path.read_text()
        assert 'model_provider = "pretorin"' in content
        assert 'base_url = "https://platform.pretorin.com/v1"' in content
        assert 'env_key = "OPENAI_API_KEY"' in content
        assert "[mcp_servers.pretorin]" in content
        assert 'command = "pretorin"' in content
        assert 'args = ["mcp-serve"]' in content

    def test_write_config_does_not_touch_user_codex(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.codex_home = tmp_path / "codex"

        # Simulate a user's ~/.codex/config.toml
        user_codex = tmp_path / ".codex"
        user_codex.mkdir()
        user_config = user_codex / "config.toml"
        user_config.write_text("# user config\n")

        runtime.write_config(
            model="gpt-4o",
            provider_name="pretorin",
            base_url="https://example.com/v1",
            env_key="OPENAI_API_KEY",
        )

        # User's config must remain untouched
        assert user_config.read_text() == "# user config\n"

    def test_write_config_merges_user_mcp_servers(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.codex_home = tmp_path / "codex"

        # Create a user mcp.json
        mcp_dir = tmp_path / ".pretorin"
        mcp_dir.mkdir()
        mcp_json = mcp_dir / "mcp.json"
        mcp_json.write_text('{"servers": {"github": {"command": "uvx", "args": ["mcp-server-github"]}}}')

        with patch("pathlib.Path.home", return_value=tmp_path):
            config_path = runtime.write_config(
                model="gpt-4o",
                provider_name="pretorin",
                base_url="https://example.com/v1",
                env_key="OPENAI_API_KEY",
            )

        content = config_path.read_text()
        assert "[mcp_servers.pretorin]" in content
        assert "[mcp_servers.github]" in content
        assert 'command = "uvx"' in content

    def test_cleanup_old_versions(self, tmp_path: Path) -> None:
        runtime = CodexRuntime(version="test-v2")
        runtime.bin_dir = tmp_path / "bin"
        runtime.bin_dir.mkdir(parents=True)

        # Create old and current binaries
        old = runtime.bin_dir / "codex-test-v1"
        old.write_text("old")
        current = runtime.bin_dir / "codex-test-v2"
        current.write_text("current")

        # Also a non-codex file that should not be removed
        other = runtime.bin_dir / "other-tool"
        other.write_text("other")

        removed = runtime.cleanup_old_versions()
        assert old in removed
        assert not old.exists()
        assert current.exists()
        assert other.exists()

    def test_cleanup_empty_bin_dir(self, tmp_path: Path) -> None:
        runtime = CodexRuntime()
        runtime.bin_dir = tmp_path / "nonexistent"
        removed = runtime.cleanup_old_versions()
        assert removed == []

    def test_ensure_installed_returns_path_when_already_installed(self, tmp_path: Path) -> None:
        runtime = CodexRuntime(version="test-v1")
        runtime.bin_dir = tmp_path / "bin"
        runtime.bin_dir.mkdir(parents=True)
        binary = runtime.binary_path
        binary.write_text("#!/bin/sh\necho test")
        binary.chmod(binary.stat().st_mode | stat.S_IXUSR)

        result = runtime.ensure_installed()
        assert result == binary
