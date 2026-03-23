"""Coverage tests for src/pretorin/cli/context.py."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pretorin.cli.context import (
    _ensure_single_framework_scope,
    _resolve_context_values,
    resolve_context,
)
from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import PretorianClientError

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
# Helpers
# ---------------------------------------------------------------------------


def _run_with_mock_client(args, client):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.client.api.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


def _make_client(*, configured=True, systems=None, compliance_status=None):
    """Build a commonly-shaped async mock client."""
    client = AsyncMock()
    client.is_configured = configured
    client.list_systems = AsyncMock(return_value=systems or [])
    if compliance_status is None:
        compliance_status = {
            "frameworks": [{"framework_id": "fedramp-moderate", "progress": 42, "status": "in_progress"}]
        }
    client.get_system_compliance_status = AsyncMock(return_value=compliance_status)
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary System"))
    return client


# ---------------------------------------------------------------------------
# context list
# ---------------------------------------------------------------------------


def test_context_list_json_mode_with_systems_and_frameworks():
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 55, "status": "in_progress"}]},
    )
    result = _run_with_mock_client(["--json", "context", "list"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["system_id"] == "sys-1"
    assert payload[0]["framework_id"] == "fedramp-moderate"
    assert payload[0]["progress"] == 55


def test_context_list_system_without_frameworks_shows_placeholder_row():
    client = _make_client(
        systems=[{"id": "sys-2", "name": "Empty System"}],
        compliance_status={"frameworks": []},
    )
    result = _run_with_mock_client(["--json", "context", "list"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["framework_id"] == "-"
    assert payload[0]["status"] == "no frameworks"


def test_context_list_compliance_status_error_shows_error_row():
    client = _make_client(systems=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("server error", status_code=500)
    )
    result = _run_with_mock_client(["--json", "context", "list"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload[0]["status"] == "error fetching status"


def test_context_list_api_error_exits_one():
    client = _make_client()
    client.list_systems = AsyncMock(side_effect=PretorianClientError("connection refused"))
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# context set
# ---------------------------------------------------------------------------


def test_context_set_flags_json_mode():
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate"}]},
    )
    mock_config = MagicMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(
            ["--json", "context", "set", "--system", "Primary", "--framework", "fedramp-moderate"],
            client,
        )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["system_id"] == "sys-1"
    assert payload["framework_id"] == "fedramp-moderate"
    mock_config.set.assert_any_call("active_system_id", "sys-1")
    mock_config.set.assert_any_call("active_system_name", "Primary")


def test_context_set_invalid_system_name_exits_one():
    client = _make_client(systems=[{"id": "sys-1", "name": "Primary"}])
    result = _run_with_mock_client(
        ["context", "set", "--system", "nonexistent", "--framework", "fedramp-moderate"],
        client,
    )
    assert result.exit_code == 1
    assert "not found" in result.stdout.lower()


def test_context_set_framework_not_associated_with_system_exits_one():
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate"}]},
    )
    result = _run_with_mock_client(
        ["context", "set", "--system", "Primary", "--framework", "fedramp-high"],
        client,
    )
    assert result.exit_code == 1
    assert "not associated" in result.stdout.lower()


def test_context_set_interactive_mode_valid_selection(monkeypatch):
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 0}]},
    )
    mock_config = MagicMock()
    inputs = iter(["1", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 0
    assert "Context Set" in result.output
    mock_config.set.assert_any_call("active_system_id", "sys-1")
    mock_config.set.assert_any_call("active_system_name", "Primary")
    mock_config.set.assert_any_call("active_framework_id", "fedramp-moderate")


# ---------------------------------------------------------------------------
# context show
# ---------------------------------------------------------------------------


def test_context_show_with_context_set_json_mode():
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [
            {"framework_id": "fedramp-moderate", "progress": 80, "status": "implemented"}
        ]}
    )
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["active_system_id"] == "sys-1"
    assert payload["active_framework_id"] == "fedramp-moderate"
    assert payload["valid"] is True


def test_context_show_not_logged_in_shows_stored_context():
    client = _make_client(configured=False)
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-offline",
        "active_system_name": "Offline System",
        "active_framework_id": "fedramp-low",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["active_system_id"] == "sys-offline"
    assert payload["active_system_name"] == "Offline System"


# ---------------------------------------------------------------------------
# context clear
# ---------------------------------------------------------------------------


def test_context_clear_json_mode():
    mock_config = MagicMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = runner.invoke(app, ["--json", "context", "clear"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["cleared"] is True
    mock_config.delete.assert_any_call("active_system_id")
    mock_config.delete.assert_any_call("active_system_name")
    mock_config.delete.assert_any_call("active_framework_id")


def test_context_clear_normal_mode():
    mock_config = MagicMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = runner.invoke(app, ["context", "clear"])
    assert result.exit_code == 0
    assert "cleared" in result.stdout.lower()


# ---------------------------------------------------------------------------
# _resolve_context_values
# ---------------------------------------------------------------------------


def test_resolve_context_values_flags_take_precedence():
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "config-sys",
        "active_framework_id": "config-fw",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        system_id, framework_id = _resolve_context_values(system="flag-sys", framework="flag-fw")
    assert system_id == "flag-sys"
    assert framework_id == "flag-fw"


def test_resolve_context_values_falls_back_to_stored_config():
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "stored-sys",
        "active_framework_id": "stored-fw",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        system_id, framework_id = _resolve_context_values()
    assert system_id == "stored-sys"
    assert framework_id == "stored-fw"


# ---------------------------------------------------------------------------
# _ensure_single_framework_scope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_input", [
    "fedramp-low and fedramp-moderate",
    "fw1,fw2",
    "fw1/fw2",
    "fw1\\fw2",
    "fw1 & fw2",
])
def test_ensure_single_framework_scope_rejects_multi_framework(bad_input):
    with pytest.raises(ValueError, match="exactly one framework"):
        _ensure_single_framework_scope(bad_input)


def test_ensure_single_framework_scope_accepts_valid_id():
    assert _ensure_single_framework_scope("fedramp-moderate") == "fedramp-moderate"


# ---------------------------------------------------------------------------
# resolve_context
# ---------------------------------------------------------------------------


def test_resolve_context_succeeds_when_both_values_present():
    mock_config = MagicMock()
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        system_id, framework_id = resolve_context()
    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"


def test_resolve_context_raises_exit_when_system_missing():
    mock_config = MagicMock()
    mock_config.get.return_value = None
    with patch("pretorin.client.config.Config", return_value=mock_config):
        with pytest.raises(typer.Exit):
            resolve_context()


def test_resolve_context_explicit_flags_bypass_config():
    mock_config = MagicMock()
    mock_config.get.return_value = None
    with patch("pretorin.client.config.Config", return_value=mock_config):
        system_id, framework_id = resolve_context(system="direct-sys", framework="direct-fw")
    assert system_id == "direct-sys"
    assert framework_id == "direct-fw"
