"""Additional coverage tests for src/pretorin/cli/context.py.

Covers the remaining uncovered lines:
- Line 47: _ensure_single_framework_scope returning empty candidate
- Line 67: resolve_execution_context raising PretorianClientError for missing context
- Lines 139-140: _context_list when no systems found
- Lines 187-218: _context_list rich table output (non-JSON path)
- Lines 260-262: _context_set PretorianClientError when listing systems
- Lines 264-266: _context_set when no systems found
- Lines 292, 294-296: _context_set interactive system selection invalid choice
- Lines 309-310: _context_set framework validation failure (compliance status error)
- Lines 323-329: _context_set interactive framework selection when no frameworks
- Lines 342-346: _context_set interactive framework selection invalid choice
- Lines 390-395: _context_show when no context set (both JSON and non-JSON)
- Lines 403, 423-424, 433-434, 447-448: _context_show various display paths
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pretorin.cli.context import (
    _ensure_single_framework_scope,
    resolve_execution_context,
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
# _ensure_single_framework_scope — line 47 (empty candidate)
# ---------------------------------------------------------------------------


def test_ensure_single_framework_scope_returns_empty_for_blank_input():
    """Line 47: returns empty string without raising when input is blank."""
    result = _ensure_single_framework_scope("")
    assert result == ""


def test_ensure_single_framework_scope_returns_empty_for_whitespace_only():
    """Line 47: whitespace-only input strips to empty and returns it."""
    result = _ensure_single_framework_scope("   ")
    assert result == ""


# ---------------------------------------------------------------------------
# resolve_execution_context — line 67 (missing context error)
# ---------------------------------------------------------------------------


async def test_resolve_execution_context_raises_when_no_system():
    """Line 67: raises PretorianClientError when system_value is missing."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.return_value = None
    client = AsyncMock()

    with patch("pretorin.client.config.Config", return_value=mock_config):
        with pytest.raises(PretorianClientError, match="No system/framework context set"):
            await resolve_execution_context(client)


async def test_resolve_execution_context_raises_when_no_framework():
    """Line 67: raises PretorianClientError when framework_value is missing."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": None,
    }.get(key)
    client = AsyncMock()

    with patch("pretorin.client.config.Config", return_value=mock_config):
        with pytest.raises(PretorianClientError, match="No system/framework context set"):
            await resolve_execution_context(client)


async def test_resolve_execution_context_rejects_multi_framework():
    """Lines 72-74: raises PretorianClientError when framework contains separators."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fw1,fw2",
    }.get(key)
    client = AsyncMock()

    with patch("pretorin.client.config.Config", return_value=mock_config):
        with pytest.raises(PretorianClientError, match="exactly one framework"):
            await resolve_execution_context(client)


async def test_resolve_execution_context_no_frameworks_on_system():
    """Lines 78-81: raises PretorianClientError when system has no frameworks."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": []})

    with patch("pretorin.client.config.Config", return_value=mock_config), \
         patch("pretorin.workflows.compliance_updates.resolve_system", new_callable=AsyncMock, return_value=("sys-1", "Primary")):
        with pytest.raises(PretorianClientError, match="no configured frameworks"):
            await resolve_execution_context(client, system="sys-1", framework="fedramp-moderate")


async def test_resolve_execution_context_framework_not_available():
    """Lines 82-86: raises PretorianClientError when requested framework not on system."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-high",
    }.get(key)
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )

    with patch("pretorin.client.config.Config", return_value=mock_config), \
         patch("pretorin.workflows.compliance_updates.resolve_system", new_callable=AsyncMock, return_value=("sys-1", "Primary")):
        with pytest.raises(PretorianClientError, match="not associated with system"):
            await resolve_execution_context(client, system="sys-1", framework="fedramp-high")


async def test_resolve_execution_context_success():
    """Lines 75-87: successful resolution returns (system_id, framework_id)."""
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )

    with patch("pretorin.client.config.Config", return_value=mock_config), \
         patch("pretorin.workflows.compliance_updates.resolve_system", new_callable=AsyncMock, return_value=("sys-1", "Primary")):
        system_id, framework_id = await resolve_execution_context(
            client, system="sys-1", framework="fedramp-moderate"
        )
    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"


# ---------------------------------------------------------------------------
# _context_list — lines 139-140 (no systems found)
# ---------------------------------------------------------------------------


def test_context_list_no_systems_found():
    """Lines 139-140: prints sad message and exits 0 when no systems."""
    client = _make_client(systems=[])
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 0
    assert "No systems found" in result.output


# ---------------------------------------------------------------------------
# _context_list — lines 187-218 (rich table output, non-JSON)
# ---------------------------------------------------------------------------


def test_context_list_rich_table_output():
    """Lines 187-218: renders rich table with systems/frameworks in non-JSON mode."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={
            "frameworks": [
                {"framework_id": "fedramp-moderate", "progress": 55, "status": "in_progress"},
            ]
        },
    )
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 0
    # Rich table title
    assert "Systems" in result.output or "Compliance" in result.output


def test_context_list_rich_table_multiple_statuses():
    """Lines 197-214: exercises multiple status_colors keys."""
    systems = [
        {"id": "sys-1", "name": "System A"},
        {"id": "sys-2", "name": "System B"},
        {"id": "sys-3", "name": "System C"},
    ]
    status_responses = {
        "sys-1": {"frameworks": [{"framework_id": "fw-1", "progress": 0, "status": "not_started"}]},
        "sys-2": {"frameworks": [{"framework_id": "fw-2", "progress": 100, "status": "complete"}]},
        "sys-3": {"frameworks": []},  # "no frameworks" row
    }
    client = _make_client(systems=systems)
    client.get_system_compliance_status = AsyncMock(
        side_effect=lambda sid: status_responses[sid]
    )
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 0
    # Should show table output with multiple rows
    assert "System A" in result.output or "fw-1" in result.output


def test_context_list_rich_table_with_error_status():
    """Lines 171-180, 203, 208: exercises the error status color path."""
    client = _make_client(systems=[{"id": "sys-err", "name": "Error System"}])
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("server error", status_code=500)
    )
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 0
    assert "Error System" in result.output


def test_context_list_rich_table_progress_dash_for_no_framework():
    """Line 207: progress shows '-' when framework_id is '-'."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "NoFW System"}],
        compliance_status={"frameworks": []},
    )
    result = _run_with_mock_client(["context", "list"], client)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _context_set — lines 260-262 (PretorianClientError listing systems)
# ---------------------------------------------------------------------------


def test_context_set_list_systems_error():
    """Lines 260-262: exits 1 when list_systems raises PretorianClientError."""
    client = _make_client()
    client.list_systems = AsyncMock(side_effect=PretorianClientError("connection refused"))
    result = _run_with_mock_client(
        ["context", "set", "--system", "Primary", "--framework", "fedramp-moderate"],
        client,
    )
    assert result.exit_code == 1
    assert "Failed to list systems" in result.output


# ---------------------------------------------------------------------------
# _context_set — lines 264-266 (no systems found)
# ---------------------------------------------------------------------------


def test_context_set_no_systems_found():
    """Lines 264-266: exits 1 when no systems exist."""
    client = _make_client(systems=[])
    result = _run_with_mock_client(
        ["context", "set", "--system", "Primary", "--framework", "fedramp-moderate"],
        client,
    )
    assert result.exit_code == 1
    assert "No systems found" in result.output


# ---------------------------------------------------------------------------
# _context_set — lines 292, 294-296 (interactive system selection invalid)
# ---------------------------------------------------------------------------


def test_context_set_interactive_invalid_system_choice(monkeypatch):
    """Lines 292, 294-296: exits 1 when interactive system selection is invalid (out of range)."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
    )
    # Select system "99" which is out of range, then should exit
    monkeypatch.setattr("builtins.input", lambda _prompt: "99")
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


def test_context_set_interactive_non_numeric_system_choice(monkeypatch):
    """Lines 294-296: exits 1 when interactive system choice is not a number."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "abc")
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


def test_context_set_interactive_zero_system_choice(monkeypatch):
    """Line 292: exits 1 when interactive system choice is 0 (idx < 0)."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "0")
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


# ---------------------------------------------------------------------------
# _context_set — lines 309-310 (framework validation with compliance error)
# ---------------------------------------------------------------------------


def test_context_set_framework_validation_compliance_error():
    """Lines 309-310: when compliance status raises, fw_ids is empty, so framework passes through."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
    )
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("compliance API error")
    )
    mock_config = MagicMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(
            ["context", "set", "--system", "Primary", "--framework", "fedramp-moderate"],
            client,
        )
    # Since fw_ids is empty, the framework still passes validation (fw_ids is falsy)
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# _context_set — lines 323-329 (interactive, no frameworks)
# ---------------------------------------------------------------------------


def test_context_set_interactive_no_frameworks(monkeypatch):
    """Lines 323-329: exits 1 when interactive framework selection has no frameworks."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": []},
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "1")
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "No frameworks" in result.output


def test_context_set_interactive_no_frameworks_compliance_error(monkeypatch):
    """Lines 323-324: exits 1 when compliance status errors and fw_list is empty."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
    )
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("compliance error")
    )
    monkeypatch.setattr("builtins.input", lambda _prompt: "1")
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "No frameworks" in result.output


# ---------------------------------------------------------------------------
# _context_set — lines 342-346 (interactive framework selection invalid)
# ---------------------------------------------------------------------------


def test_context_set_interactive_invalid_framework_choice(monkeypatch):
    """Lines 342, 344-346: exits 1 when interactive framework choice is out of range."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 0}]},
    )
    inputs = iter(["1", "99"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


def test_context_set_interactive_non_numeric_framework_choice(monkeypatch):
    """Lines 344-346: exits 1 when interactive framework choice is not a number."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 0}]},
    )
    inputs = iter(["1", "xyz"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


def test_context_set_interactive_zero_framework_choice(monkeypatch):
    """Line 342: exits 1 when framework choice is 0 (idx < 0)."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 0}]},
    )
    inputs = iter(["1", "0"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 1
    assert "Invalid selection" in result.output


# ---------------------------------------------------------------------------
# _context_set — non-JSON success with Panel output
# ---------------------------------------------------------------------------


def test_context_set_non_json_success_displays_panel(monkeypatch):
    """Lines 362-371: non-JSON success path renders a Panel."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 0}]},
    )
    inputs = iter(["1", "1"])
    monkeypatch.setattr("builtins.input", lambda _prompt: next(inputs))
    mock_config = MagicMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "set"], client)
    assert result.exit_code == 0
    assert "Context Set" in result.output


# ---------------------------------------------------------------------------
# _context_show — lines 390-395 (no context set)
# ---------------------------------------------------------------------------


def test_context_show_no_context_json_mode():
    """Lines 390-391: JSON mode outputs null values when no context set."""
    client = _make_client()
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.return_value = None
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["active_system_id"] is None
    assert payload["active_framework_id"] is None
    assert payload["valid"] is False


def test_context_show_no_context_normal_mode():
    """Lines 392-395: non-JSON mode prints sad message when no context."""
    client = _make_client()
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.return_value = None
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show"], client)
    assert result.exit_code == 0
    assert "No active context" in result.output


# ---------------------------------------------------------------------------
# _context_show — line 403 (not configured, non-JSON Panel)
# ---------------------------------------------------------------------------


def test_context_show_not_configured_non_json():
    """Line 403: renders a Panel with stored context when not logged in (non-JSON)."""
    client = _make_client(configured=False)
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-offline",
        "active_system_name": "Offline System",
        "active_framework_id": "fedramp-low",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show"], client)
    assert result.exit_code == 0
    assert "Active Context" in result.output
    assert "Offline System (sys-offline)" in result.output
    assert "stored context only" in result.output


# ---------------------------------------------------------------------------
# _context_show — stale or unverified context paths
# ---------------------------------------------------------------------------


def test_context_show_marks_missing_system_as_invalid():
    """Stored context should be marked invalid when the system no longer exists."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [
            {"framework_id": "fedramp-moderate", "progress": 80, "status": "implemented"}
        ]}
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-unknown-id",
        "active_system_name": "Retired System",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["active_system_name"] == "Retired System"
    assert payload["valid"] is False
    assert payload["validation_state"] == "invalid"
    assert "no longer exists" in payload["validation_error"]


# ---------------------------------------------------------------------------
# _context_show — compliance status PretorianClientError
# ---------------------------------------------------------------------------


def test_context_show_compliance_status_error_keeps_defaults():
    """Progress defaults remain and validation becomes unverified when compliance lookup fails."""
    client = _make_client(systems=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("compliance error")
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["progress"] == 0
    assert payload["status"] == "unknown"
    assert payload["valid"] is None
    assert payload["validation_state"] == "unverified"
    assert "Could not validate framework membership" in payload["validation_error"]


def test_context_show_marks_missing_framework_as_invalid():
    """Stored framework should be marked invalid when it no longer belongs to the system."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-low", "progress": 10, "status": "in_progress"}]},
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["--json", "context", "show"], client)
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert payload["validation_state"] == "invalid"
    assert "Available frameworks: fedramp-low" in payload["validation_error"]


# ---------------------------------------------------------------------------
# _context_show — lines 447-448 (non-JSON Panel with live data)
# ---------------------------------------------------------------------------


def test_context_show_non_json_with_live_data():
    """Lines 447-448: renders a Panel in non-JSON mode with live system data."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [
            {"framework_id": "fedramp-moderate", "progress": 80, "status": "implemented"}
        ]}
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show"], client)
    assert result.exit_code == 0
    assert "Active Context" in result.output


def test_context_show_non_json_system_error_and_compliance_error():
    """Non-JSON path surfaces framework validation problems instead of silently falling back."""
    client = _make_client(systems=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        side_effect=PretorianClientError("compliance error")
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show"], client)
    assert result.exit_code == 0
    assert "Active Context" in result.output
    assert "Could not validate framework membership" in result.output


def test_context_show_quiet_outputs_single_line():
    """Quiet mode should emit a compact one-line summary."""
    client = _make_client(
        systems=[{"id": "sys-1", "name": "Primary"}],
        compliance_status={"frameworks": [{"framework_id": "fedramp-moderate", "progress": 80, "status": "implemented"}]},
    )
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show", "--quiet"], client)
    assert result.exit_code == 0
    assert "Primary (sys-1) / fedramp-moderate [implemented, 80%]" in result.output


def test_context_show_check_exits_nonzero_for_stale_context():
    """Check mode should fail fast when stored context points at a missing system."""
    client = _make_client(systems=[{"id": "sys-1", "name": "Primary"}])
    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = None
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-missing",
        "active_system_name": "Retired System",
        "active_framework_id": "fedramp-moderate",
    }.get(key)
    with patch("pretorin.client.config.Config", return_value=mock_config):
        result = _run_with_mock_client(["context", "show", "--quiet", "--check"], client)
    assert result.exit_code == 1
    assert "Retired System (sys-missing)" in result.output
    assert "invalid" in result.output
