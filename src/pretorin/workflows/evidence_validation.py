"""Validate code references in evidence before sending to platform.

Shared by campaign apply and recipe execution to ensure agent-reported
file paths and line numbers are real. The actual file content at the
reported lines becomes the canonical code_snippet.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pretorin.client.models import EvidenceCodeContext

logger = logging.getLogger(__name__)

# Snippets larger than this are truncated with a suffix.
MAX_SNIPPET_BYTES = 50 * 1024  # 50 KB


def validate_code_reference(
    code_file_path: str | None,
    code_line_numbers: str | None,
    working_dir: Path,
) -> EvidenceCodeContext | None:
    """Validate and enrich a code reference from an AI-reported evidence item.

    - Checks that the file exists at ``working_dir / code_file_path``.
    - Parses ``code_line_numbers`` as "N-M" and checks the range is valid.
    - Reads the actual file content at those lines as the canonical snippet.
    - Returns None if the reference is invalid (file missing, bad line range).
    - Truncates the snippet if it exceeds MAX_SNIPPET_BYTES.
    """
    if not code_file_path:
        return None

    resolved = working_dir / code_file_path
    if not resolved.is_file():
        logger.warning(
            "Evidence code_file_path does not exist: %s (resolved: %s)",
            code_file_path,
            resolved,
        )
        return None

    # Resolve to prevent traversal outside working_dir
    try:
        resolved = resolved.resolve()
        if not resolved.is_relative_to(working_dir.resolve()):
            logger.warning("Path traversal detected: %s", code_file_path)
            return None
    except (OSError, ValueError):
        return None

    context: EvidenceCodeContext = {"code_file_path": code_file_path}

    if code_line_numbers:
        start, end = _parse_line_range(code_line_numbers)
        if start is not None and end is not None:
            try:
                lines = resolved.read_text(errors="replace").splitlines()
            except OSError:
                logger.warning("Could not read file: %s", resolved)
                return context

            if end > len(lines):
                logger.warning(
                    "Line range %s exceeds file length (%d lines): %s",
                    code_line_numbers,
                    len(lines),
                    code_file_path,
                )
                # Drop the line reference but keep the file path
                return context

            # Extract actual content (1-indexed)
            snippet_lines = lines[start - 1 : end]
            snippet = "\n".join(snippet_lines)

            if len(snippet.encode("utf-8")) > MAX_SNIPPET_BYTES:
                truncated = snippet.encode("utf-8")[:MAX_SNIPPET_BYTES].decode("utf-8", errors="ignore")
                snippet = truncated + f"\n[TRUNCATED — full file: {code_file_path}]"

            context["code_line_numbers"] = code_line_numbers
            context["code_snippet"] = snippet
        else:
            logger.warning("Invalid line range format: %s", code_line_numbers)

    return context


def enrich_evidence_recommendations(
    recommendations: list[dict[str, Any]],
    working_dir: Path,
) -> list[dict[str, Any]]:
    """Validate and enrich code references in a list of evidence recommendations.

    For each recommendation with code_file_path, validates the reference and
    replaces the agent's snippet with the actual file content. Returns the
    modified list (mutates in place for efficiency).
    """
    for rec in recommendations:
        file_path = rec.get("code_file_path")
        if not file_path:
            continue

        validated = validate_code_reference(
            code_file_path=file_path,
            code_line_numbers=rec.get("code_line_numbers"),
            working_dir=working_dir,
        )

        if validated is None:
            # Invalid reference — drop all code fields
            rec.pop("code_file_path", None)
            rec.pop("code_line_numbers", None)
            rec.pop("code_snippet", None)
        else:
            # Replace agent-reported values with validated ones
            rec["code_file_path"] = validated.get("code_file_path")
            if "code_line_numbers" in validated:
                rec["code_line_numbers"] = validated["code_line_numbers"]
            else:
                rec.pop("code_line_numbers", None)
            if "code_snippet" in validated:
                rec["code_snippet"] = validated["code_snippet"]
            else:
                rec.pop("code_snippet", None)

    return recommendations


def _parse_line_range(spec: str) -> tuple[int | None, int | None]:
    """Parse a line range like '42-67' into (start, end). Both 1-indexed."""
    spec = spec.strip()
    if "-" in spec:
        parts = spec.split("-", 1)
        try:
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            if start < 1 or end < start:
                return None, None
            return start, end
        except ValueError:
            return None, None
    else:
        try:
            line = int(spec)
            return line, line
        except ValueError:
            return None, None
