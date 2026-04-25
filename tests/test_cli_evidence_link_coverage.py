"""Coverage tests for evidence link and push skip display in src/pretorin/cli/evidence.py.

Covers:
- Line 245: evidence push result display when items are skipped (non-JSON)
- Line 269: the evidence_link command entry point
- Lines 285-320: _link_evidence async function (the entire function)
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

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


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.client.api.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


def _make_sync_result(created=None, reused=None, skipped=None, errors=None, events=None):
    return SimpleNamespace(
        created=created or [],
        reused=reused or [],
        skipped=skipped or [],
        errors=errors or [],
        events=events or [],
    )


# ---------------------------------------------------------------------------
# evidence push — line 245 (skipped items in non-JSON output)
# ---------------------------------------------------------------------------


def test_evidence_push_skipped_items_normal_mode():
    """Line 245: skipped items display 'Skipped N already-synced item(s)' in non-JSON mode."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(
        skipped=["fedramp-moderate/ac-02/RBAC Config", "fedramp-moderate/sc-07/Firewall"],
    )

    with patch("pretorin.evidence.sync.EvidenceSync") as mock_sync_cls:
        mock_sync_cls.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 0
    assert "Skipped" in result.output
    assert "2" in result.output


def test_evidence_push_skipped_with_created_normal_mode():
    """Line 245: skipped items are shown alongside created items."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(
        created=["fedramp-moderate/ac-02/New Evidence"],
        skipped=["fedramp-moderate/sc-07/Existing Evidence"],
    )

    with patch("pretorin.evidence.sync.EvidenceSync") as mock_sync_cls:
        mock_sync_cls.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 0
    assert "Created" in result.output
    assert "Skipped" in result.output


# ---------------------------------------------------------------------------
# evidence link — line 269 (entry point) and lines 285-320 (_link_evidence)
# ---------------------------------------------------------------------------


def test_evidence_link_json_mode_success():
    """Lines 269, 285-320: evidence link in JSON mode returns structured payload."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "fedramp-moderate"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "evidence",
                "link",
                "ev-abc123",
                "ac-02",
                "--framework-id",
                "fedramp-moderate",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["system_id"] == "sys-1"
    assert payload["system_name"] == "Primary"
    assert payload["evidence_id"] == "ev-abc123"
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert payload["result"] == {"linked": True}


def test_evidence_link_normal_mode_success():
    """Lines 269, 320-330: evidence link in normal mode renders a Panel."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "fedramp-moderate"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "link",
                "ev-abc123",
                "ac-02",
                "--framework-id",
                "fedramp-moderate",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Evidence Linked" in result.output


def test_evidence_link_client_error():
    """Lines 304-306: evidence link exits 1 on PretorianClientError."""
    client = AsyncMock()
    client.is_configured = True

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            side_effect=PretorianClientError("scope resolution failed"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "link",
                "ev-abc123",
                "ac-02",
                "--framework-id",
                "fedramp-moderate",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 1
    assert "Link failed" in result.output


def test_evidence_link_link_api_error():
    """Lines 304-306: exits 1 when link_evidence_to_control raises PretorianClientError."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.link_evidence_to_control = AsyncMock(side_effect=PretorianClientError("evidence not found"))

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "fedramp-moderate"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "link",
                "ev-abc123",
                "ac-02",
                "--framework-id",
                "fedramp-moderate",
            ],
        )

    assert result.exit_code == 1
    assert "Link failed" in result.output


def test_evidence_link_without_flags_uses_context():
    """Lines 269-276: evidence link without --framework-id and --system uses stored context."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("pretorin.client.api.PretorianClient", return_value=ctx),
        patch(
            "pretorin.cli.context.resolve_execution_context",
            new_callable=AsyncMock,
            return_value=("sys-1", "fedramp-moderate"),
        ) as mock_resolve,
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "evidence",
                "link",
                "ev-abc123",
                "ac-02",
            ],
        )

    assert result.exit_code == 0, result.output
    # Verify resolve_execution_context was called with None for both optional params
    mock_resolve.assert_called_once()
    call_kwargs = mock_resolve.call_args
    assert call_kwargs.kwargs.get("system") is None
    assert call_kwargs.kwargs.get("framework") is None
