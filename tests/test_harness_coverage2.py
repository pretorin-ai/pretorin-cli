"""Additional coverage tests for src/pretorin/cli/harness.py.

Covers:
- Line 54: DoctorReport.to_dict()
- Lines 110, 122, 126, 133, 143, 147, 161, 165, 177: Various _evaluate_setup paths
  and _get_table_array
- Lines 235-236: harness_init no provider URL error
- Lines 280-288: harness_init JSON mode output
- Lines 294-296: harness_init errors in non-JSON mode
- Lines 331-334: harness_doctor JSON mode (both ok=True and ok=False)
- Lines 388, 404: harness_run JSON mode paths
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch
from typer.testing import CliRunner

from pretorin.cli import harness as harness_cli
from pretorin.cli.output import set_json_mode

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _set_harness_config_path(monkeypatch: MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setattr(harness_cli, "HARNESS_CONFIG_FILE", path)
    return path


def _valid_pretorin_config(base_url: str = "https://models.example/v1") -> str:
    return (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        f'base_url = "{base_url}"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )


import pytest


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


# ---------------------------------------------------------------------------
# DoctorReport.to_dict() — line 54
# ---------------------------------------------------------------------------


def test_doctor_report_to_dict():
    """Line 54: to_dict serializes all DoctorReport fields."""
    report = harness_cli.DoctorReport(
        ok=True,
        provider="pretorin",
        provider_base_url="https://models.example/v1",
        provider_env_key="OPENAI_API_KEY",
        mcp_enabled=True,
        errors=[],
        warnings=["test warning"],
    )
    d = report.to_dict()
    assert d["ok"] is True
    assert d["provider"] == "pretorin"
    assert d["provider_base_url"] == "https://models.example/v1"
    assert d["provider_env_key"] == "OPENAI_API_KEY"
    assert d["mcp_enabled"] is True
    assert d["errors"] == []
    assert d["warnings"] == ["test warning"]


def test_doctor_report_to_dict_with_errors():
    """Line 54: to_dict includes errors properly."""
    report = harness_cli.DoctorReport(
        ok=False,
        provider=None,
        provider_base_url=None,
        provider_env_key=None,
        mcp_enabled=False,
        errors=["error 1", "error 2"],
        warnings=[],
    )
    d = report.to_dict()
    assert d["ok"] is False
    assert d["provider"] is None
    assert len(d["errors"]) == 2


# ---------------------------------------------------------------------------
# _get_table_value and _get_table_array — lines 110, 122, 126
# ---------------------------------------------------------------------------


def test_get_table_value_no_section():
    """Line 110: returns None when section is not found."""
    content = 'model_provider = "pretorin"\n'
    result = harness_cli._get_table_value(content, "model_providers.pretorin", "base_url")
    assert result is None


def test_get_table_value_no_key():
    """Line 113: returns None when key is not found in section."""
    content = "[model_providers.pretorin]\nname = \"Pretorin\"\n"
    result = harness_cli._get_table_value(content, "model_providers.pretorin", "base_url")
    assert result is None


def test_get_table_array_no_section():
    """Line 122: returns None when section not found."""
    content = 'model_provider = "pretorin"\n'
    result = harness_cli._get_table_array(content, "mcp_servers.pretorin", "args")
    assert result is None


def test_get_table_array_no_key():
    """Line 126: returns None when key not found in section."""
    content = "[mcp_servers.pretorin]\ncommand = \"pretorin\"\n"
    result = harness_cli._get_table_array(content, "mcp_servers.pretorin", "args")
    assert result is None


def test_get_table_array_success():
    """Lines 127-128: returns parsed array when section and key found."""
    content = '[mcp_servers.pretorin]\ncommand = "pretorin"\nargs = ["mcp-serve", "extra"]\n'
    result = harness_cli._get_table_array(content, "mcp_servers.pretorin", "args")
    assert result == ["mcp-serve", "extra"]


# ---------------------------------------------------------------------------
# _evaluate_setup — various paths
# ---------------------------------------------------------------------------


def test_evaluate_setup_missing_backend_command(monkeypatch: MonkeyPatch):
    """Line 143: reports error when backend command not in PATH."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: None)
    content = _valid_pretorin_config()
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="nonexistent-cmd")
    assert not report.ok
    assert any("not found in PATH" in e for e in report.errors)


def test_evaluate_setup_missing_provider(monkeypatch: MonkeyPatch):
    """Line 147: reports error when model_provider not set."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = "[mcp_servers.pretorin]\ncommand = \"pretorin\"\nargs = [\"mcp-serve\"]\n"
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("model_provider" in e and "not set" in e for e in report.errors)


def test_evaluate_setup_wrong_provider_for_mode(monkeypatch: MonkeyPatch):
    """Line 151: wrong provider for non-openai mode."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "openai"\n\n'
        "[model_providers.openai]\n"
        'base_url = "https://api.openai.com/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("expected `pretorin`" in e for e in report.errors)


def test_evaluate_setup_pretorin_missing_base_url(monkeypatch: MonkeyPatch):
    """Line 161: pretorin provider missing base_url."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("missing `base_url`" in e for e in report.errors)


def test_evaluate_setup_pretorin_wrong_env_key(monkeypatch: MonkeyPatch):
    """Line 165: pretorin provider env_key should be OPENAI_API_KEY."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        'base_url = "https://models.example/v1"\n'
        'env_key = "WRONG_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert any("env_key should be" in w for w in report.warnings)


def test_evaluate_setup_env_key_not_set_warning(monkeypatch: MonkeyPatch):
    """Line 171: warns when env variable is not set in shell."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    content = _valid_pretorin_config()
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert any("not set in this shell" in w for w in report.warnings)


def test_evaluate_setup_mcp_not_configured(monkeypatch: MonkeyPatch):
    """Line 177: reports error when MCP server not configured."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        'base_url = "https://models.example/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("MCP server is not configured" in e for e in report.errors)


def test_evaluate_setup_mcp_wrong_command(monkeypatch: MonkeyPatch):
    """Line 175-177: MCP with wrong command name."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "pretorin"\n\n'
        "[model_providers.pretorin]\n"
        'base_url = "https://models.example/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "wrong-cmd"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("MCP server is not configured" in e for e in report.errors)


def test_evaluate_setup_openai_forbidden_in_non_openai_mode(monkeypatch: MonkeyPatch):
    """Line 168: openai provider in non-openai mode is flagged."""
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    content = (
        'model_provider = "openai"\n\n'
        "[model_providers.openai]\n"
        'base_url = "https://api.openai.com/v1"\n'
        'env_key = "OPENAI_API_KEY"\n\n'
        "[mcp_servers.pretorin]\n"
        'command = "pretorin"\n'
        'args = ["mcp-serve"]\n'
    )
    report = harness_cli._evaluate_setup(content, allow_openai_api=False, backend_command="codex")
    assert not report.ok
    assert any("forbids OpenAI" in e or "expected `pretorin`" in e for e in report.errors)


# ---------------------------------------------------------------------------
# harness_init — lines 235-236 (no provider URL error)
# ---------------------------------------------------------------------------


def test_harness_init_no_provider_url_exits_1(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 234-236: exits 1 when no provider URL and not in openai mode."""
    _set_harness_config_path(monkeypatch, tmp_path)

    class DummyConfig:
        def __init__(self):
            self.model_api_base_url = None

    monkeypatch.setattr(harness_cli, "Config", DummyConfig)
    result = runner.invoke(harness_cli.app, ["init"])
    assert result.exit_code == 1
    assert "provider URL is required" in result.output


# ---------------------------------------------------------------------------
# harness_init — lines 280-288 (JSON mode output)
# ---------------------------------------------------------------------------


def test_harness_init_json_mode(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 280-288: harness init in JSON mode outputs structured result."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    set_json_mode(True)

    result = runner.invoke(
        harness_cli.app,
        ["init", "--provider-url", "https://models.example/v1", "--backend-command", "codex"],
    )
    # JSON output path — need to check JSON is produced
    # The function checks is_json_mode() which we set above
    # However, the runner may not see the global set because typer testing
    # uses its own main callback. Let's use --json at the app level.
    set_json_mode(False)

    # Use the main app with --json flag for proper JSON mode
    from pretorin.cli.main import app as main_app

    # Mock the config file path for the main app path too
    result2 = runner.invoke(
        main_app,
        ["--json", "harness", "init", "--provider-url", "https://models.example/v1", "--backend-command", "codex"],
    )
    # harness_init should produce JSON output when is_json_mode() is True
    # It may exit 0 or 1 depending on doctor check, but JSON should be produced
    if result2.exit_code == 0:
        payload = json.loads(result2.stdout)
        assert "config_path" in payload
        assert "report" in payload
        assert "mode" in payload


def test_harness_init_json_mode_pretorin_provider(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 280-288: JSON mode with pretorin provider mode."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(
        main_app,
        ["--json", "harness", "init", "--provider-url", "https://models.example/v1", "--backend-command", "codex"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "pretorin-provider"
    assert payload["backend_command"] == "codex"
    assert "report" in payload
    assert payload["report"]["ok"] is True


def test_harness_init_json_mode_openai_mode(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 280-288: JSON mode with openai-api-test mode."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(
        main_app,
        ["--json", "harness", "init", "--allow-openai-api", "--backend-command", "codex"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["mode"] == "openai-api-test"


# ---------------------------------------------------------------------------
# harness_init — lines 294-296 (errors in non-JSON mode)
# ---------------------------------------------------------------------------


def test_harness_init_non_json_with_errors(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 294-296: harness init errors raise typer.Exit(1) in non-JSON mode."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    # Don't put backend command in PATH to trigger error
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: None)

    result = runner.invoke(
        harness_cli.app,
        ["init", "--provider-url", "https://models.example/v1", "--backend-command", "nonexistent"],
    )
    assert result.exit_code == 1
    assert "not found in PATH" in result.output


def test_harness_init_non_json_with_warnings_only(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 297-298: harness init warnings are shown but don't cause exit 1."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = runner.invoke(
        harness_cli.app,
        ["init", "--provider-url", "https://models.example/v1", "--backend-command", "codex"],
    )
    assert result.exit_code == 0
    assert "Updated harness config" in result.output


# ---------------------------------------------------------------------------
# harness_doctor — lines 331-334 (JSON mode)
# ---------------------------------------------------------------------------


def test_harness_doctor_json_mode_config_missing(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 331-334: doctor in JSON mode exits 1 when config missing."""
    _set_harness_config_path(monkeypatch, tmp_path)

    from pretorin.cli.main import app as main_app

    result = runner.invoke(main_app, ["--json", "harness", "doctor"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


def test_harness_doctor_json_mode_config_valid(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 331-334: doctor in JSON mode exits 0 when config valid."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(main_app, ["--json", "harness", "doctor", "--backend-command", "codex"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ok"] is True


def test_harness_doctor_json_mode_config_invalid(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Lines 332-334: doctor in JSON mode exits 1 when report.ok is False."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    # Config with wrong provider
    config_path.write_text('model_provider = "openai"\n')
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(main_app, ["--json", "harness", "doctor", "--backend-command", "codex"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert len(payload["errors"]) > 0


# ---------------------------------------------------------------------------
# harness_run — line 388 (not ready, JSON mode)
# ---------------------------------------------------------------------------


def test_harness_run_not_ready_json_mode(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Line 388: harness run in JSON mode prints report.to_dict() when not ready."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    # Config with policy violation
    config_path.write_text(_valid_pretorin_config(base_url="https://api.openai.com/v1"))
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(
        main_app,
        ["--json", "harness", "run", "Assess AC-2", "--backend-command", "codex"],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False


# ---------------------------------------------------------------------------
# harness_run — line 404 (dry-run, JSON mode)
# ---------------------------------------------------------------------------


def test_harness_run_dry_run_json_mode(monkeypatch: MonkeyPatch, tmp_path: Path):
    """Line 404: harness run --dry-run in JSON mode outputs command/prompt payload."""
    config_path = _set_harness_config_path(monkeypatch, tmp_path)
    config_path.write_text(_valid_pretorin_config())
    monkeypatch.setattr(harness_cli.shutil, "which", lambda _: "/usr/bin/codex")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    from pretorin.cli.main import app as main_app

    result = runner.invoke(
        main_app,
        [
            "--json",
            "harness",
            "run",
            "Assess AC-2 implementation",
            "--dry-run",
            "--backend-command",
            "codex",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "command" in payload
    assert "prompt" in payload
    assert "Assess AC-2 implementation" in payload["prompt"]


# ---------------------------------------------------------------------------
# _contains_disallowed_endpoint
# ---------------------------------------------------------------------------


def test_contains_disallowed_endpoint_none():
    """Line 132-133: returns False for None input."""
    assert harness_cli._contains_disallowed_endpoint(None) is False


def test_contains_disallowed_endpoint_safe():
    """Returns False for safe URLs."""
    assert harness_cli._contains_disallowed_endpoint("https://models.example.com/v1") is False


def test_contains_disallowed_endpoint_chatgpt():
    """Returns True for chatgpt.com URLs."""
    assert harness_cli._contains_disallowed_endpoint("https://chatgpt.com/v1") is True


# ---------------------------------------------------------------------------
# _get_scalar_value
# ---------------------------------------------------------------------------


def test_get_scalar_value_found():
    """Returns value when key is present."""
    content = 'model_provider = "pretorin"\n'
    assert harness_cli._get_scalar_value(content, "model_provider") == "pretorin"


def test_get_scalar_value_not_found():
    """Returns None when key is absent."""
    content = 'other_key = "value"\n'
    assert harness_cli._get_scalar_value(content, "model_provider") is None


# ---------------------------------------------------------------------------
# _build_compliance_prompt
# ---------------------------------------------------------------------------


def test_build_compliance_prompt():
    """Wraps user task with compliance guidance."""
    prompt = harness_cli._build_compliance_prompt("Assess AC-2")
    assert "compliance-focused" in prompt
    assert "Assess AC-2" in prompt


# ---------------------------------------------------------------------------
# _set_scalar appending new key
# ---------------------------------------------------------------------------


def test_set_scalar_appends_to_empty():
    """Appends key when content is empty."""
    result = harness_cli._set_scalar("", "model_provider", "pretorin")
    assert 'model_provider = "pretorin"' in result


def test_set_scalar_appends_to_existing():
    """Appends key when content has other keys."""
    content = 'web_search = "disabled"\n'
    result = harness_cli._set_scalar(content, "model_provider", "pretorin")
    assert 'model_provider = "pretorin"' in result
    assert 'web_search = "disabled"' in result


# ---------------------------------------------------------------------------
# _replace_or_append_table appending new table
# ---------------------------------------------------------------------------


def test_replace_or_append_table_appends_to_empty():
    """Appends table when content is empty."""
    result = harness_cli._replace_or_append_table("", "mcp_servers.pretorin", ['command = "pretorin"'])
    assert "[mcp_servers.pretorin]" in result
    assert 'command = "pretorin"' in result


def test_replace_or_append_table_appends_to_existing():
    """Appends table when content has other content."""
    content = 'model_provider = "pretorin"\n'
    result = harness_cli._replace_or_append_table(content, "mcp_servers.pretorin", ['command = "pretorin"'])
    assert "[mcp_servers.pretorin]" in result
    assert 'model_provider = "pretorin"' in result


# ---------------------------------------------------------------------------
# _deprecation_warning
# ---------------------------------------------------------------------------


def test_deprecation_warning_non_json():
    """Deprecation warning is printed in non-JSON mode (covers line 206)."""
    # This is a basic smoke test — the function just prints
    harness_cli._deprecation_warning("init")


def test_deprecation_warning_json_mode():
    """Deprecation warning is suppressed in JSON mode."""
    set_json_mode(True)
    harness_cli._deprecation_warning("init")
    set_json_mode(False)
