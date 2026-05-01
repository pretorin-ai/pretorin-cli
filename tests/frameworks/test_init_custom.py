"""Tests for the init-custom command and its template."""

import json
from pathlib import Path

from typer.testing import CliRunner

from pretorin.cli.commands import app
from pretorin.frameworks.templates import minimal_unified
from pretorin.frameworks.validate import validate_unified

runner = CliRunner()


def test_minimal_template_is_valid():
    artifact = minimal_unified("acme-test")
    result = validate_unified(artifact)
    assert result.valid, [str(e) for e in result.errors]


def test_minimal_template_uses_provided_title():
    artifact = minimal_unified("x", title="Custom Title")
    assert artifact["metadata"]["title"] == "Custom Title"


def test_minimal_template_falls_back_to_id_when_no_title():
    artifact = minimal_unified("acme-x")
    assert artifact["metadata"]["title"] == "acme-x"


def test_init_custom_writes_valid_artifact(tmp_path: Path):
    out = tmp_path / "out.json"
    result = runner.invoke(
        app,
        ["init-custom", "acme-test", "--output", str(out)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()

    artifact = json.loads(out.read_text())
    assert artifact["framework_id"] == "acme-test"
    assert validate_unified(artifact).valid


def test_init_custom_refuses_to_overwrite_without_force(tmp_path: Path):
    out = tmp_path / "out.json"
    out.write_text("existing content")

    result = runner.invoke(app, ["init-custom", "x", "--output", str(out)])
    assert result.exit_code == 1
    assert out.read_text() == "existing content"


def test_init_custom_overwrites_with_force(tmp_path: Path):
    out = tmp_path / "out.json"
    out.write_text("existing content")

    result = runner.invoke(app, ["init-custom", "x", "--output", str(out), "--force"])
    assert result.exit_code == 0
    assert json.loads(out.read_text())["framework_id"] == "x"
