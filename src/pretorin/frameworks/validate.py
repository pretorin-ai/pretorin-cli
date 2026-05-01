"""JSON Schema validator for unified framework artifacts.

Local pre-flight only — the platform runs the authoritative validator on upload
and returns a structured `validation_report` on 400. Use this to catch
structural errors fast before paying the network round-trip.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


@dataclass
class ValidationError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}" if self.path else self.message


@dataclass
class ValidationResult:
    valid: bool
    errors: list[ValidationError] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.valid


_SCHEMA_CACHE: dict[str, Any] | None = None


def _load_schema() -> dict[str, Any]:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        schema_path = resources.files("pretorin.frameworks.schema").joinpath("unified_framework.schema.json")
        _SCHEMA_CACHE = json.loads(schema_path.read_text())
    return _SCHEMA_CACHE


def validate_unified(data: Any) -> ValidationResult:
    """Validate a unified.json artifact against the bundled JSON Schema.

    Returns a ValidationResult — falsy when invalid. Errors are flattened to
    (path, message) pairs for friendly rendering.
    """
    schema = _load_schema()
    validator = Draft202012Validator(schema)
    raw_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    if not raw_errors:
        return ValidationResult(valid=True)

    errors = [
        ValidationError(
            path=".".join(str(p) for p in e.absolute_path),
            message=e.message,
        )
        for e in raw_errors
    ]
    return ValidationResult(valid=False, errors=errors)


def validate_unified_file(path: Path | str) -> ValidationResult:
    """Validate a unified.json file on disk."""
    text = Path(path).read_text()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return ValidationResult(
            valid=False,
            errors=[ValidationError(path="", message=f"Invalid JSON: {e}")],
        )
    return validate_unified(data)


__all__ = ["ValidationError", "ValidationResult", "validate_unified", "validate_unified_file"]
