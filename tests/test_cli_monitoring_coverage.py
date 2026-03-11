"""Coverage tests for src/pretorin/cli/monitoring.py.

Covers: monitoring push command.
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(*, is_configured: bool = True) -> AsyncMock:
    """Return an AsyncMock PretorianClient context manager."""
    client = AsyncMock()
    client.is_configured = is_configured
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


def _mock_scoped_client(client: AsyncMock) -> None:
    """Configure list_systems / get_system_compliance_status / get_system on client."""
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))


def _run_push(
    args: list[str],
    client: AsyncMock,
    *,
    resolved_context: tuple[str, str] = ("sys-1", "fedramp-moderate"),
) -> object:
    """Invoke `monitoring push` with a fully mocked client and context resolver."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with patch("pretorin.client.api.PretorianClient", return_value=ctx), \
         patch(
             "pretorin.cli.context.resolve_execution_context",
             new_callable=AsyncMock,
             return_value=resolved_context,
         ):
        return runner.invoke(app, args)


# ---------------------------------------------------------------------------
# monitoring push — happy path
# ---------------------------------------------------------------------------


class TestMonitoringPushHappyPath:
    """Tests for successful `pretorin monitoring push` invocations."""

    def test_push_basic_event_exits_0(self) -> None:
        """A well-formed push with valid severity exits successfully."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-abc123def456"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Nightly scan complete",
                "--severity", "high",
                "--control", "sc-07",
            ],
            client,
        )

        assert result.exit_code == 0
        client.create_monitoring_event.assert_awaited_once()

    def test_push_info_severity(self) -> None:
        """info is a valid severity value."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-info0001"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Informational event",
                "--severity", "info",
            ],
            client,
        )

        assert result.exit_code == 0

    def test_push_medium_severity_output_contains_system(self) -> None:
        """Normal-mode output mentions the system name and framework."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-med0001"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Config drift detected",
                "--severity", "medium",
                "--control", "cm-06",
            ],
            client,
        )

        assert result.exit_code == 0
        assert "Primary" in result.output

    def test_push_with_description(self) -> None:
        """--description is accepted without error."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-desc0001"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Access review",
                "--severity", "low",
                "--description", "Quarterly access review completed with no anomalies.",
            ],
            client,
        )

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# monitoring push — invalid severity
# ---------------------------------------------------------------------------


class TestMonitoringPushInvalidSeverity:
    """Tests for invalid severity values."""

    def test_push_invalid_severity_exits_1(self) -> None:
        """An unrecognised severity value causes exit code 1."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-never"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Test event",
                "--severity", "catastrophic",
            ],
            client,
        )

        assert result.exit_code == 1
        assert "Invalid severity" in result.output

    def test_push_invalid_severity_message_lists_valid_options(self) -> None:
        """The error message lists the valid severity options."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock()

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Bad severity",
                "--severity", "extreme",
            ],
            client,
        )

        assert result.exit_code == 1
        for valid in ("critical", "high", "medium", "low", "info"):
            assert valid in result.output


# ---------------------------------------------------------------------------
# monitoring push — --update-control-status flag
# ---------------------------------------------------------------------------


class TestMonitoringPushUpdateControlStatus:
    """Tests for --update-control-status flag behaviour."""

    def test_push_update_control_status_calls_update(self) -> None:
        """With --update-control-status and --control, update_control_status is called."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-upd0001"})
        client.update_control_status = AsyncMock(return_value=None)

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Patch applied",
                "--severity", "high",
                "--control", "si-02",
                "--update-control-status",
            ],
            client,
        )

        assert result.exit_code == 0
        client.update_control_status.assert_awaited_once_with(
            system_id="sys-1",
            control_id="si-02",
            status="in_progress",
            framework_id="fedramp-moderate",
        )

    def test_push_update_control_status_without_control_skips_update(self) -> None:
        """With --update-control-status but no --control, update is skipped."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-noctrl"})
        client.update_control_status = AsyncMock(return_value=None)

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "No control event",
                "--severity", "low",
                "--update-control-status",
            ],
            client,
        )

        assert result.exit_code == 0
        client.update_control_status.assert_not_awaited()

    def test_push_update_control_status_failure_warns_but_succeeds(self) -> None:
        """A failure to update control status is reported as a warning, not a hard exit."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-warnupd"})
        client.update_control_status = AsyncMock(
            side_effect=PretorianClientError("Status update failed", status_code=422)
        )

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Patch scan",
                "--severity", "critical",
                "--control", "si-02",
                "--update-control-status",
            ],
            client,
        )

        # Should not exit with failure just because the status update failed
        assert result.exit_code == 0
        assert "Warning" in result.output or "warning" in result.output.lower()


# ---------------------------------------------------------------------------
# monitoring push — JSON mode
# ---------------------------------------------------------------------------


class TestMonitoringPushJsonMode:
    """Tests for `pretorin --json monitoring push` output."""

    def test_push_json_output_structure(self) -> None:
        """JSON output contains all expected fields."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-json0001-long-id"})

        result = _run_push(
            [
                "--json",
                "monitoring", "push",
                "--title", "JSON mode test",
                "--severity", "high",
                "--control", "ac-02",
            ],
            client,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["system_id"] == "sys-1"
        assert payload["system_name"] == "Primary"
        assert payload["framework_id"] == "fedramp-moderate"
        assert payload["title"] == "JSON mode test"
        assert payload["severity"] == "high"
        assert payload["control_id"] == "ac-02"

    def test_push_json_control_status_updated_field(self) -> None:
        """control_status_updated is true when flag and control both provided."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-jsonupd0001-long"})
        client.update_control_status = AsyncMock(return_value=None)

        result = _run_push(
            [
                "--json",
                "monitoring", "push",
                "--title", "Status update event",
                "--severity", "medium",
                "--control", "cm-06",
                "--update-control-status",
            ],
            client,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["control_status_updated"] is True

    def test_push_json_control_status_updated_false_without_control(self) -> None:
        """control_status_updated is false when no control is supplied."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-noctrl-json-long"})

        result = _run_push(
            [
                "--json",
                "monitoring", "push",
                "--title", "No control JSON",
                "--severity", "info",
                "--update-control-status",
            ],
            client,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["control_status_updated"] is False


# ---------------------------------------------------------------------------
# monitoring push — error paths
# ---------------------------------------------------------------------------


class TestMonitoringPushErrors:
    """Tests for error handling in `pretorin monitoring push`."""

    def test_push_client_error_on_create_event_exits_1(self) -> None:
        """PretorianClientError from create_monitoring_event causes exit code 1."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(
            side_effect=PretorianClientError("Event store unavailable", status_code=503)
        )

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Will fail",
                "--severity", "high",
            ],
            client,
        )

        assert result.exit_code == 1
        assert "Failed to create event" in result.output

    def test_push_resolve_context_error_exits_1(self) -> None:
        """PretorianClientError from resolve_execution_context causes exit code 1."""
        client = _make_client()

        ctx = AsyncMock()
        ctx.__aenter__ = AsyncMock(return_value=client)
        ctx.__aexit__ = AsyncMock(return_value=None)

        with patch("pretorin.client.api.PretorianClient", return_value=ctx), \
             patch(
                 "pretorin.cli.context.resolve_execution_context",
                 new_callable=AsyncMock,
                 side_effect=PretorianClientError("No active system configured", status_code=400),
             ):
            result = runner.invoke(
                app,
                [
                    "monitoring", "push",
                    "--title", "Scope error event",
                    "--severity", "high",
                ],
            )

        assert result.exit_code == 1
        assert "Failed to resolve execution scope" in result.output

    def test_push_severity_case_insensitive(self) -> None:
        """Severity value is lowercased before validation so UPPER input is accepted."""
        client = _make_client()
        _mock_scoped_client(client)
        client.create_monitoring_event = AsyncMock(return_value={"id": "evt-upper-case-id"})

        result = _run_push(
            [
                "monitoring", "push",
                "--title", "Case test",
                "--severity", "HIGH",
            ],
            client,
        )

        assert result.exit_code == 0
