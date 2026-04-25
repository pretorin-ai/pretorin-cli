"""Coverage tests for src/pretorin/cli/auth.py.

Covers: login, logout, whoami commands.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import AuthenticationError, PretorianClientError

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(*, is_configured: bool = True) -> AsyncMock:
    """Return an AsyncMock that behaves as a PretorianClient context manager."""
    client = AsyncMock()
    client.is_configured = is_configured
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


# ---------------------------------------------------------------------------
# login --api-key
# ---------------------------------------------------------------------------


class TestLoginWithApiKey:
    """Tests for `pretorin login --api-key <key>`."""

    def test_login_success_stores_credentials(self) -> None:
        """Successful validation causes store_credentials to be called."""
        with (
            patch("pretorin.cli.auth.PretorianClient") as mock_client_cls,
            patch("pretorin.cli.auth.store_credentials") as mock_store,
            patch("pretorin.cli.auth.animated_status") as mock_anim,
        ):
            mock_anim.return_value.__enter__ = MagicMock(return_value=None)
            mock_anim.return_value.__exit__ = MagicMock(return_value=False)

            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.validate_api_key = AsyncMock(return_value=None)
            mock_client.close = AsyncMock()
            mock_client._api_base_url = "https://api.example.com"

            result = runner.invoke(app, ["login", "--api-key", "test-key-longer-than-12"])

        assert result.exit_code == 0
        mock_store.assert_called_once_with("test-key-longer-than-12", None)

    def test_login_authentication_error(self) -> None:
        """AuthenticationError from validate_api_key causes exit code 1."""
        with (
            patch("pretorin.cli.auth.PretorianClient") as mock_client_cls,
            patch("pretorin.cli.auth.store_credentials") as mock_store,
            patch("pretorin.cli.auth.animated_status") as mock_anim,
        ):
            mock_anim.return_value.__enter__ = MagicMock(return_value=None)
            mock_anim.return_value.__exit__ = MagicMock(return_value=False)

            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.validate_api_key = AsyncMock(
                side_effect=AuthenticationError("Invalid API key", status_code=401)
            )
            mock_client.close = AsyncMock()
            mock_client._api_base_url = "https://api.example.com"

            result = runner.invoke(app, ["login", "--api-key", "bad-key"])

        assert result.exit_code == 1
        mock_store.assert_not_called()
        assert "Authentication failed" in result.output

    def test_login_client_error(self) -> None:
        """PretorianClientError from validate_api_key causes exit code 1."""
        with (
            patch("pretorin.cli.auth.PretorianClient") as mock_client_cls,
            patch("pretorin.cli.auth.store_credentials") as mock_store,
            patch("pretorin.cli.auth.animated_status") as mock_anim,
        ):
            mock_anim.return_value.__enter__ = MagicMock(return_value=None)
            mock_anim.return_value.__exit__ = MagicMock(return_value=False)

            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.validate_api_key = AsyncMock(
                side_effect=PretorianClientError("Service unavailable", status_code=503)
            )
            mock_client.close = AsyncMock()
            mock_client._api_base_url = "https://api.example.com"

            result = runner.invoke(app, ["login", "--api-key", "some-key"])

        assert result.exit_code == 1
        mock_store.assert_not_called()

    def test_login_with_custom_api_url(self) -> None:
        """--api-url is forwarded to PretorianClient and store_credentials."""
        with (
            patch("pretorin.cli.auth.PretorianClient") as mock_client_cls,
            patch("pretorin.cli.auth.store_credentials") as mock_store,
            patch("pretorin.cli.auth.animated_status") as mock_anim,
        ):
            mock_anim.return_value.__enter__ = MagicMock(return_value=None)
            mock_anim.return_value.__exit__ = MagicMock(return_value=False)

            mock_client = AsyncMock()
            mock_client_cls.return_value = mock_client
            mock_client.validate_api_key = AsyncMock(return_value=None)
            mock_client.close = AsyncMock()
            mock_client._api_base_url = "https://self-hosted.example.com"

            result = runner.invoke(
                app,
                ["login", "--api-key", "my-key-abc-1234", "--api-url", "https://self-hosted.example.com"],
            )

        assert result.exit_code == 0
        mock_store.assert_called_once_with("my-key-abc-1234", "https://self-hosted.example.com")


# ---------------------------------------------------------------------------
# login without --api-key (already-authenticated path)
# ---------------------------------------------------------------------------


class TestLoginWithoutApiKey:
    """Tests for `pretorin login` when no key is provided."""

    def test_login_already_authenticated_skips_prompt(self) -> None:
        """When already configured and validation succeeds, prints already-authenticated message."""
        mock_ctx_client = AsyncMock()
        mock_ctx_client.validate_api_key = AsyncMock(return_value=None)
        mock_ctx_client.__aenter__ = AsyncMock(return_value=mock_ctx_client)
        mock_ctx_client.__aexit__ = AsyncMock(return_value=None)

        mock_config = MagicMock()
        mock_config.is_configured = True

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_ctx_client),
        ):
            result = runner.invoke(app, ["login"])

        assert result.exit_code == 0
        assert "Already authenticated" in result.output

    def test_login_already_configured_but_validation_fails_proceeds_to_prompt(self) -> None:
        """When configured but validation fails, falls through to the prompt."""
        # The _check_existing() path uses PretorianClient as context manager.
        # Make validate_api_key fail on first call (existing check), succeed on second (new key).
        call_count = 0

        async def _validate_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthenticationError("Expired", status_code=401)

        mock_client = AsyncMock()
        mock_client.validate_api_key = AsyncMock(side_effect=_validate_side_effect)
        mock_client.close = AsyncMock()
        mock_client._api_base_url = "https://api.test"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_config = MagicMock()
        mock_config.is_configured = True

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_client),
            patch("pretorin.cli.auth.store_credentials"),
        ):
            result = runner.invoke(app, ["login"], input="new-key-12345\n")

        # First validation fails so it falls through to prompt;
        # second validation (with new key) succeeds.
        assert result.exit_code == 0
        assert "Welcome to Pretorin" in result.output


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------


class TestLogout:
    """Tests for `pretorin logout`."""

    def test_logout_when_logged_in(self) -> None:
        """clear_credentials is called and success message printed."""
        mock_config = MagicMock()
        mock_config.is_configured = True

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.clear_credentials") as mock_clear,
        ):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        mock_clear.assert_called_once()
        assert "Logged out" in result.output

    def test_logout_when_not_logged_in(self) -> None:
        """Prints informational message and exits cleanly when not configured."""
        mock_config = MagicMock()
        mock_config.is_configured = False

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.clear_credentials") as mock_clear,
        ):
            result = runner.invoke(app, ["logout"])

        assert result.exit_code == 0
        mock_clear.assert_not_called()
        assert "not currently logged in" in result.output


# ---------------------------------------------------------------------------
# whoami
# ---------------------------------------------------------------------------


class TestWhoami:
    """Tests for `pretorin whoami`."""

    def _make_framework_list(self, total: int = 5) -> MagicMock:
        fl = MagicMock()
        fl.total = total
        return fl

    def test_whoami_authenticated_normal_mode(self) -> None:
        """Displays session panel when authenticated in normal mode."""
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = "abcdefgh12345678"  # > 12 chars so it gets masked

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(return_value=None)
        mock_client.list_frameworks = AsyncMock(return_value=self._make_framework_list(10))
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

        assert result.exit_code == 0
        assert "Authenticated" in result.output

    def test_whoami_authenticated_json_mode(self) -> None:
        """JSON output contains expected fields when authenticated."""
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = "abcdefgh12345678"

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(return_value=None)
        mock_client.list_frameworks = AsyncMock(return_value=self._make_framework_list(7))
        mock_client._api_base_url = "https://api.example.com"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_client),
        ):
            result = runner.invoke(app, ["--json", "whoami"])

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["authenticated"] is True
        assert payload["frameworks_available"] == 7
        assert "api_key" in payload

    def test_whoami_not_authenticated_normal_mode(self) -> None:
        """Exits with code 1 and prints login suggestion when not configured."""
        mock_config = MagicMock()
        mock_config.is_configured = False

        with patch("pretorin.cli.auth.Config", return_value=mock_config):
            result = runner.invoke(app, ["whoami"])

        assert result.exit_code == 1
        assert "Not logged in" in result.output

    def test_whoami_not_authenticated_json_mode(self) -> None:
        """JSON output contains authenticated=false when not configured."""
        mock_config = MagicMock()
        mock_config.is_configured = False

        with patch("pretorin.cli.auth.Config", return_value=mock_config):
            result = runner.invoke(app, ["--json", "whoami"])

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["authenticated"] is False

    def test_whoami_authentication_error_from_validate(self) -> None:
        """AuthenticationError during session check causes exit code 1."""
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = "shortkey"

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(side_effect=AuthenticationError("Token revoked", status_code=401))
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
        assert "Authentication issue" in result.output

    def test_whoami_api_key_masked_when_long(self) -> None:
        """API key longer than 12 chars is displayed masked in JSON output."""
        long_key = "abcdefgh12345678end"  # > 12 chars
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = long_key

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(return_value=None)
        mock_client.list_frameworks = AsyncMock(return_value=self._make_framework_list(3))
        mock_client._api_base_url = "https://api.example.com"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_client),
        ):
            result = runner.invoke(app, ["--json", "whoami"])

        payload = json.loads(result.output)
        assert "..." in payload["api_key"]
        assert long_key not in payload["api_key"]

    def test_whoami_api_key_starred_when_short(self) -> None:
        """API key 12 chars or shorter is replaced with *** in JSON output."""
        short_key = "shortkey123"  # <= 12 chars
        mock_config = MagicMock()
        mock_config.is_configured = True
        mock_config.api_key = short_key

        mock_client = AsyncMock()
        mock_client.is_configured = True
        mock_client.validate_api_key = AsyncMock(return_value=None)
        mock_client.list_frameworks = AsyncMock(return_value=self._make_framework_list(2))
        mock_client._api_base_url = "https://api.example.com"
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with (
            patch("pretorin.cli.auth.Config", return_value=mock_config),
            patch("pretorin.cli.auth.PretorianClient", return_value=mock_client),
        ):
            result = runner.invoke(app, ["--json", "whoami"])

        payload = json.loads(result.output)
        assert payload["api_key"] == "***"
