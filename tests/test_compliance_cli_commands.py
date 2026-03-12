"""Tests for narrative/notes/evidence parity CLI commands."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.models import EvidenceItemResponse, NarrativeResponse

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode() -> None:
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
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]})
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))


def test_narrative_get_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    _mock_scoped_client(client)
    client.get_narrative = AsyncMock(
        return_value=NarrativeResponse(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            narrative="Current narrative",
            status="draft",
        )
    )

    result = _run_with_mock_client(
        ["--json", "narrative", "get", "ac-2", "fedramp-moderate", "--system", "Primary"],
        client,
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["narrative"] == "Current narrative"


def test_notes_list_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    _mock_scoped_client(client)
    client.list_control_notes = AsyncMock(return_value=[{"content": "Manual SSO evidence upload required"}])

    result = _run_with_mock_client(
        ["--json", "notes", "list", "ac-2", "fedramp-moderate", "--system", "Primary"],
        client,
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    client.list_control_notes.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        framework_id="fedramp-moderate",
    )


def test_evidence_upsert_reuses_duplicate_json() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    _mock_scoped_client(client)
    client.list_evidence = AsyncMock(
        return_value=[
            EvidenceItemResponse(
                id="ev-1",
                name="RBAC Config",
                description="- Role mapping",
                evidence_type="configuration",
                collected_at="2026-01-01T00:00:00+00:00",
            )
        ]
    )
    client.link_evidence_to_control = AsyncMock(return_value={"linked": True})

    result = _run_with_mock_client(
        [
            "--json",
            "evidence",
            "upsert",
            "ac-2",
            "fedramp-moderate",
            "--name",
            "RBAC Config",
            "--description",
            "- Role mapping",
            "--type",
            "configuration",
            "--system",
            "Primary",
        ],
        client,
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["created"] is False
    assert payload["evidence_id"] == "ev-1"


def test_evidence_upsert_rejects_plain_description() -> None:
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    _mock_scoped_client(client)

    result = _run_with_mock_client(
        [
            "evidence",
            "upsert",
            "ac-2",
            "fedramp-moderate",
            "--name",
            "RBAC Config",
            "--description",
            "Role mapping",
            "--type",
            "configuration",
            "--system",
            "Primary",
        ],
        client,
    )
    assert result.exit_code == 1
    assert "markdown requirements failed" in result.stdout
    client.list_evidence.assert_not_called()


def test_narrative_push_rejects_heading_markdown(tmp_path: Path) -> None:
    narrative_file = tmp_path / "ac02.md"
    narrative_file.write_text("# AC-02\n\nPlain text paragraph.")

    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    _mock_scoped_client(client)

    result = _run_with_mock_client(
        [
            "narrative",
            "push-file",
            "ac-2",
            "fedramp-moderate",
            "Primary",
            str(narrative_file),
        ],
        client,
    )
    assert result.exit_code == 1
    assert "markdown requirements failed" in result.stdout
    client.update_narrative.assert_not_called()
