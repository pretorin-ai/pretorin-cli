"""Coverage tests for src/pretorin/cli/control.py.

Targets: control status (invalid status, happy path normal + JSON, client error),
control context (happy path normal + JSON, client error).
"""

from __future__ import annotations

import json
from types import SimpleNamespace
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


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    """Invoke the CLI with a mocked PretorianClient and resolve_execution_context."""
    ctx_mgr = AsyncMock()
    ctx_mgr.__aenter__ = AsyncMock(return_value=client)
    ctx_mgr.__aexit__ = AsyncMock(return_value=None)
    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx_mgr),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "nist-800-53-r5"),
        ),
    ):
        return runner.invoke(app, args)


def _base_client() -> AsyncMock:
    """Return a fully wired mock client for control commands."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    return client


# =============================================================================
# control status -- invalid status
# =============================================================================


def test_control_status_invalid_status() -> None:
    """control status rejects an invalid status value and exits 1."""
    result = runner.invoke(app, ["control", "status", "ac-02", "bogus"])

    assert result.exit_code == 1
    assert "Invalid status" in result.output
    assert "bogus" in result.output


# =============================================================================
# control status -- happy path (normal mode)
# =============================================================================


def test_control_status_normal_mode() -> None:
    """control status updates and shows a rich panel in normal mode."""
    client = _base_client()
    client.update_control_status = AsyncMock(return_value={"updated": True})

    result = _run_with_mock_client(
        ["control", "status", "ac-02", "implemented", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "AC-02" in result.output
    assert "implemented" in result.output
    assert "Primary" in result.output
    client.update_control_status.assert_awaited_once()


# =============================================================================
# control status -- happy path (JSON mode)
# =============================================================================


def test_control_status_json_mode() -> None:
    """control status --json emits structured JSON output."""
    client = _base_client()
    client.update_control_status = AsyncMock(return_value={"updated": True})

    result = _run_with_mock_client(
        [
            "--json",
            "control",
            "status",
            "ac-02",
            "partially_implemented",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["system_id"] == "sys-1"
    assert payload["system_name"] == "Primary"
    assert payload["control_id"] == "ac-02"
    assert payload["status"] == "partially_implemented"
    assert payload["result"] == {"updated": True}


# =============================================================================
# control status -- PretorianClientError
# =============================================================================


def test_control_status_client_error() -> None:
    """control status exits 1 on PretorianClientError."""
    client = _base_client()
    client.update_control_status = AsyncMock(side_effect=PretorianClientError("Control not found"))

    result = _run_with_mock_client(
        ["control", "status", "ac-02", "planned", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1
    assert "Status update failed" in result.output
    assert "Control not found" in result.output


# =============================================================================
# control context -- happy path (normal mode, all fields populated)
# =============================================================================


def _mock_control_context() -> MagicMock:
    """Build a MagicMock that behaves like a ControlContext model."""
    ctx = MagicMock()
    ctx.control_id = "ac-02"
    ctx.title = "Account Management"
    ctx.status = "partially_implemented"
    ctx.statement = "The organization manages information system accounts."
    ctx.objectives = ["Objective A", "Objective B"]
    ctx.guidance = "Follow NIST SP 800-53 guidance for account management."
    ctx.ai_guidance = {"recommendation": "Automate account provisioning", "risk": "Medium"}
    ctx.implementation_narrative = "RBAC is enforced through the identity provider."
    ctx.model_dump.return_value = {
        "control_id": "ac-02",
        "title": "Account Management",
        "status": "partially_implemented",
        "statement": "The organization manages information system accounts.",
        "objectives": ["Objective A", "Objective B"],
        "guidance": "Follow NIST SP 800-53 guidance for account management.",
        "ai_guidance": {"recommendation": "Automate account provisioning", "risk": "Medium"},
        "implementation_narrative": "RBAC is enforced through the identity provider.",
    }
    return ctx


def test_control_context_normal_mode() -> None:
    """control context renders all fields in normal mode."""
    client = _base_client()
    client.get_control_context = AsyncMock(return_value=_mock_control_context())

    result = _run_with_mock_client(
        ["control", "context", "ac-02", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "Primary" in result.output
    assert "AC-02" in result.output
    assert "Account Management" in result.output
    assert "partially_implemented" in result.output
    assert "manages information system accounts" in result.output
    assert "Objective A" in result.output
    assert "Objective B" in result.output
    assert "NIST SP 800-53" in result.output
    assert "Automate account provisioning" in result.output
    assert "RBAC" in result.output
    client.get_control_context.assert_awaited_once()


# =============================================================================
# control context -- happy path (JSON mode)
# =============================================================================


def test_control_context_json_mode() -> None:
    """control context --json emits structured JSON with context fields."""
    client = _base_client()
    client.get_control_context = AsyncMock(return_value=_mock_control_context())

    result = _run_with_mock_client(
        ["--json", "control", "context", "ac-02", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["system_id"] == "sys-1"
    assert payload["system_name"] == "Primary"
    assert payload["framework_id"] == "nist-800-53-r5"
    assert payload["control_id"] == "ac-02"
    assert payload["title"] == "Account Management"
    assert payload["status"] == "partially_implemented"


# =============================================================================
# control context -- PretorianClientError
# =============================================================================


def test_control_context_client_error() -> None:
    """control context exits 1 on PretorianClientError."""
    client = _base_client()
    client.get_control_context = AsyncMock(side_effect=PretorianClientError("Not authorized"))

    result = _run_with_mock_client(
        ["control", "context", "ac-02", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1
    assert "Context fetch failed" in result.output
    assert "Not authorized" in result.output
