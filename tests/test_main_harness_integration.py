"""Integration tests for harness commands routed through the root CLI app."""

from __future__ import annotations

import json
from pathlib import Path

from pytest import MonkeyPatch, fixture
from typer.testing import CliRunner

from pretorin.cli import harness as harness_cli
from pretorin.cli.main import app as main_app
from pretorin.cli.output import set_json_mode

runner = CliRunner()


@fixture(autouse=True)
def reset_json_mode() -> None:
    """Ensure JSON mode does not leak between tests."""
    set_json_mode(False)
    yield
    set_json_mode(False)


def _set_harness_config_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    config_path = tmp_path / "config.toml"
    monkeypatch.setattr(harness_cli, "HARNESS_CONFIG_FILE", config_path)
    return config_path


def _valid_pretorin_config(base_url: str = "https://models.example/v1") -> str:
    return (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        f'base_url = "{base_url}"\n'
        'env_key = "PRETORIN_LLM_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )


def test_root_cli_exposes_harness_command_group() -> None:
    result = runner.invoke(main_app, ["harness", "--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "doctor" in result.stdout
    assert "run" in result.stdout


def test_root_cli_routes_harness_doctor(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    result = runner.invoke(
        main_app,
        ["harness", "doctor", "--backend-command", "agentctl"],
    )
    assert result.exit_code == 0
    assert "integration is ready" in result.stdout.lower()


def test_root_cli_routes_harness_run_dry_run(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    result = runner.invoke(
        main_app,
        [
            "harness",
            "run",
            "Assess AC-2 implementation",
            "--dry-run",
            "--backend-command",
            "agentctl",
            "--backend-exec-subcommand",
            "execute",
        ],
    )
    assert result.exit_code == 0
    assert "agentctl execute" in result.stdout
    assert "Task:" in result.stdout


def test_root_cli_json_mode_flows_into_harness(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    result = runner.invoke(
        main_app,
        ["--json", "harness", "doctor", "--backend-command", "agentctl"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["provider"] == "pretorin"
    assert payload["mcp_enabled"] is True
