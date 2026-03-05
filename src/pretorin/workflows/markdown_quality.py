"""Markdown quality checks for auditor-friendly compliance artifacts."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

ArtifactType = Literal["narrative", "evidence_description"]

_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+\S", re.MULTILINE)
_FENCED_CODE_RE = re.compile(r"```[\s\S]*?```")
_TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\s*\|.+\|\s*$", re.MULTILINE)
_LIST_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+\S", re.MULTILINE)
_IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
_LINK_RE = re.compile(r"(?<!!)\[[^\]]+]\([^)]+\)")

_RICH_ELEMENTS = ("code_block", "table", "list", "link")
_STRUCTURAL_ELEMENTS = {"code_block", "table", "list"}


@dataclass
class MarkdownValidationResult:
    """Validation result for audit markdown rules."""

    artifact_type: ArtifactType
    errors: list[str] = field(default_factory=list)
    rich_elements: list[str] = field(default_factory=list)
    heading_count: int = 0

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def error_message(self) -> str:
        prefix = "Narrative" if self.artifact_type == "narrative" else "Evidence description"
        return f"{prefix} markdown requirements failed: " + "; ".join(self.errors)


def _detect_rich_elements(content: str) -> list[str]:
    elements: list[str] = []
    if _FENCED_CODE_RE.search(content):
        elements.append("code_block")
    if _TABLE_SEPARATOR_RE.search(content) or len(_TABLE_ROW_RE.findall(content)) >= 2:
        elements.append("table")
    if _LIST_RE.search(content):
        elements.append("list")
    if _LINK_RE.search(content):
        elements.append("link")
    return elements


def validate_audit_markdown(content: str, artifact_type: ArtifactType) -> MarkdownValidationResult:
    """Validate markdown style for human-readable audit artifacts."""
    result = MarkdownValidationResult(artifact_type=artifact_type)
    text = content.strip()
    if not text:
        result.errors.append("content is empty")
        return result

    result.heading_count = len(_HEADING_RE.findall(text))
    if result.heading_count:
        result.errors.append("markdown headings are not allowed; use lists, tables, code blocks, and links")

    if _IMAGE_RE.search(text):
        result.errors.append("image markdown is not allowed until platform evidence upload support is enabled")

    result.rich_elements = _detect_rich_elements(text)
    min_rich = 2 if artifact_type == "narrative" else 1
    if len(result.rich_elements) < min_rich:
        needed = (
            "at least two rich markdown elements"
            if artifact_type == "narrative"
            else "at least one rich markdown element"
        )
        result.errors.append(
            f"{needed} required ({', '.join(_RICH_ELEMENTS)}); found {len(result.rich_elements)}"
        )

    if artifact_type == "narrative" and not _STRUCTURAL_ELEMENTS.intersection(result.rich_elements):
        result.errors.append("narratives must include at least one structural element (code_block, table, or list)")

    return result


def ensure_audit_markdown(content: str, artifact_type: ArtifactType) -> None:
    """Raise ValueError when markdown does not meet audit quality rules."""
    result = validate_audit_markdown(content, artifact_type)
    if not result.is_valid:
        raise ValueError(result.error_message())
