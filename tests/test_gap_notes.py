"""Tests for the shared gap-note format used by skill prompts and the apply pipeline."""

from __future__ import annotations

from pretorin.workflows.gap_notes import GAP_NOTE_TEMPLATE, synthesize_gap_note


def test_template_exposes_all_five_labels() -> None:
    for label in ("Gap:", "Observed:", "Missing:", "Why missing:", "Manual next step:"):
        assert label in GAP_NOTE_TEMPLATE


def test_synthesize_fills_every_section() -> None:
    rec = {
        "name": "SSO metadata",
        "description": "Describe IdP federation metadata",
        "evidence_type": "configuration",
    }
    note = synthesize_gap_note(rec, reason="IdP not connected to MCP")

    assert note.startswith("Gap: SSO metadata")
    assert "Observed:" in note
    assert "configuration" in note
    assert "IdP not connected to MCP" in note
    assert "Manual next step:" in note


def test_synthesize_with_missing_name_uses_fallback() -> None:
    note = synthesize_gap_note({"description": "orphan rec"}, reason="AI did not specify an evidence_type")
    assert "Gap: AI-drafted evidence (rejected)" in note
    assert "AI did not specify an evidence_type" in note


def test_synthesize_tolerates_non_dict() -> None:
    # `rec` should never be non-dict in practice, but the helper must not crash.
    note = synthesize_gap_note({}, reason="malformed recommendation")
    assert "Gap: AI-drafted evidence (rejected)" in note
    assert "malformed recommendation" in note


def test_synthesize_empty_strings_use_defaults() -> None:
    note = synthesize_gap_note(
        {"name": "   ", "description": "", "evidence_type": None},
        reason="blank fields",
    )
    assert "Gap: AI-drafted evidence (rejected)" in note
    assert "(no description provided)" in note
