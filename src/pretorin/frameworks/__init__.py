"""Custom framework authoring: build, validate, and convert unified.json artifacts.

This module wraps the platform's framework revision lifecycle. The canonical
upload artifact is `unified.json` — the same format used by the monorepo's
control-data pipeline. `_index.json` is NOT an upload format.

Public surface:
    validate.validate_unified(data) -> ValidationResult
    oscal_to_unified.convert(oscal_catalog, framework_id) -> dict
    unified_to_oscal.convert(unified, framework_id) -> dict
    custom_to_unified.convert(catalog, framework_id) -> dict
    templates.minimal_unified(framework_id, title) -> dict
"""
