"""Tests for the unified framework JSON Schema validator."""

import json

from pretorin.frameworks.validate import (
    ValidationResult,
    validate_unified,
    validate_unified_file,
)


def _minimal_valid() -> dict:
    return {
        "framework_id": "acme-test",
        "version": "1.0",
        "source_format": "custom",
        "metadata": {
            "title": "Acme Test Framework",
            "version": "1.0",
            "last_modified": "2026-04-30T00:00:00Z",
        },
        "families": [
            {
                "id": "ac",
                "title": "Access Control",
                "class_type": "family",
                "controls": [
                    {
                        "id": "ac-01",
                        "title": "Access Control Policy",
                    }
                ],
            }
        ],
    }


def test_minimal_valid_artifact_passes():
    result = validate_unified(_minimal_valid())
    assert result.valid is True
    assert bool(result) is True
    assert result.errors == []


def test_missing_required_top_level_field():
    data = _minimal_valid()
    del data["framework_id"]
    result = validate_unified(data)
    assert result.valid is False
    assert any("framework_id" in str(e) for e in result.errors)


def test_invalid_source_format_enum():
    data = _minimal_valid()
    data["source_format"] = "made-up"
    result = validate_unified(data)
    assert result.valid is False


def test_validate_unified_file_invalid_json(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not valid json")
    result = validate_unified_file(p)
    assert result.valid is False
    assert "Invalid JSON" in result.errors[0].message


def test_validate_unified_file_valid(tmp_path):
    p = tmp_path / "good.json"
    p.write_text(json.dumps(_minimal_valid()))
    result = validate_unified_file(p)
    assert result.valid is True


def test_validation_result_str_with_path():
    from pretorin.frameworks.validate import ValidationError

    err = ValidationError(path="families.0.id", message="something wrong")
    assert "families.0.id" in str(err)


def test_validation_result_falsy_when_invalid():
    result = ValidationResult(valid=False)
    assert not result
