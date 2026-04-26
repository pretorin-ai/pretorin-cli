"""Coverage tests for src/pretorin/cli/cci.py.

Targets all three CCI commands: list, show, chain — in both normal and JSON
modes plus error handling.
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


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.client.api.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


def _base_client() -> AsyncMock:
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    return client


# =============================================================================
# cci list
# =============================================================================


def test_cci_list_normal_with_items() -> None:
    """cci list renders a table when CCIs are present."""
    client = _base_client()
    client.list_ccis = AsyncMock(
        return_value={
            "total": 2,
            "items": [
                {
                    "cci_id": "CCI-000015",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "The organization manages accounts.",
                },
                {
                    "cci_id": "CCI-000016",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "The organization assigns account managers.",
                },
            ],
        }
    )

    result = _run_with_mock_client(["cci", "list", "--control", "ac-2"], client)

    assert result.exit_code == 0, result.output
    assert "CCI-000015" in result.output
    assert "CCI-000016" in result.output


def test_cci_list_empty() -> None:
    """cci list shows empty message when no CCIs found."""
    client = _base_client()
    client.list_ccis = AsyncMock(return_value={"total": 0, "items": []})

    result = _run_with_mock_client(["cci", "list"], client)

    assert result.exit_code == 0
    assert "No CCI entries" in result.output


def test_cci_list_json_mode() -> None:
    """cci list --json emits structured JSON."""
    client = _base_client()
    data = {
        "total": 1,
        "items": [
            {
                "cci_id": "CCI-000015",
                "nist_control_id": "ac-2",
                "cci_type": "technical",
                "definition": "Test definition.",
            },
        ],
    }
    client.list_ccis = AsyncMock(return_value=data)

    result = _run_with_mock_client(["--json", "cci", "list"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["items"][0]["cci_id"] == "CCI-000015"


def test_cci_list_error() -> None:
    """cci list exits 1 on PretorianClientError."""
    client = _base_client()
    client.list_ccis = AsyncMock(side_effect=PretorianClientError("Not authorized"))

    result = _run_with_mock_client(["cci", "list"], client)

    assert result.exit_code == 1
    assert "Not authorized" in result.output


# =============================================================================
# cci show
# =============================================================================


def test_cci_show_normal_mode() -> None:
    """cci show renders CCI detail in normal mode."""
    client = _base_client()
    client.get_cci = AsyncMock(
        return_value={
            "cci_id": "CCI-000015",
            "nist_control_id": "ac-2",
            "cci_type": "technical",
            "status": "published",
            "definition": "The organization manages accounts.",
            "assessment_objective": "Determine if the org manages accounts.",
            "stig_rules": [
                {
                    "stig_id": "RHEL-08-010010",
                    "rule_id": "SV-230221r858671_rule",
                    "severity": "cat_ii",
                    "title": "RHEL 8 must employ strong authenticators.",
                },
            ],
            "srgs": [
                {"srg_id": "SRG-OS-000001-GPOS-00001", "title": "SRG title"},
            ],
        }
    )

    result = _run_with_mock_client(["cci", "show", "CCI-000015"], client)

    assert result.exit_code == 0, result.output
    assert "CCI-000015" in result.output
    assert "AC-2" in result.output
    assert "manages accounts" in result.output


def test_cci_show_normalises_id() -> None:
    """cci show normalises bare numeric CCI IDs."""
    client = _base_client()
    client.get_cci = AsyncMock(
        return_value={
            "cci_id": "CCI-000015",
            "nist_control_id": "ac-2",
            "cci_type": "technical",
            "status": "published",
            "definition": "Test.",
            "stig_rules": [],
            "srgs": [],
        }
    )

    result = _run_with_mock_client(["cci", "show", "15"], client)

    assert result.exit_code == 0
    client.get_cci.assert_awaited_once_with("CCI-000015")


def test_cci_show_json_mode() -> None:
    """cci show --json emits structured JSON."""
    client = _base_client()
    data = {
        "cci_id": "CCI-000015",
        "nist_control_id": "ac-2",
        "cci_type": "technical",
        "status": "published",
        "definition": "Test.",
        "stig_rules": [],
        "srgs": [],
    }
    client.get_cci = AsyncMock(return_value=data)

    result = _run_with_mock_client(["--json", "cci", "show", "CCI-000015"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["cci_id"] == "CCI-000015"


def test_cci_show_error() -> None:
    """cci show exits 1 on PretorianClientError."""
    client = _base_client()
    client.get_cci = AsyncMock(side_effect=PretorianClientError("Not found"))

    result = _run_with_mock_client(["cci", "show", "CCI-999999"], client)

    assert result.exit_code == 1
    assert "Not found" in result.output


def test_cci_show_no_stig_rules_no_srgs() -> None:
    """cci show renders cleanly when there are no STIG rules or SRGs."""
    client = _base_client()
    client.get_cci = AsyncMock(
        return_value={
            "cci_id": "CCI-000015",
            "nist_control_id": "ac-2",
            "cci_type": "technical",
            "status": "draft",
            "definition": "Test definition.",
            "stig_rules": [],
            "srgs": [],
        }
    )

    result = _run_with_mock_client(["cci", "show", "CCI-000015"], client)

    assert result.exit_code == 0
    assert "CCI-000015" in result.output


def test_cci_show_no_assessment_objective() -> None:
    """cci show omits assessment objective section when absent."""
    client = _base_client()
    client.get_cci = AsyncMock(
        return_value={
            "cci_id": "CCI-000015",
            "nist_control_id": "ac-2",
            "cci_type": "technical",
            "status": "published",
            "definition": "Test.",
            "assessment_objective": None,
            "stig_rules": [],
            "srgs": [],
        }
    )

    result = _run_with_mock_client(["cci", "show", "CCI-000015"], client)

    assert result.exit_code == 0
    assert "Assessment Objective" not in result.output


# =============================================================================
# cci chain
# =============================================================================


def test_cci_chain_normal_mode() -> None:
    """cci chain renders a tree view."""
    client = _base_client()
    client.list_ccis = AsyncMock(
        return_value={
            "items": [
                {
                    "cci_id": "CCI-000015",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "Manages accounts.",
                },
            ],
        }
    )

    result = _run_with_mock_client(["cci", "chain", "ac-2"], client)

    assert result.exit_code == 0, result.output
    assert "AC-2" in result.output
    assert "CCI-000015" in result.output


def test_cci_chain_empty() -> None:
    """cci chain shows empty message when no CCIs found."""
    client = _base_client()
    client.list_ccis = AsyncMock(return_value={"items": []})

    result = _run_with_mock_client(["cci", "chain", "zz-99"], client)

    assert result.exit_code == 0
    assert "No CCIs found" in result.output


def test_cci_chain_json_mode() -> None:
    """cci chain --json emits structured JSON."""
    client = _base_client()
    client.list_ccis = AsyncMock(
        return_value={
            "items": [
                {
                    "cci_id": "CCI-000015",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "Test.",
                },
            ],
        }
    )

    result = _run_with_mock_client(["--json", "cci", "chain", "ac-2"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-2"
    assert len(payload["ccis"]) == 1


def test_cci_chain_with_system_status() -> None:
    """cci chain with --system includes CCI test status."""
    client = _base_client()
    client.list_ccis = AsyncMock(
        return_value={
            "items": [
                {
                    "cci_id": "CCI-000015",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "Test.",
                },
            ],
        }
    )
    client.get_cci_status = AsyncMock(
        return_value={
            "ccis": [
                {
                    "cci_id": "CCI-000015",
                    "status": "pass",
                    "passing_rules": 3,
                    "total_rules": 3,
                    "stig_results": [
                        {"stig_id": "RHEL-08-010010", "rule_id": "SV-230221", "status": "pass"},
                    ],
                },
            ],
        }
    )

    with patch(
        "pretorin.cli.context.resolve_execution_context",
        new=AsyncMock(return_value=("sys-1", "fedramp-moderate")),
    ):
        result = _run_with_mock_client(
            ["cci", "chain", "ac-2", "--system", "Primary"], client
        )

    assert result.exit_code == 0, result.output
    assert "CCI-000015" in result.output
    assert "PASS" in result.output


def test_cci_chain_error() -> None:
    """cci chain exits 1 on PretorianClientError."""
    client = _base_client()
    client.list_ccis = AsyncMock(side_effect=PretorianClientError("Server error"))

    result = _run_with_mock_client(["cci", "chain", "ac-2"], client)

    assert result.exit_code == 1
    assert "Server error" in result.output


def test_cci_chain_system_status_error_ignored() -> None:
    """cci chain gracefully handles CCI status fetch failure."""
    client = _base_client()
    client.list_ccis = AsyncMock(
        return_value={
            "items": [
                {
                    "cci_id": "CCI-000015",
                    "nist_control_id": "ac-2",
                    "cci_type": "technical",
                    "definition": "Test.",
                },
            ],
        }
    )
    client.get_cci_status = AsyncMock(side_effect=PretorianClientError("No results"))

    result = _run_with_mock_client(
        ["cci", "chain", "ac-2", "--system", "Primary"], client
    )

    # Should still succeed — status errors are silently ignored
    assert result.exit_code == 0
    assert "CCI-000015" in result.output
