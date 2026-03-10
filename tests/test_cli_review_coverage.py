"""Coverage tests for src/pretorin/cli/review.py."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import typer
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.cli.review import _discover_files, _validate_path
from pretorin.client.api import PretorianClientError
from pretorin.client.models import ControlDetail, ControlImplementationResponse, ControlReferences

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


def _make_client():
    client = AsyncMock()
    client.is_configured = True
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Primary System"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )
    client.get_control = AsyncMock(return_value=ControlDetail(id="ac-02", title="Access Management"))
    client.get_control_references = AsyncMock(
        return_value=ControlReferences(
            control_id="ac-02",
            statement="The organization manages accounts.",
            guidance="See NIST SP 800-53.",
        )
    )
    client.get_control_implementation = AsyncMock(
        return_value=ControlImplementationResponse(
            control_id="ac-02",
            status="in_progress",
            implementation_narrative="Access is controlled via IAM.",
            evidence_count=2,
        )
    )
    return client


def _patch_client(client):
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return patch("pretorin.client.api.PretorianClient", return_value=ctx)


def _patch_resolve(system_id="sys-1", framework_id="fedramp-moderate"):
    return patch(
        "pretorin.cli.review.resolve_execution_context",
        new_callable=AsyncMock,
        return_value=(system_id, framework_id),
    )


# ---------------------------------------------------------------------------
# _validate_path
# ---------------------------------------------------------------------------


def test_validate_path_within_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    sub = tmp_path / "src"
    sub.mkdir()
    result = _validate_path(sub, label="--path")
    assert result == sub.resolve()


def test_validate_path_traversal_raises_bad_parameter(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outside = tmp_path.parent / "secret"
    with pytest.raises(typer.BadParameter, match="must be within the working directory"):
        _validate_path(outside, label="--path")


# ---------------------------------------------------------------------------
# _discover_files
# ---------------------------------------------------------------------------


def test_discover_files_returns_single_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "main.py"
    f.write_text("print('hello')")
    assert _discover_files(f) == [f]


def test_discover_files_from_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "app.py").write_text("# python")
    (tmp_path / "config.yaml").write_text("key: value")
    result = _discover_files(tmp_path)
    names = {p.name for p in result}
    assert "app.py" in names
    assert "config.yaml" in names


def test_discover_files_empty_directory_returns_empty(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert _discover_files(tmp_path) == []


# ---------------------------------------------------------------------------
# review run — local mode
# ---------------------------------------------------------------------------


def test_review_run_local_creates_markdown_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    client = _make_client()

    with _patch_client(client):
        result = runner.invoke(
            app,
            [
                "--json", "review", "run",
                "--control-id", "ac-02",
                "--framework-id", "fedramp-moderate",
                "--local",
                "--path", str(tmp_path),
                "--output-dir", str(output_dir),
            ],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    output_file = output_dir / "fedramp-moderate" / "ac-02.md"
    assert output_file.exists()
    assert "AC-02" in output_file.read_text()


def test_review_run_local_without_framework_exits_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _make_client()
    with _patch_client(client):
        result = runner.invoke(app, ["review", "run", "--control-id", "ac-02", "--local"])
    assert result.exit_code == 1
    assert "--framework-id is required" in result.stdout


def test_review_run_local_normal_mode_shows_saved_panel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    client = _make_client()

    with _patch_client(client):
        result = runner.invoke(
            app,
            [
                "review", "run",
                "--control-id", "ac-02",
                "--framework-id", "fedramp-moderate",
                "--local",
                "--path", str(tmp_path),
                "--output-dir", str(output_dir),
            ],
        )

    assert result.exit_code == 0
    assert "AC-02" in result.stdout


# ---------------------------------------------------------------------------
# review run — platform mode
# ---------------------------------------------------------------------------


def test_review_run_platform_json_includes_implementation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _make_client()

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(
            app,
            ["--json", "review", "run", "--control-id", "ac-02", "--path", str(tmp_path)],
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["system_id"] == "sys-1"
    assert payload["implementation_status"] == "in_progress"
    assert payload["evidence_count"] == 2


def test_review_run_platform_context_error_exits_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _make_client()

    with _patch_client(client), patch(
        "pretorin.cli.review.resolve_execution_context",
        new_callable=AsyncMock,
        side_effect=PretorianClientError("No system/framework context set."),
    ):
        result = runner.invoke(app, ["review", "run", "--control-id", "ac-02"])

    assert result.exit_code == 1
    assert "context" in result.stdout.lower() or "system" in result.stdout.lower()


def test_review_run_platform_control_fetch_error_exits_one(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _make_client()
    client.get_control = AsyncMock(side_effect=PretorianClientError("control not found"))

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(app, ["review", "run", "--control-id", "ac-02"])

    assert result.exit_code == 1
    assert "failed to fetch control" in result.stdout.lower()


def test_review_run_platform_normal_mode_shows_control_panel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    client = _make_client()

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(
            app, ["review", "run", "--control-id", "ac-02", "--path", str(tmp_path)]
        )

    assert result.exit_code == 0
    assert "AC-02" in result.stdout
    assert "Control Requirements" in result.stdout


# ---------------------------------------------------------------------------
# review status
# ---------------------------------------------------------------------------


def test_review_status_json_mode():
    client = _make_client()

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(
            app, ["--json", "review", "status", "--control-id", "ac-02"]
        )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["control_id"] == "ac-02"
    assert payload["framework_id"] == "fedramp-moderate"
    assert payload["system_id"] == "sys-1"
    assert payload["status"] == "in_progress"
    assert payload["evidence_count"] == 2


def test_review_status_normal_mode_displays_panel():
    client = _make_client()

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(app, ["review", "status", "--control-id", "ac-02"])

    assert result.exit_code == 0
    assert "AC-02" in result.stdout
    assert "Implementation Status" in result.stdout


def test_review_status_context_error_json():
    client = _make_client()

    with _patch_client(client), patch(
        "pretorin.cli.review.resolve_execution_context",
        new_callable=AsyncMock,
        side_effect=PretorianClientError("No context set."),
    ):
        result = runner.invoke(
            app, ["--json", "review", "status", "--control-id", "ac-02"]
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["error"] == "No context set."
    assert payload["control_id"] == "ac-02"


def test_review_status_implementation_fetch_error_exits_one_json():
    client = _make_client()
    client.get_control_implementation = AsyncMock(
        side_effect=PretorianClientError("not found", status_code=404)
    )

    with _patch_client(client), _patch_resolve():
        result = runner.invoke(
            app, ["--json", "review", "status", "--control-id", "ac-02"]
        )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert "error" in payload


def test_review_status_context_error_normal_mode():
    client = _make_client()

    with _patch_client(client), patch(
        "pretorin.cli.review.resolve_execution_context",
        new_callable=AsyncMock,
        side_effect=PretorianClientError("No context set."),
    ):
        result = runner.invoke(app, ["review", "status", "--control-id", "ac-02"])

    assert result.exit_code == 1
    assert "no context set" in result.stdout.lower()
