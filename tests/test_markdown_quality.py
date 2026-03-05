"""Tests for markdown quality guardrails."""

from __future__ import annotations

import pytest

from pretorin.workflows.markdown_quality import ensure_audit_markdown, validate_audit_markdown


def test_validate_narrative_markdown_accepts_rich_headerless_content() -> None:
    content = (
        "- Control objective is enforced through RBAC and SSO mappings.\n"
        "- Access requests require approval in ticket workflow.\n\n"
        "| Evidence | Location |\n"
        "| --- | --- |\n"
        "| RBAC policy | [rbac.yaml](https://example.com/rbac.yaml) |\n"
    )
    result = validate_audit_markdown(content, artifact_type="narrative")
    assert result.is_valid is True


def test_validate_narrative_markdown_rejects_headings() -> None:
    result = validate_audit_markdown("# Heading\n\n- item", artifact_type="narrative")
    assert result.is_valid is False
    assert any("headings are not allowed" in err for err in result.errors)


def test_validate_narrative_markdown_requires_structural_elements() -> None:
    result = validate_audit_markdown(
        "[runbook](https://example.com/runbook)\n\n![diag](https://example.com/diagram.png)",
        artifact_type="narrative",
    )
    assert result.is_valid is False
    assert any("structural element" in err for err in result.errors)


def test_validate_markdown_rejects_images() -> None:
    result = validate_audit_markdown(
        "![diag](https://example.com/diagram.png)\n\n- supporting bullet",
        artifact_type="evidence_description",
    )
    assert result.is_valid is False
    assert any("image markdown is not allowed" in err for err in result.errors)


def test_validate_evidence_markdown_accepts_single_rich_element() -> None:
    result = validate_audit_markdown("- Verified in deployment pipeline logs", artifact_type="evidence_description")
    assert result.is_valid is True


def test_ensure_audit_markdown_raises_for_plain_text_evidence() -> None:
    with pytest.raises(ValueError):
        ensure_audit_markdown("Plain evidence description", artifact_type="evidence_description")
