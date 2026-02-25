"""Tests for harness CLI integration and command behavior."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch
from typer.testing import CliRunner

from pretorin.cli import harness as harness_cli

runner = CliRunner()


def _set_harness_config_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setattr(harness_cli, "HARNESS_CONFIG_FILE", path)
    return path


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


def test_set_scalar_replaces_existing_value() -> None:
    content = 'model_provider = "openai"\n'
    updated = harness_cli._set_scalar(content, "model_provider", "pretorin")
    assert 'model_provider = "pretorin"' in updated
    assert 'model_provider = "openai"' not in updated


def test_replace_or_append_table_replaces_existing_block() -> None:
    content = (
        "[mcp_servers.pretorin]\n"
        'command = "old"\n'
        'args = ["old"]\n'
        "\n"
        "[another.section]\n"
        'value = "x"\n'
    )
    updated = harness_cli._replace_or_append_table(
        content,
        "mcp_servers.pretorin",
        ['command = "pretorin"', 'args = ["mcp-serve"]'],
    )
    assert 'command = "pretorin"' in updated
    assert 'args = ["mcp-serve"]' in updated
    assert 'command = "old"' not in updated
    assert "[another.section]" in updated


def test_evaluate_setup_enforces_pretorin_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")
    content = (
        'model_provider = "openai"\n\n'
        "[model_providers.openai]\n"
        'base_url = "https://api.openai.com/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="harness")
    assert not report.ok
    assert any("expected `pretorin`" in error for error in report.errors)


def test_evaluate_setup_accepts_openai_in_test_mode(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")
    content = (
        'model_provider = "openai"\n\n'
        "[model_providers.openai]\n"
        'base_url = "https://api.openai.com/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=True, backend_command="harness")
    assert report.ok


def test_evaluate_setup_rejects_openai_endpoint_for_pretorin(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")
    content = (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        'base_url = "https://api.openai.com/v1"\n'
        'env_key = "PRETORIN_LLM_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="harness")
    assert not report.ok
    assert any("OpenAI/ChatGPT endpoint" in error for error in report.errors)


def test_harness_init_writes_pretorin_provider_config(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")

    result = runner.invoke(
        harness_cli.app,
        ["init", "--provider-url", "https://pretorin-models.example/v1", "--backend-command", "harness"],
    )
    assert result.exit_code == 0
    content = config_path.read_text()
    assert 'model_provider = "pretorin"' in content
    assert 'base_url = "https://pretorin-models.example/v1"' in content
    assert "[mcp_servers.pretorin]" in content
    assert 'args = ["mcp-serve"]' in content


def test_harness_init_uses_config_default_model_url(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    class DummyConfig:
        def __init__(self) -> None:
            self.model_api_base_url = "https://from-config.example/v1"

    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli, "Config", DummyConfig)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")

    result = runner.invoke(
        harness_cli.app,
        ["init", "--backend-command", "harness"],
    )
    assert result.exit_code == 0
    content = config_path.read_text()
    assert 'base_url = "https://from-config.example/v1"' in content


def test_harness_init_openai_mode_writes_openai_provider(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")

    result = runner.invoke(
        harness_cli.app,
        ["init", "--allow-openai-api", "--backend-command", "harness"],
    )
    assert result.exit_code == 0
    content = config_path.read_text()
    assert 'model_provider = "openai"' in content
    assert 'base_url = "https://api.openai.com/v1"' in content


def test_harness_doctor_fails_when_config_missing(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _set_harness_config_path(monkeypatch, tmp_path)

    result = runner.invoke(harness_cli.app, ["doctor"])
    assert result.exit_code == 1
    assert "config not found" in result.stdout.lower()


def test_harness_doctor_succeeds_when_config_valid(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/harness")

    result = runner.invoke(
        harness_cli.app,
        ["doctor", "--backend-command", "harness"],
    )
    assert result.exit_code == 0
    assert "integration is ready" in result.stdout.lower()


def test_harness_run_dry_run_prints_command_and_prompt(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    result = runner.invoke(
        harness_cli.app,
        [
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
    assert "Assess AC-2 implementation" in result.stdout


def test_harness_run_executes_backend_command(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    captured: dict[str, Any] = {}

    def fake_run(cmd: list[str], check: bool = False) -> SimpleNamespace:
        captured["cmd"] = cmd
        captured["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(harness_cli.subprocess, "run", fake_run)

    result = runner.invoke(
        harness_cli.app,
        [
            "run",
            "Assess AC-2 implementation",
            "--backend-command",
            "agentctl",
            "--backend-exec-subcommand",
            "exec",
        ],
    )
    assert result.exit_code == 0
    assert captured["cmd"][0] == "agentctl"
    assert captured["cmd"][1] == "exec"
    assert isinstance(captured["cmd"][2], str)
    assert captured["check"] is False


def test_harness_run_returns_backend_exit_code(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")
    monkeypatch.setattr(
        harness_cli.subprocess,
        "run",
        lambda cmd, check=False: SimpleNamespace(returncode=7),  # noqa: ARG005
    )

    result = runner.invoke(
        harness_cli.app,
        ["run", "Assess AC-2 implementation", "--backend-command", "agentctl"],
    )
    assert result.exit_code == 7


def test_harness_run_blocks_policy_violations(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config(base_url="https://api.openai.com/v1"))
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/agentctl")

    called: list[bool] = []

    def fake_run(cmd: list[str], check: bool = False) -> SimpleNamespace:
        called.append(True)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(harness_cli.subprocess, "run", fake_run)

    result = runner.invoke(
        harness_cli.app,
        ["run", "Assess AC-2 implementation", "--backend-command", "agentctl"],
    )
    assert result.exit_code == 1
    assert called == []
    assert "OpenAI/ChatGPT endpoint" in result.stdout
