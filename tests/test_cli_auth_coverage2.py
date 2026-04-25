"""Additional coverage tests for src/pretorin/cli/auth.py.

Covers lines 70-71 (empty API key after prompt) and 180-182 (PretorianClientError
in whoami).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import PretorianClientError

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


class TestLoginEmptyApiKey:
    """Tests for login when the user provides an empty API key."""

    def test_login_empty_api_key_after_prompt_exits_one(self) -> None:
        """When user enters empty string at prompt, exit code 1 and message shown."""
        mock_config = MagicMock()
        mock_config.is_configured = False

        with patch("pretorin.cli.auth.Config", return_value=mock_config):
            # Simulate user entering empty string at prompt
            result = runner.invoke(app, ["login"], input="\n")

        assert result.exit_code == 1
        assert "API key is required" in result.output


class TestWhoamiClientError:
    """Tests for whoami PretorianClientError path."""

    def test_whoami_client_error_exits_one(self) -> None:
        """PretorianClientError during session check causes exit code 1."""
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = "abcdefgh12345678"

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(
            side_effect=PretorianClientError("Service unavailable", status_code=503)
        )
        mock_client._api_base_url = "https://api.example.com"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_client),
            patch("pretorin.cli.auth.animated_status") as mock_anim,
        ):
            mock_anim.return_value.__enter__ = MagicMock(return_value=None)
            mock_anim.return_value.__exit__ = MagicMock(return_value=False)

            result = runner.invoke(app, ["whoami"])

        assert result.exit_code == 1
        assert "Service unavailable" in result.output
