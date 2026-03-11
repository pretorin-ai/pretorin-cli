"""Coverage tests for src/pretorin/cli/narrative.py.

Targets: narrative get (normal mode + error), narrative push (success, empty
file, markdown quality failure, PretorianClientError from update_narrative, JSON
mode).
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import PretorianClientError
from pretorin.client.models import NarrativeResponse

runner = CliRunner()

# A content string that always passes ensure_audit_markdown for "narrative":
# requires no headings AND at least two rich elements including a structural one.
VALID_NARRATIVE_CONTENT = (
    "- The system enforces access control via RBAC.\n"
    "- All roles are defined in the configuration manifest.\n\n"
    "```yaml\nroles:\n  - name: admin\n    permissions: [read, write]\n```\n"
)


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
    """Return a fully wired mock client for narrative commands.

    Wires list_systems, get_system_compliance_status and get_system so that
    resolve_execution_context succeeds for system="Primary" /
    framework="fedramp-moderate".
    """
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    return client


# =============================================================================
# narrative get
# =============================================================================


def test_narrative_get_normal_mode() -> None:
    """narrative get renders control/framework/narrative output in normal mode."""
    client = _base_client()
    client.get_narrative = AsyncMock(
        return_value=NarrativeResponse(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            narrative="The system uses RBAC to manage access.",
            status="draft",
        )
    )

    result = _run_with_mock_client(
        ["narrative", "get", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "AC-02" in result.output
    assert "fedramp-moderate" in result.output
    # Narrative text or framework label should appear
    assert "RBAC" in result.output or "Primary" in result.output


def test_narrative_get_normal_no_narrative_set() -> None:
    """narrative get shows the 'No narrative set yet' placeholder when empty."""
    client = _base_client()
    client.get_narrative = AsyncMock(
        return_value=NarrativeResponse(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            narrative=None,
            status="not_started",
        )
    )

    result = _run_with_mock_client(
        ["narrative", "get", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0
    assert "No narrative" in result.output


def test_narrative_get_error() -> None:
    """narrative get exits 1 on PretorianClientError."""
    client = _base_client()
    client.get_narrative = AsyncMock(
        side_effect=PretorianClientError("Not found")
    )

    result = _run_with_mock_client(
        ["narrative", "get", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1
    assert "Fetch failed" in result.output
    assert "Not found" in result.output


def test_narrative_get_resolve_context_error() -> None:
    """narrative get exits 1 when resolve_execution_context raises."""
    client = _base_client()
    # Framework not in compliance status → resolve_execution_context will raise
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": []})

    result = _run_with_mock_client(
        ["narrative", "get", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1


# =============================================================================
# narrative push
# =============================================================================


def test_narrative_push_success_normal_mode(tmp_path: Path) -> None:
    """narrative push submits content and shows success message."""
    narrative_file = tmp_path / "narrative.md"
    narrative_file.write_text(VALID_NARRATIVE_CONTENT)

    client = _base_client()
    client.update_narrative = AsyncMock(return_value={"status": "ok"})

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "AC-02" in result.output
    client.update_narrative.assert_awaited_once()
    call_kwargs = client.update_narrative.call_args.kwargs
    assert call_kwargs["control_id"] == "ac-02"
    assert call_kwargs["framework_id"] == "fedramp-moderate"
    assert call_kwargs["is_ai_generated"] is False


def test_narrative_push_json_mode(tmp_path: Path) -> None:
    """narrative push --json emits the API result as JSON."""
    narrative_file = tmp_path / "narrative.md"
    narrative_file.write_text(VALID_NARRATIVE_CONTENT)

    client = _base_client()
    client.update_narrative = AsyncMock(
        return_value={"status": "ok", "narrative_id": "narr-001"}
    )

    result = _run_with_mock_client(
        [
            "--json",
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"


def test_narrative_push_empty_file(tmp_path: Path) -> None:
    """narrative push exits 1 when the file is empty."""
    narrative_file = tmp_path / "empty.md"
    narrative_file.write_text("   ")  # whitespace-only → stripped to empty

    client = _base_client()

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 1
    assert "empty" in result.output.lower()
    client.update_narrative.assert_not_called()


def test_narrative_push_fails_markdown_quality_heading(tmp_path: Path) -> None:
    """narrative push exits 1 when content contains a markdown heading."""
    narrative_file = tmp_path / "heading.md"
    narrative_file.write_text("# AC-02\n\nPlain text paragraph.")

    client = _base_client()

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 1
    assert "markdown requirements failed" in result.output
    client.update_narrative.assert_not_called()


def test_narrative_push_fails_markdown_quality_no_rich_elements(tmp_path: Path) -> None:
    """narrative push exits 1 when content lacks rich markdown elements."""
    narrative_file = tmp_path / "plain.md"
    narrative_file.write_text("Just plain prose with no lists, code, tables, or links.")

    client = _base_client()

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 1
    assert "markdown requirements failed" in result.output


def test_narrative_push_update_narrative_client_error(tmp_path: Path) -> None:
    """narrative push exits 1 when update_narrative raises PretorianClientError."""
    narrative_file = tmp_path / "narrative.md"
    narrative_file.write_text(VALID_NARRATIVE_CONTENT)

    client = _base_client()
    client.update_narrative = AsyncMock(
        side_effect=PretorianClientError("Server error", status_code=500)
    )

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 1
    assert "Push failed" in result.output
    assert "Server error" in result.output


def test_narrative_push_resolve_context_client_error(tmp_path: Path) -> None:
    """narrative push exits 1 when resolve_execution_context raises."""
    narrative_file = tmp_path / "narrative.md"
    narrative_file.write_text(VALID_NARRATIVE_CONTENT)

    client = _base_client()
    # Make the framework unknown so resolve_execution_context raises
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": []})

    result = _run_with_mock_client(
        [
            "narrative",
            "push",
            "ac-02",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    assert result.exit_code == 1
    client.update_narrative.assert_not_called()


def test_narrative_push_normalises_control_id(tmp_path: Path) -> None:
    """narrative push normalises abbreviated control IDs before sending to API."""
    narrative_file = tmp_path / "narrative.md"
    narrative_file.write_text(VALID_NARRATIVE_CONTENT)

    client = _base_client()
    client.update_narrative = AsyncMock(return_value={"status": "ok"})

    _run_with_mock_client(
        [
            "--json",
            "narrative",
            "push",
            "ac-2",  # abbreviated — should normalise to ac-02
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )

    client.update_narrative.assert_awaited_once()
    assert client.update_narrative.call_args.kwargs["control_id"] == "ac-02"
