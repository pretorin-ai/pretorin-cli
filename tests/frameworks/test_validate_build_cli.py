"""Tests for validate-custom and build-custom CLI commands."""

import json
from pathlib import Path

from typer.testing import CliRunner

from pretorin.cli.commands import app
from pretorin.frameworks.templates import minimal_unified

runner = CliRunner()


# ---------------------------------------------------------------------------
# validate-custom
# ---------------------------------------------------------------------------


def test_validate_custom_passes_for_valid_artifact(tmp_path: Path):
    p = tmp_path / "unified.json"
    p.write_text(json.dumps(minimal_unified("acme")))

    result = runner.invoke(app, ["validate-custom", str(p)])
    assert result.exit_code == 0
    assert "passed" in result.output.lower() or "valid" in result.output.lower()


def test_validate_custom_fails_for_invalid_artifact(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"framework_id": "x"}))  # missing required fields

    result = runner.invoke(app, ["validate-custom", str(p)])
    assert result.exit_code == 1


def test_validate_custom_fails_for_invalid_json(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("not valid json {")

    result = runner.invoke(app, ["validate-custom", str(p)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# build-custom
# ---------------------------------------------------------------------------


def test_build_custom_passes_unified_through(tmp_path: Path):
    src = tmp_path / "src.json"
    src.write_text(json.dumps(minimal_unified("source-id")))
    out = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "acme-rebrand", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output

    artifact = json.loads(out.read_text())
    assert artifact["framework_id"] == "acme-rebrand"  # re-tagged
    assert artifact["source_format"] == "custom"


def test_build_custom_converts_oscal(tmp_path: Path):
    oscal = {
        "catalog": {
            "uuid": "11111111-2222-3333-4444-555555555555",
            "metadata": {"title": "Test OSCAL", "version": "1.0", "oscal-version": "1.1.2"},
            "groups": [
                {
                    "id": "ac",
                    "title": "Access Control",
                    "controls": [{"id": "ac-01", "title": "Policy", "props": []}],
                }
            ],
        }
    }
    src = tmp_path / "oscal.json"
    src.write_text(json.dumps(oscal))
    out = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "test-converted", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output

    artifact = json.loads(out.read_text())
    assert artifact["framework_id"] == "test-converted"
    assert artifact["source_format"] == "oscal"
    assert len(artifact["families"]) == 1


def test_build_custom_converts_known_custom_shape(tmp_path: Path):
    custom = {
        "control_families": [{"family_id": "ac", "family_name": "Access Control"}],
        "controls": [
            {
                "control_id": "ac-1",
                "control_name": "Policy",
                "family_id": "ac",
                "control_intent": "Develop policy.",
            }
        ],
    }
    src = tmp_path / "custom.json"
    src.write_text(json.dumps(custom))
    out = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "test-custom", "-o", str(out)],
    )
    assert result.exit_code == 0, result.output

    artifact = json.loads(out.read_text())
    assert artifact["framework_id"] == "test-custom"
    assert artifact["source_format"] == "custom"
    assert artifact["custom_format_type"] == "control_families"


def test_build_custom_rejects_unknown_shape(tmp_path: Path):
    src = tmp_path / "weird.json"
    src.write_text(json.dumps({"some": "thing", "totally": "unknown"}))
    out = tmp_path / "out.json"

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "test", "-o", str(out)],
    )
    assert result.exit_code == 1
    assert not out.exists()


def test_build_custom_refuses_to_overwrite_without_force(tmp_path: Path):
    src = tmp_path / "src.json"
    src.write_text(json.dumps(minimal_unified("x")))
    out = tmp_path / "out.json"
    out.write_text("existing")

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "test", "-o", str(out)],
    )
    assert result.exit_code == 1
    assert out.read_text() == "existing"


def test_build_custom_overwrites_with_force(tmp_path: Path):
    src = tmp_path / "src.json"
    src.write_text(json.dumps(minimal_unified("x")))
    out = tmp_path / "out.json"
    out.write_text("existing")

    result = runner.invoke(
        app,
        ["build-custom", str(src), "-f", "test", "-o", str(out), "--force"],
    )
    assert result.exit_code == 0
    assert json.loads(out.read_text())["framework_id"] == "test"
