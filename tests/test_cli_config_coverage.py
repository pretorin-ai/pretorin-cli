"""Coverage tests for src/pretorin/cli/config.py.

Covers: config get, config set, config list, config path commands.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.client.config import (
    CONFIG_FILE,
    ENV_API_BASE_URL,
    ENV_API_KEY,
    ENV_DISABLE_UPDATE_CHECK,
    ENV_MODEL_API_BASE_URL,
    ENV_PLATFORM_API_BASE_URL,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# config get
# ---------------------------------------------------------------------------


class TestConfigGet:
    """Tests for `pretorin config get <key>`."""

    def test_get_api_key_masked_when_long(self) -> None:
        """API key longer than 12 chars is displayed with masked middle portion."""
        long_key = "abcdefgh12345678end"

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=long_key)

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "get", "api_key"])

        assert result.exit_code == 0
        assert "..." in result.output
        assert long_key not in result.output

    def test_get_api_key_starred_when_short(self) -> None:
        """API key 12 chars or shorter is replaced with **** in the output."""
        short_key = "shortkey"

        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=short_key)

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "get", "api_key"])

        assert result.exit_code == 0
        assert "****" in result.output

    def test_get_key_not_set_exits_1(self) -> None:
        """Exits with code 1 and prints not-set message for missing key."""
        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value=None)

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "get", "some_key"])

        assert result.exit_code == 1
        assert "not set" in result.output

    def test_get_non_sensitive_key_shows_value(self) -> None:
        """Non-sensitive key value is printed as-is."""
        mock_config = MagicMock()
        mock_config.get = MagicMock(return_value="https://custom.example.com")

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "get", "api_base_url"])

        assert result.exit_code == 0
        assert "https://custom.example.com" in result.output


# ---------------------------------------------------------------------------
# config set
# ---------------------------------------------------------------------------


class TestConfigSet:
    """Tests for `pretorin config set <key> <value>`."""

    def test_set_api_key_refused_with_login_hint(self) -> None:
        """Setting api_key via `config set` is blocked with a helpful message."""
        result = runner.invoke(app, ["config", "set", "api_key", "some-value"])

        assert result.exit_code == 1
        assert "pretorin login" in result.output

    def test_set_custom_key_succeeds(self) -> None:
        """Non-reserved key is written via Config.set and a confirmation is shown."""
        mock_config = MagicMock()
        mock_config.set = MagicMock()

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "set", "custom_key", "my-value"])

        assert result.exit_code == 0
        mock_config.set.assert_called_once_with("custom_key", "my-value")
        assert "custom_key" in result.output
        assert "my-value" in result.output

    def test_set_api_base_url_succeeds(self) -> None:
        """api_base_url can be set (only api_key is blocked)."""
        mock_config = MagicMock()
        mock_config.set = MagicMock()

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(
                app,
                ["config", "set", "api_base_url", "https://self-hosted.example.com"],
            )

        assert result.exit_code == 0
        mock_config.set.assert_called_once_with("api_base_url", "https://self-hosted.example.com")


# ---------------------------------------------------------------------------
# config list
# ---------------------------------------------------------------------------


class TestConfigList:
    """Tests for `pretorin config list`."""

    def test_list_with_stored_config(self) -> None:
        """Stored config entries appear in the output table."""
        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(
            return_value={"api_key": "abcdefgh12345678", "api_base_url": "https://api.example.com"}
        )

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        # api_key should be masked in the table
        assert "..." in result.output or "****" in result.output
        # The config file path footer should appear
        assert str(CONFIG_FILE) in result.output

    def test_list_with_env_var_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An env-var API key appears in the list under the correct source column."""
        monkeypatch.setenv(ENV_API_KEY, "env-api-key-value")

        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert ENV_API_KEY in result.output

    def test_list_with_env_var_api_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """An env-var platform API URL appears in the table."""
        monkeypatch.setenv(ENV_API_BASE_URL, "https://env.test")

        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert "env.test" in result.output
        assert ENV_API_BASE_URL in result.output

    def test_list_with_env_var_platform_api_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENV_PLATFORM_API_BASE_URL is shown when set."""
        monkeypatch.setenv(ENV_PLATFORM_API_BASE_URL, "https://plat.test")

        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert "plat.test" in result.output

    def test_list_with_env_var_model_api_base_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENV_MODEL_API_BASE_URL is shown when set."""
        monkeypatch.setenv(ENV_MODEL_API_BASE_URL, "https://model.test")

        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert "model.test" in result.output

    def test_list_with_env_var_disable_update_check(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """ENV_DISABLE_UPDATE_CHECK is shown when set."""
        monkeypatch.setenv(ENV_DISABLE_UPDATE_CHECK, "1")

        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert ENV_DISABLE_UPDATE_CHECK in result.output

    def test_list_no_config_prints_hint(self) -> None:
        """With no stored config and no env vars, prints a helpful empty-state message."""
        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={})

        # Ensure none of the relevant env vars are set
        env_keys = [
            ENV_API_KEY,
            ENV_API_BASE_URL,
            ENV_PLATFORM_API_BASE_URL,
            ENV_MODEL_API_BASE_URL,
            ENV_DISABLE_UPDATE_CHECK,
        ]
        with patch("pretorin.cli.config.Config", return_value=mock_config), \
             patch.dict("os.environ", {k: "" for k in env_keys}, clear=False):
            # Remove the env keys entirely so os.environ.get returns None
            import os
            saved = {k: os.environ.pop(k, None) for k in env_keys}
            try:
                result = runner.invoke(app, ["config", "list"])
            finally:
                for k, v in saved.items():
                    if v is not None:
                        os.environ[k] = v

        assert result.exit_code == 0
        assert "No configuration set" in result.output

    def test_list_api_key_in_stored_config_is_masked(self) -> None:
        """api_key stored in config file is masked (not shown in plaintext)."""
        long_key = "supersecretapikey1234"
        mock_config = MagicMock()
        mock_config.to_dict = MagicMock(return_value={"api_key": long_key})

        with patch("pretorin.cli.config.Config", return_value=mock_config):
            result = runner.invoke(app, ["config", "list"])

        assert result.exit_code == 0
        assert long_key not in result.output


# ---------------------------------------------------------------------------
# config path
# ---------------------------------------------------------------------------


class TestConfigPath:
    """Tests for `pretorin config path`."""

    def test_path_prints_config_file_location(self) -> None:
        """Prints the path to the configuration file."""
        result = runner.invoke(app, ["config", "path"])

        assert result.exit_code == 0
        assert str(CONFIG_FILE) in result.output
