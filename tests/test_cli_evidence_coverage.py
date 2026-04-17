"""Coverage tests for src/pretorin/cli/evidence.py.

Targets: evidence create, evidence list, evidence push, evidence search,
         evidence upsert — both JSON and normal output paths.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import PretorianClientError
from pretorin.client.models import EvidenceItemResponse

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


def _mock_scoped_client(client: AsyncMock) -> None:
    """Wire up the standard resolve_execution_context dependencies."""
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]})
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))


# =============================================================================
# evidence create
# =============================================================================


def test_evidence_create_json_mode() -> None:
    """evidence create outputs JSON with path/control/framework/name fields."""
    fake_path = Path("evidence/fedramp-moderate/ac-02/test-evidence.md")
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        mock_writer = MockWriter.return_value
        mock_writer.write.return_value = fake_path

        result = runner.invoke(
            app,
            [
                "--json",
                "evidence",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--description",
                "- RBAC configuration in Kubernetes",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert "path" in payload
    assert "name" in payload


def test_evidence_create_normal_mode() -> None:
    """evidence create renders a rich panel in normal mode."""
    fake_path = Path("evidence/fedramp-moderate/ac-02/test-evidence.md")
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        mock_writer = MockWriter.return_value
        mock_writer.write.return_value = fake_path

        result = runner.invoke(
            app,
            [
                "evidence",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--description",
                "- RBAC configuration in Kubernetes",
                "--name",
                "RBAC Config",
                "--type",
                "configuration",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Evidence Created" in result.output or "AC-02" in result.output


def test_evidence_create_name_defaults_to_description() -> None:
    """When --name is omitted the description (up to 60 chars) becomes the name."""
    fake_path = Path("evidence/fedramp-moderate/ac-02/rbac.md")
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        mock_writer = MockWriter.return_value
        mock_writer.write.return_value = fake_path

        result = runner.invoke(
            app,
            [
                "--json",
                "evidence",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--description",
                "- RBAC config",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "- RBAC config"


# =============================================================================
# evidence list
# =============================================================================


def _make_local_evidence(control_id: str = "ac-02", platform_id: str | None = None):
    return SimpleNamespace(
        control_id=control_id,
        framework_id="fedramp-moderate",
        name="RBAC Config",
        evidence_type="configuration",
        status="draft",
        platform_id=platform_id,
        path=Path(f"evidence/fedramp-moderate/{control_id}/rbac.md"),
    )


def test_evidence_list_json_with_items() -> None:
    """evidence list --json returns a list of evidence dicts."""
    items = [_make_local_evidence("ac-02", platform_id="ev-999")]
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        MockWriter.return_value.list_local.return_value = items

        result = runner.invoke(app, ["--json", "evidence", "list"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["control_id"] == "ac-02"
    assert payload[0]["platform_id"] == "ev-999"


def test_evidence_list_json_empty() -> None:
    """evidence list --json returns empty list when nothing exists."""
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        MockWriter.return_value.list_local.return_value = []

        result = runner.invoke(app, ["--json", "evidence", "list"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == []


def test_evidence_list_normal_with_items() -> None:
    """evidence list renders a table in normal mode when items are present."""
    items = [_make_local_evidence("ac-02"), _make_local_evidence("sc-07")]
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        MockWriter.return_value.list_local.return_value = items

        result = runner.invoke(app, ["evidence", "list"])

    assert result.exit_code == 0
    assert "Local Evidence" in result.output or "Total" in result.output


def test_evidence_list_normal_empty() -> None:
    """evidence list shows the 'no evidence' help message when list is empty."""
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        MockWriter.return_value.list_local.return_value = []

        result = runner.invoke(app, ["evidence", "list"])

    assert result.exit_code == 0
    assert "No local evidence" in result.output


def test_evidence_list_framework_filter() -> None:
    """evidence list --framework passes the filter to the writer."""
    with patch("pretorin.evidence.writer.EvidenceWriter") as MockWriter:
        MockWriter.return_value.list_local.return_value = []

        runner.invoke(app, ["evidence", "list", "--framework", "fedramp-moderate"])

        MockWriter.return_value.list_local.assert_called_once_with("fedramp-moderate")


# =============================================================================
# evidence push
# =============================================================================


def _make_sync_result(created=None, reused=None, skipped=None, errors=None, events=None):
    return SimpleNamespace(
        created=created or [],
        reused=reused or [],
        skipped=skipped or [],
        errors=errors or [],
        events=events or [],
    )


def test_evidence_push_success_normal_mode() -> None:
    """evidence push shows created/reused items in normal mode."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(
        created=["fedramp-moderate/ac-02/RBAC Config"],
        reused=["fedramp-moderate/sc-07/Firewall Config"],
    )

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 0
    assert "Created" in result.output or "Reused" in result.output


def test_evidence_push_dry_run() -> None:
    """evidence push --dry-run shows DRY RUN in output."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(created=["[dry-run] fedramp-moderate/ac-02/RBAC Config"])

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push", "--dry-run"], client)

    assert result.exit_code == 0
    assert "DRY RUN" in result.output


def test_evidence_push_json_mode() -> None:
    """evidence push --json emits a structured result dict."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(
        created=["fedramp-moderate/ac-02/RBAC Config"],
        skipped=["fedramp-moderate/sc-07/Firewall Config"],
    )

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["--json", "evidence", "push"], client)

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "created" in payload
    assert "skipped" in payload


def test_evidence_push_with_errors() -> None:
    """evidence push displays errors but exits 0 (errors shown inline)."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result(errors=["fedramp-moderate/ac-02/RBAC Config: timeout"])

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 0
    assert "Errors" in result.output or "timeout" in result.output


def test_evidence_push_nothing_to_push() -> None:
    """evidence push with nothing new shows the 'already synced' message."""
    client = AsyncMock()
    client.is_configured = True

    sync_result = _make_sync_result()

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(return_value=sync_result)
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 0
    assert "already synced" in result.output or "Nothing" in result.output


def test_evidence_push_client_error() -> None:
    """evidence push exits 1 when PretorianClientError is raised."""
    client = AsyncMock()
    client.is_configured = True

    with patch("pretorin.evidence.sync.EvidenceSync") as MockSync:
        MockSync.return_value.push = AsyncMock(side_effect=PretorianClientError("API unavailable"))
        result = _run_with_mock_client(["evidence", "push"], client)

    assert result.exit_code == 1
    assert "Push failed" in result.output


# =============================================================================
# evidence search
# =============================================================================


def _make_evidence_item(ev_id: str = "ev-aabbccdd"):
    return EvidenceItemResponse(
        id=ev_id,
        name="RBAC Config",
        description="- Role mapping",
        evidence_type="configuration",
        status="active",
        collected_at="2026-01-01T00:00:00+00:00",
    )


def test_evidence_search_json_with_results() -> None:
    """evidence search --json returns structured scope + evidence list."""
    client = AsyncMock()
    client.is_configured = True
    client.list_evidence = AsyncMock(return_value=[_make_evidence_item("ev-001")])
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
                "search",
                "--system",
                "Primary",
                "--framework-id",
                "fedramp-moderate",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert "evidence" in payload
    assert payload["framework_id"] == "fedramp-moderate"


def test_evidence_search_normal_no_results() -> None:
    """evidence search in normal mode shows no-results message when list is empty."""
    client = AsyncMock()
    client.is_configured = True
    client.list_evidence = AsyncMock(return_value=[])
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
                "search",
                "--system",
                "Primary",
                "--framework-id",
                "fedramp-moderate",
            ],
        )

    assert result.exit_code == 0
    assert "No evidence" in result.output


def test_evidence_search_normal_with_results() -> None:
    """evidence search shows table in normal mode when items returned."""
    client = AsyncMock()
    client.is_configured = True
    client.list_evidence = AsyncMock(return_value=[_make_evidence_item("ev-aabbccdd")])
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
                "search",
                "--system",
                "Primary",
                "--framework-id",
                "fedramp-moderate",
            ],
        )

    assert result.exit_code == 0
    assert "Total" in result.output or "Platform Evidence" in result.output


def test_evidence_search_client_error() -> None:
    """evidence search exits 1 on PretorianClientError."""
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
            side_effect=PretorianClientError("Scope resolution failed"),
        ),
    ):
        result = runner.invoke(
            app,
            ["evidence", "search", "--system", "Primary", "--framework-id", "fedramp-moderate"],
        )

    assert result.exit_code == 1
    assert "Search failed" in result.output


# =============================================================================
# evidence upsert
# =============================================================================


def _upsert_result(created: bool = True, linked: bool = True, link_error: str | None = None):
    d = {"created": created, "evidence_id": "ev-123", "linked": linked}
    return SimpleNamespace(
        created=created,
        evidence_id="ev-123",
        linked=linked,
        link_error=link_error,
        to_dict=lambda: d,
    )


def test_evidence_upsert_success_json() -> None:
    """evidence upsert outputs JSON payload on success."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
        patch(
            "pretorin.workflows.compliance_updates.upsert_evidence",
            new_callable=AsyncMock,
            return_value=_upsert_result(created=True),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "--json",
                "evidence",
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "--name",
                "RBAC Config",
                "--description",
                "- Role mapping\n\n`kubectl get roles`\n",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["created"] is True
    assert payload["evidence_id"] == "ev-123"
    assert payload["system_id"] == "sys-1"


def test_evidence_upsert_success_normal_mode() -> None:
    """evidence upsert renders a panel in normal mode."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
        patch(
            "pretorin.workflows.compliance_updates.upsert_evidence",
            new_callable=AsyncMock,
            return_value=_upsert_result(created=False, linked=True),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "--name",
                "RBAC Config",
                "--description",
                "- Role mapping\n\n`kubectl get roles`\n",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Evidence Upserted" in result.output or "Reused" in result.output


def test_evidence_upsert_link_error_shows_warning() -> None:
    """evidence upsert shows a warning when link_error is present."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
        patch(
            "pretorin.workflows.compliance_updates.upsert_evidence",
            new_callable=AsyncMock,
            return_value=_upsert_result(created=True, linked=False, link_error="control not found"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "--name",
                "RBAC Config",
                "--description",
                "- Role mapping\n\n`kubectl get roles`\n",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 0
    assert "Warning" in result.output or "link failed" in result.output


def test_evidence_upsert_invalid_evidence_type() -> None:
    """evidence upsert exits 1 immediately for an invalid evidence_type."""
    result = runner.invoke(
        app,
        [
            "evidence",
            "upsert",
            "ac-02",
            "fedramp-moderate",
            "--name",
            "Bad Type Evidence",
            "--description",
            "- item",
            "--type",
            "not_a_valid_type",
        ],
    )

    assert result.exit_code == 1
    assert "Invalid evidence type" in result.output


def test_evidence_upsert_value_error_from_markdown_quality() -> None:
    """evidence upsert exits 1 when upsert_evidence raises ValueError (markdown quality)."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
        patch(
            "pretorin.workflows.compliance_updates.upsert_evidence",
            new_callable=AsyncMock,
            side_effect=ValueError("Evidence description markdown requirements failed: no rich elements"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "--name",
                "RBAC Config",
                "--description",
                "plain text only",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 1
    assert "Upsert failed" in result.output


def test_evidence_upsert_client_error() -> None:
    """evidence upsert exits 1 when PretorianClientError is raised."""
    client = AsyncMock()
    client.is_configured = True
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))

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
        patch(
            "pretorin.workflows.compliance_updates.upsert_evidence",
            new_callable=AsyncMock,
            side_effect=PretorianClientError("Platform error"),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "evidence",
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "--name",
                "RBAC Config",
                "--description",
                "- Role mapping\n\n`kubectl get roles`\n",
                "--system",
                "Primary",
            ],
        )

    assert result.exit_code == 1
    assert "Upsert failed" in result.output
    assert "Platform error" in result.output


# =============================================================================
# evidence delete
# =============================================================================


def test_evidence_delete_success_json() -> None:
    """evidence delete outputs JSON with evidence_id and deleted flag."""
    client = AsyncMock()
    client.is_configured = True
    client.delete_evidence = AsyncMock()

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
                "delete",
                "ev-abc123",
                "--system",
                "Primary",
                "--yes",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["evidence_id"] == "ev-abc123"
    assert payload["deleted"] is True


def test_evidence_delete_success_normal() -> None:
    """evidence delete shows success message in normal mode."""
    client = AsyncMock()
    client.is_configured = True
    client.delete_evidence = AsyncMock()

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
            ["evidence", "delete", "ev-abc123", "--yes"],
        )

    assert result.exit_code == 0, result.output
    assert "deleted" in result.output


def test_evidence_delete_cancelled() -> None:
    """evidence delete exits 0 when user declines confirmation."""
    result = runner.invoke(app, ["evidence", "delete", "ev-abc123"], input="n\n")
    assert result.exit_code == 0
    assert "Cancelled" in result.output


def test_evidence_delete_client_error() -> None:
    """evidence delete exits 1 on PretorianClientError."""
    client = AsyncMock()
    client.is_configured = True
    client.delete_evidence = AsyncMock(side_effect=PretorianClientError("Not found"))

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
            ["evidence", "delete", "ev-abc123", "--yes"],
        )

    assert result.exit_code == 1
    assert "Delete failed" in result.output
    assert "Not found" in result.output
