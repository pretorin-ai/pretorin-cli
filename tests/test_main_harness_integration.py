"""Integration tests for CLI root app behaviour (update notices, JSON mode)."""

from __future__ import annotations

import json
from unittest.mock import patch

from typer.testing import CliRunner

from pretorin.cli.main import app as main_app
from pretorin.cli.output import set_json_mode
from pytest import fixture

runner = CliRunner()


@fixture(autouse=True)
def reset_json_mode() -> None:
    """Ensure JSON mode does not leak between tests."""
    set_json_mode(False)
    yield
    set_json_mode(False)


def test_root_cli_shows_update_notice_for_interactive_subcommands() -> None:
    with patch("pretorin.cli.main._should_show_update_notice", return_value=True):
        with patch("pretorin.cli.version_check.get_update_message", return_value="Update available"):
            result = runner.invoke(main_app, ["config", "path"])

    assert result.exit_code == 0
    assert "Update available" in result.stdout


def test_root_cli_suppresses_update_notice_for_json_mode() -> None:
    with patch("pretorin.cli.main._should_show_update_notice", return_value=True):
        with patch("pretorin.cli.version_check.get_update_message", return_value="Update available"):
            result = runner.invoke(main_app, ["--json"])

    assert result.exit_code == 0
    assert "Update available" not in result.stdout
    payload = json.loads(result.stdout)
    assert payload["version"]
