"""Coverage tests for src/pretorin/cli/main.py.

Targets missing lines: show_banner, _should_show_update_notice,
_maybe_print_update_notice, _version_callback, main callback (JSON output),
version command, update command, mcp_serve command.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin import __version__
from pretorin.cli.main import _should_show_update_notice, app, show_banner
from pretorin.cli.output import set_json_mode

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


# ---------------------------------------------------------------------------
# --version flag
# ---------------------------------------------------------------------------


class TestVersionFlag:
    def test_version_flag_prints_version_and_exits(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_short_version_flag(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_flag_includes_pretorin_label(self):
        result = runner.invoke(app, ["--version"])
        assert "pretorin" in result.output.lower()


# ---------------------------------------------------------------------------
# No-subcommand (banner + help)
# ---------------------------------------------------------------------------


class TestNoSubcommand:
    def test_no_args_exits_zero(self):
        result = runner.invoke(app, [])
        assert result.exit_code == 0

    def test_no_args_outputs_something(self):
        result = runner.invoke(app, [])
        assert result.output.strip() != ""

    def test_json_flag_no_subcommand_prints_json_version(self):
        result = runner.invoke(app, ["--json"])
        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["version"] == __version__


# ---------------------------------------------------------------------------
# version subcommand
# ---------------------------------------------------------------------------


class TestVersionSubcommand:
    def test_version_subcommand_prints_version(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_subcommand_includes_label(self):
        result = runner.invoke(app, ["version"])
        assert "pretorin" in result.output.lower()


# ---------------------------------------------------------------------------
# _should_show_update_notice
# ---------------------------------------------------------------------------


class TestShouldShowUpdateNotice:
    def test_returns_false_when_json_output(self):
        assert _should_show_update_notice(json_output=True) is False

    def test_returns_false_when_subcommand_is_update(self):
        assert _should_show_update_notice(invoked_subcommand="update") is False

    def test_returns_false_when_subcommand_is_mcp_serve(self):
        assert _should_show_update_notice(invoked_subcommand="mcp-serve") is False

    def test_returns_false_when_not_a_tty(self):
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty = lambda: False
            result = _should_show_update_notice()
        assert result is False

    def test_returns_true_when_tty_and_no_exclusions(self):
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty = lambda: True
            result = _should_show_update_notice()
        assert result is True

    def test_json_output_overrides_tty(self):
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.isatty = lambda: True
            result = _should_show_update_notice(json_output=True)
        assert result is False


# ---------------------------------------------------------------------------
# show_banner
# ---------------------------------------------------------------------------


class TestShowBanner:
    def test_show_banner_without_update_check_does_not_call_update(self):
        with patch("pretorin.cli.main._maybe_print_update_notice") as mock_notice:
            show_banner(check_updates=False)
        mock_notice.assert_not_called()

    def test_show_banner_with_update_check_calls_notice(self):
        with patch("pretorin.cli.main._maybe_print_update_notice") as mock_notice:
            show_banner(check_updates=True)
        mock_notice.assert_called_once()


# ---------------------------------------------------------------------------
# update command
# ---------------------------------------------------------------------------


class TestUpdateCommand:
    def test_update_already_up_to_date(self):
        mock_result = MagicMock()
        mock_result.checked = True
        mock_result.latest_version = __version__

        with patch("pretorin.cli.version_check.check_for_updates", return_value=mock_result):
            with patch("subprocess.run"):
                result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "latest" in result.output.lower() or __version__ in result.output

    def test_update_available_runs_pip(self):
        mock_result = MagicMock()
        mock_result.checked = True
        mock_result.update_available = True
        mock_result.latest_version = "99.9.9"

        with patch("pretorin.cli.version_check.check_for_updates", return_value=mock_result):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
        assert "99.9.9" in result.output

    def test_update_version_check_fails_still_succeeds(self):
        mock_result = MagicMock()
        mock_result.checked = False
        mock_result.latest_version = None

        with patch("pretorin.cli.version_check.check_for_updates", return_value=mock_result):
            with patch("subprocess.run"):
                result = runner.invoke(app, ["update"])

        assert result.exit_code == 0
        assert "update complete" in result.output.lower()

    def test_update_pip_fails_exits_one(self):
        import subprocess

        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "pip")):
            result = runner.invoke(app, ["update"])

        assert result.exit_code == 1
        assert "failed" in result.output.lower() or "manually" in result.output.lower()


# ---------------------------------------------------------------------------
# mcp-serve command
# ---------------------------------------------------------------------------


class TestMcpServeCommand:
    def test_mcp_serve_calls_run_server(self):
        with patch("pretorin.mcp.server.run_server") as mock_run:
            result = runner.invoke(app, ["mcp-serve"])

        assert result.exit_code == 0
        mock_run.assert_called_once()
