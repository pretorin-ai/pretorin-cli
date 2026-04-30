"""Coverage tests for src/pretorin/cli/notes.py.

Targets: notes list, notes add — both JSON and normal output paths plus error
handling.
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
    """Build a fully wired mock client for notes commands.

    Wires up list_systems, get_system_compliance_status and get_system so that
    resolve_execution_context succeeds for system="Primary" /
    framework="fedramp-moderate".
    """
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary"}])
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]})
    client.get_system = AsyncMock(return_value=SimpleNamespace(name="Primary"))
    return client


# =============================================================================
# notes list
# =============================================================================


def test_notes_list_normal_with_notes() -> None:
    """notes list renders a table when notes are present."""
    client = _base_client()
    client.list_control_notes = AsyncMock(
        return_value=[
            {"content": "Manual SSO evidence upload required"},
            {"content": "Reviewed by auditor 2026-01-15"},
        ]
    )

    result = _run_with_mock_client(
        ["notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "AC-02" in result.output
    assert "Manual SSO" in result.output or "Reviewed" in result.output


def test_notes_list_normal_empty() -> None:
    """notes list shows the empty-state message when there are no notes."""
    client = _base_client()
    client.list_control_notes = AsyncMock(return_value=[])

    result = _run_with_mock_client(
        ["notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0
    assert "No notes" in result.output


def test_notes_list_json_mode() -> None:
    """notes list --json emits a structured payload with total and notes."""
    client = _base_client()
    client.list_control_notes = AsyncMock(return_value=[{"content": "Manual SSO evidence upload required"}])

    result = _run_with_mock_client(
        ["--json", "notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert payload["system_id"] == "sys-1"
    # Notes list should have been called with correct keyword args
    client.list_control_notes.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        framework_id="fedramp-moderate",
    )


def test_notes_list_json_empty() -> None:
    """notes list --json returns total:0 and empty notes list."""
    client = _base_client()
    client.list_control_notes = AsyncMock(return_value=[])

    result = _run_with_mock_client(
        ["--json", "notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total"] == 0
    assert payload["notes"] == []


def test_notes_list_error() -> None:
    """notes list exits 1 on PretorianClientError."""
    client = _base_client()
    client.list_control_notes = AsyncMock(side_effect=PretorianClientError("Not authorized"))

    result = _run_with_mock_client(
        ["notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1
    assert "List failed" in result.output
    assert "Not authorized" in result.output


def test_notes_list_resolve_context_error() -> None:
    """notes list exits 1 when context resolution raises PretorianClientError."""
    client = _base_client()
    # Simulate missing framework in compliance status so resolve_execution_context fails
    client.get_system_compliance_status = AsyncMock(return_value={"frameworks": []})

    result = _run_with_mock_client(
        ["notes", "list", "ac-02", "fedramp-moderate", "--system", "Primary"],
        client,
    )

    assert result.exit_code == 1


# =============================================================================
# notes add
# =============================================================================


def test_notes_add_normal_mode() -> None:
    """notes add shows a success message in normal mode."""
    client = _base_client()
    client.add_control_note = AsyncMock(return_value={"id": "note-1", "content": "Deploy audit log"})

    result = _run_with_mock_client(
        [
            "notes",
            "add",
            "ac-02",
            "fedramp-moderate",
            "--content",
            "Deploy audit log",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "AC-02" in result.output


def test_notes_add_json_mode() -> None:
    """notes add --json emits a payload with system_id, note, control_id."""
    client = _base_client()
    client.add_control_note = AsyncMock(return_value={"id": "note-1", "content": "Deploy audit log"})

    result = _run_with_mock_client(
        [
            "--json",
            "notes",
            "add",
            "ac-02",
            "fedramp-moderate",
            "--content",
            "Deploy audit log",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert payload["system_id"] == "sys-1"
    assert payload["note"] == {"id": "note-1", "content": "Deploy audit log"}
    client.add_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        framework_id="fedramp-moderate",
        content="Deploy audit log",
        source="cli",
    )


def test_notes_add_error() -> None:
    """notes add exits 1 when the API call raises PretorianClientError."""
    client = _base_client()
    client.add_control_note = AsyncMock(side_effect=PretorianClientError("Control not found"))

    result = _run_with_mock_client(
        [
            "notes",
            "add",
            "ac-02",
            "fedramp-moderate",
            "--content",
            "Audit note",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 1
    assert "Add failed" in result.output
    assert "Control not found" in result.output


# =============================================================================
# notes resolve
# =============================================================================


def test_notes_resolve_normal_mode() -> None:
    """notes resolve shows a success message in normal mode."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(
        return_value={"id": "note-1", "content": "Deploy audit log", "is_resolved": True}
    )

    result = _run_with_mock_client(
        [
            "notes",
            "resolve",
            "ac-02",
            "fedramp-moderate",
            "note-1",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "resolved" in result.output.lower()
    assert "AC-02" in result.output


def test_notes_resolve_json_mode() -> None:
    """notes resolve --json emits a payload with system_id, note, control_id."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(
        return_value={"id": "note-1", "content": "Deploy audit log", "is_resolved": True}
    )

    result = _run_with_mock_client(
        [
            "--json",
            "notes",
            "resolve",
            "ac-02",
            "fedramp-moderate",
            "note-1",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert payload["system_id"] == "sys-1"
    assert payload["note"]["is_resolved"] is True
    client.resolve_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        note_id="note-1",
        framework_id="fedramp-moderate",
        is_resolved=True,
        content=None,
        is_pinned=None,
    )


def test_notes_resolve_reopen() -> None:
    """notes resolve --reopen passes is_resolved=False."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(
        return_value={"id": "note-1", "content": "Deploy audit log", "is_resolved": False}
    )

    result = _run_with_mock_client(
        [
            "notes",
            "resolve",
            "ac-02",
            "fedramp-moderate",
            "note-1",
            "--reopen",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    assert "reopened" in result.output.lower()
    client.resolve_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        note_id="note-1",
        framework_id="fedramp-moderate",
        is_resolved=False,
        content=None,
        is_pinned=None,
    )


def test_notes_resolve_with_content_update() -> None:
    """notes resolve can update content alongside resolving."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(return_value={"id": "note-1", "content": "Updated", "is_resolved": True})

    result = _run_with_mock_client(
        [
            "--json",
            "notes",
            "resolve",
            "ac-02",
            "fedramp-moderate",
            "note-1",
            "--content",
            "Updated",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 0, result.output
    client.resolve_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        note_id="note-1",
        framework_id="fedramp-moderate",
        is_resolved=True,
        content="Updated",
        is_pinned=None,
    )


def test_notes_resolve_error() -> None:
    """notes resolve exits 1 when the API call raises PretorianClientError."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(side_effect=PretorianClientError("Note not found"))

    result = _run_with_mock_client(
        [
            "notes",
            "resolve",
            "ac-02",
            "fedramp-moderate",
            "note-1",
            "--system",
            "Primary",
        ],
        client,
    )

    assert result.exit_code == 1
    assert "Resolve failed" in result.output
    assert "Note not found" in result.output


def test_notes_resolve_normalises_control_id() -> None:
    """notes resolve normalises the control ID before sending to the API."""
    client = _base_client()
    client.resolve_control_note = AsyncMock(return_value={"id": "note-1", "is_resolved": True})

    _run_with_mock_client(
        [
            "--json",
            "notes",
            "resolve",
            "ac-2",
            "fedramp-moderate",
            "note-1",
            "--system",
            "Primary",
        ],
        client,
    )

    client.resolve_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        note_id="note-1",
        framework_id="fedramp-moderate",
        is_resolved=True,
        content=None,
        is_pinned=None,
    )


# =============================================================================
# notes add (continued)
# =============================================================================


def test_notes_add_normalises_control_id() -> None:
    """notes add normalises the control ID before sending to the API."""
    client = _base_client()
    client.add_control_note = AsyncMock(return_value={"id": "note-2", "content": "Check"})

    _run_with_mock_client(
        [
            "--json",
            "notes",
            "add",
            "ac-2",  # abbreviated form
            "fedramp-moderate",
            "--content",
            "Check",
            "--system",
            "Primary",
        ],
        client,
    )

    # The normalised control id should be "ac-02"
    client.add_control_note.assert_awaited_once_with(
        system_id="sys-1",
        control_id="ac-02",
        framework_id="fedramp-moderate",
        content="Check",
        source="cli",
    )


# =============================================================================
# notes create (local file)
# =============================================================================


def test_notes_create_normal_mode() -> None:
    """notes create writes a local file and shows success output."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.write.return_value = Path("/tmp/notes/test.md")
        result = runner.invoke(
            app,
            [
                "notes",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--content",
                "Gap: missing SSO evidence",
            ],
        )

    assert result.exit_code == 0, result.output
    assert "Note Created" in result.output
    assert "AC-02" in result.output
    assert "fedramp-moderate" in result.output


def test_notes_create_json_mode() -> None:
    """notes create --json emits structured JSON."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.write.return_value = Path("/tmp/notes/test.md")
        result = runner.invoke(
            app,
            [
                "--json",
                "notes",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--content",
                "Gap: missing SSO evidence",
            ],
        )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert "path" in payload


def test_notes_create_normalises_control_id() -> None:
    """notes create normalises abbreviated control IDs."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.write.return_value = Path("/tmp/notes/test.md")
        result = runner.invoke(
            app,
            [
                "--json",
                "notes",
                "create",
                "ac-2",
                "fedramp-moderate",
                "--content",
                "Test note",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"


def test_notes_create_with_custom_name() -> None:
    """notes create uses --name when provided."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.write.return_value = Path("/tmp/notes/test.md")
        result = runner.invoke(
            app,
            [
                "--json",
                "notes",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--content",
                "Test note",
                "--name",
                "custom-name",
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["name"] == "custom-name"


def test_notes_create_default_name_from_content() -> None:
    """notes create uses first 60 chars of content as name when no --name given."""
    long_content = "A" * 100
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.write.return_value = Path("/tmp/notes/test.md")
        result = runner.invoke(
            app,
            [
                "--json",
                "notes",
                "create",
                "ac-02",
                "fedramp-moderate",
                "--content",
                long_content,
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["name"]) == 60


# =============================================================================
# notes list --local
# =============================================================================


def test_notes_list_local_empty() -> None:
    """notes list --local shows empty message when no local notes exist."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.list_local.return_value = []
        result = runner.invoke(app, ["notes", "list", "--local"])

    assert result.exit_code == 0
    assert "No local notes" in result.output


def test_notes_list_local_with_items() -> None:
    """notes list --local renders a table when notes exist."""
    from types import SimpleNamespace

    mock_item = SimpleNamespace(
        control_id="ac-02",
        framework_id="fedramp-moderate",
        name="missing-sso",
        platform_synced=False,
    )
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.list_local.return_value = [mock_item]
        result = runner.invoke(app, ["notes", "list", "--local"])

    assert result.exit_code == 0
    assert "AC-02" in result.output
    assert "fedramp-moderate" in result.output


def test_notes_list_local_json_mode() -> None:
    """notes list --local --json emits structured JSON list."""
    from types import SimpleNamespace

    mock_item = SimpleNamespace(
        control_id="ac-02",
        framework_id="fedramp-moderate",
        name="missing-sso",
        platform_synced=True,
        path=Path("/tmp/test.md"),
    )
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.list_local.return_value = [mock_item]
        result = runner.invoke(app, ["--json", "notes", "list", "--local"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload) == 1
    assert payload[0]["control_id"] == "ac-02"
    assert payload[0]["platform_synced"] is True


def test_notes_list_local_with_framework_filter() -> None:
    """notes list --local --framework filters results."""
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.list_local.return_value = []
        result = runner.invoke(app, ["notes", "list", "--local", "--framework", "fedramp-moderate"])

    mock_writer_cls.return_value.list_local.assert_called_once_with("fedramp-moderate")
    assert result.exit_code == 0


def test_notes_list_local_long_name_truncation() -> None:
    """notes list --local truncates names longer than 40 chars."""
    from types import SimpleNamespace

    long_name = "a" * 50
    mock_item = SimpleNamespace(
        control_id="ac-02",
        framework_id="fedramp-moderate",
        name=long_name,
        platform_synced=False,
    )
    with patch("pretorin.notes.writer.NotesWriter") as mock_writer_cls:
        mock_writer_cls.return_value.list_local.return_value = [mock_item]
        result = runner.invoke(app, ["notes", "list", "--local"])

    assert result.exit_code == 0
    # Table renders with truncation — either "..." or Rich's ellipsis char "…"
    assert "..." in result.output or "\u2026" in result.output


def test_notes_list_missing_args_error() -> None:
    """notes list (platform) requires control_id and framework_id."""
    result = runner.invoke(app, ["notes", "list"])
    assert result.exit_code == 1
    assert "control_id and framework_id are required" in result.output
