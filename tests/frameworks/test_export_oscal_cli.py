"""Tests for the export-oscal CLI command."""

import json
from pathlib import Path

from typer.testing import CliRunner

from pretorin.cli.commands import app
from pretorin.frameworks import oscal_to_unified

runner = CliRunner()


def test_export_oscal_writes_catalog(tmp_path: Path):
    # Build a unified artifact via the OSCAL converter so we have valid _oscal blocks
    oscal_input = {
        "catalog": {
            "uuid": "11111111-2222-3333-4444-555555555555",
            "metadata": {"title": "Test", "version": "1.0", "oscal-version": "1.1.2"},
            "groups": [
                {
                    "id": "ac",
                    "title": "Access Control",
                    "controls": [{"id": "ac-01", "title": "Policy", "props": []}],
                }
            ],
        }
    }
    unified = oscal_to_unified.convert(oscal_input, "test-fw")

    src = tmp_path / "unified.json"
    src.write_text(json.dumps(unified))
    out = tmp_path / "out-catalog.json"

    result = runner.invoke(app, ["export-oscal", str(src), "-o", str(out)])
    assert result.exit_code == 0, result.output

    catalog = json.loads(out.read_text())
    assert "catalog" in catalog
    assert catalog["catalog"]["uuid"] == "11111111-2222-3333-4444-555555555555"
    assert len(catalog["catalog"]["groups"]) == 1


def test_export_oscal_refuses_to_overwrite_without_force(tmp_path: Path):
    src = tmp_path / "u.json"
    src.write_text(json.dumps({"framework_id": "x", "metadata": {}, "families": []}))
    out = tmp_path / "out.json"
    out.write_text("existing")

    result = runner.invoke(app, ["export-oscal", str(src), "-o", str(out)])
    assert result.exit_code == 1
    assert out.read_text() == "existing"


def test_export_oscal_invalid_json(tmp_path: Path):
    src = tmp_path / "bad.json"
    src.write_text("not json")
    out = tmp_path / "out.json"

    result = runner.invoke(app, ["export-oscal", str(src), "-o", str(out)])
    assert result.exit_code == 1
