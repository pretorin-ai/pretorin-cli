"""Tests for platform-touching frameworks CLI commands.

Mocks PretorianClient to avoid hitting the platform. Smoke-testing against
`make dev-local` is documented separately for manual verification.
"""

import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from pretorin.cli.commands import app
from pretorin.client.api import PretorianClientError
from pretorin.frameworks.templates import minimal_unified

runner = CliRunner()


@pytest.fixture
def mock_client(monkeypatch):
    """Replace PretorianClient with a mocked async-context-manager."""
    mock = MagicMock()
    mock.is_configured = True
    mock.create_custom_draft = AsyncMock()
    mock.publish_draft = AsyncMock()
    mock.fork_framework = AsyncMock()
    mock.create_rebase_draft = AsyncMock()
    mock.list_revisions = AsyncMock()

    @asynccontextmanager
    async def fake_ctx(*args, **kwargs):
        yield mock

    monkeypatch.setattr("pretorin.cli.commands.PretorianClient", fake_ctx)
    return mock


# ---------------------------------------------------------------------------
# upload-custom
# ---------------------------------------------------------------------------


def test_upload_custom_draft_only(tmp_path: Path, mock_client):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(minimal_unified("acme")))

    mock_client.create_custom_draft.return_value = {
        "revision_id": "rev-1",
        "lifecycle_state": "draft",
        "validation_status": "passed",
    }

    result = runner.invoke(app, ["upload-custom", str(p)])
    assert result.exit_code == 0, result.output
    mock_client.create_custom_draft.assert_awaited_once()
    mock_client.publish_draft.assert_not_awaited()
    args, _kwargs = mock_client.create_custom_draft.call_args
    assert args[0] == "acme"  # framework_id from artifact


def test_upload_custom_with_publish(tmp_path: Path, mock_client):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(minimal_unified("acme")))

    mock_client.create_custom_draft.return_value = {
        "revision_id": "rev-1",
        "lifecycle_state": "draft",
        "validation_status": "passed",
    }
    mock_client.publish_draft.return_value = {"lifecycle_state": "published", "revision_id": "rev-1"}

    result = runner.invoke(app, ["upload-custom", str(p), "--publish"])
    assert result.exit_code == 0, result.output
    mock_client.publish_draft.assert_awaited_once_with("acme", "rev-1")


def test_upload_custom_uses_explicit_framework_id(tmp_path: Path, mock_client):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(minimal_unified("from-artifact")))

    mock_client.create_custom_draft.return_value = {"revision_id": "rev-1", "lifecycle_state": "draft"}

    result = runner.invoke(app, ["upload-custom", str(p), "-f", "override-id"])
    assert result.exit_code == 0
    args, _ = mock_client.create_custom_draft.call_args
    assert args[0] == "override-id"


def test_upload_custom_renders_validation_report_on_400(tmp_path: Path, mock_client):
    p = tmp_path / "u.json"
    p.write_text(json.dumps(minimal_unified("acme")))

    mock_client.create_custom_draft.side_effect = PretorianClientError(
        "Validation failed",
        400,
        {
            "validation_report": {
                "valid": False,
                "errors": [
                    {"path": "families.0.id", "message": "is required"},
                    {"path": "metadata", "message": "is required"},
                ],
            }
        },
    )

    result = runner.invoke(app, ["upload-custom", str(p)])
    assert result.exit_code == 1
    assert "families.0.id" in result.output
    assert "is required" in result.output


def test_upload_custom_invalid_json(tmp_path: Path, mock_client):
    p = tmp_path / "bad.json"
    p.write_text("not json")

    result = runner.invoke(app, ["upload-custom", str(p)])
    assert result.exit_code == 1


def test_upload_custom_missing_framework_id(tmp_path: Path, mock_client):
    p = tmp_path / "u.json"
    artifact = minimal_unified("acme")
    del artifact["framework_id"]
    p.write_text(json.dumps(artifact))

    result = runner.invoke(app, ["upload-custom", str(p)])
    assert result.exit_code == 1
    assert "framework_id" in result.output


# ---------------------------------------------------------------------------
# fork-framework / rebase-fork
# ---------------------------------------------------------------------------


def test_fork_framework_calls_client(mock_client):
    mock_client.fork_framework.return_value = {
        "revision_id": "rev-fork-1",
        "lifecycle_state": "draft",
        "upstream_base_revision_id": "upstream-uuid",
    }
    result = runner.invoke(app, ["fork-framework", "nist-800-53-r5", "acme-nist", "-v", "initial"])
    assert result.exit_code == 0, result.output
    mock_client.fork_framework.assert_awaited_once_with("nist-800-53-r5", "acme-nist", "initial")


def test_rebase_fork_calls_client(mock_client):
    mock_client.create_rebase_draft.return_value = {
        "revision_id": "rev-rebase-1",
        "lifecycle_state": "draft",
    }
    result = runner.invoke(app, ["rebase-fork", "acme-nist", "-v", "rebase-1"])
    assert result.exit_code == 0, result.output
    mock_client.create_rebase_draft.assert_awaited_once_with("acme-nist", "rebase-1")


# ---------------------------------------------------------------------------
# revisions
# ---------------------------------------------------------------------------


def test_revisions_renders_table(mock_client):
    mock_client.list_revisions.return_value = [
        {"id": "rev-1", "lifecycle_state": "published", "version_label": "v1.0", "validation_status": "passed"},
        {"id": "rev-2", "lifecycle_state": "draft", "version_label": "v1.1", "validation_status": "passed"},
    ]
    result = runner.invoke(app, ["revisions", "acme-nist"])
    assert result.exit_code == 0, result.output
    assert "rev-1" in result.output
    assert "rev-2" in result.output
    assert "published" in result.output
    assert "draft" in result.output


def test_revisions_handles_empty(mock_client):
    mock_client.list_revisions.return_value = []
    result = runner.invoke(app, ["revisions", "x"])
    assert result.exit_code == 0
    assert "No revisions" in result.output
