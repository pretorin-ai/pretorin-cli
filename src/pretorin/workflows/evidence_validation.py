"""Validate code references in evidence before sending to platform.

Shared by campaign apply and recipe execution to ensure agent-reported
file paths and line numbers are real. Issue #88 (post-rework
2026-04-27): the file content is read, run through the same redaction
pipeline as CLI capture, and embedded inline in the evidence
``description`` markdown with a ``**Source:**`` prelude. This makes
campaign / agent / MCP write paths produce evidence that passes the
hard rule enforced on ``EvidenceCreate`` / ``EvidenceBatchItemCreate``.

Minimal-change rule: the only behavioral changes for code-snippet-style
evidence are (a) the ``**Source:** ...`` prelude on the description and
(b) the embedded fenced code block. Everything else carries forward —
including the structured ``code_snippet`` API field, which is preserved
(now populated with the *redacted* snippet rather than raw).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _has_fenced_code_block(text: str) -> bool:
    """Cheap regex check matching the validator on the pydantic models."""
    from pretorin.client.models import _FENCED_CODE_BLOCK_RE

    return bool(_FENCED_CODE_BLOCK_RE.search(text))


def enrich_evidence_recommendations(
    recommendations: list[dict[str, Any]],
    working_dir: Path,
) -> list[dict[str, Any]]:
    """Validate code references and embed redacted snippets in descriptions.

    For each recommendation with ``code_file_path``:

    1. Resolve the path under ``working_dir`` and reject traversal.
    2. Read the actual file content for the reported line range (1-indexed).
    3. Run the snippet through ``redact()`` once.
    4. If the AI's description has no fenced code block, ``compose()`` a
       full description with prose + ``**Source:**`` prelude + fenced
       block + redaction footer. Otherwise leave the AI's description
       alone (the pydantic ``EvidenceCreate`` /
       ``EvidenceBatchItemCreate`` validator will auto-prepend the
       prelude downstream).
    5. Set ``rec["code_snippet"]`` to the redacted snippet. The
       structured field stays populated (carries the same content the
       prior behavior did, just redacted now).

    If the reference is invalid (file missing, bad line range, traversal),
    drop *all* code fields so the record passes validation as
    "no code reference at all" rather than failing the hard rule.
    """
    from pretorin.evidence.markdown import SourceMeta, compose, language_for_path
    from pretorin.evidence.redact import redact

    for rec in recommendations:
        file_path_value = rec.get("code_file_path")
        if not file_path_value:
            continue

        resolved = working_dir / file_path_value
        if not resolved.is_file():
            logger.warning(
                "Evidence code_file_path does not exist: %s (resolved: %s); dropping reference",
                file_path_value,
                resolved,
            )
            _drop_code_fields(rec)
            continue

        try:
            resolved = resolved.resolve()
            if not resolved.is_relative_to(working_dir.resolve()):
                logger.warning("Path traversal detected: %s; dropping reference", file_path_value)
                _drop_code_fields(rec)
                continue
        except (OSError, ValueError):
            _drop_code_fields(rec)
            continue

        line_range = rec.get("code_line_numbers")
        snippet_text = _read_snippet(resolved, line_range)
        if snippet_text is None:
            # Invalid line range against the actual file — drop the line
            # reference but keep the file path for the prelude.
            line_range = None
            try:
                snippet_text = resolved.read_text(errors="replace")
            except OSError:
                logger.warning("Could not read file: %s; dropping reference", resolved)
                _drop_code_fields(rec)
                continue

        redacted_snippet, redaction_summary = redact(snippet_text, pii=False, redact_secrets=True)

        original_description = str(rec.get("description") or "")
        if not _has_fenced_code_block(original_description):
            rec["description"] = compose(
                original_description,
                redacted_snippet,
                language=language_for_path(str(file_path_value)),
                source=SourceMeta(
                    path=str(file_path_value),
                    line_range=line_range,
                    commit=rec.get("code_commit_hash"),
                ),
                redaction=redaction_summary,
                captured_at=datetime.now(timezone.utc),
            )

        # Preserve the structured field (was the original behavior),
        # but with the redacted content rather than raw.
        rec["code_snippet"] = redacted_snippet
        if line_range is None:
            rec.pop("code_line_numbers", None)

    return recommendations


def _read_snippet(resolved_path: Path, line_range: str | None) -> str | None:
    """Read the file slice corresponding to ``line_range``.

    Returns the full file content when ``line_range`` is None, the slice
    when it parses cleanly, or None when the range is malformed or
    out-of-bounds (caller falls back to whole-file).
    """
    try:
        content = resolved_path.read_text(errors="replace")
    except OSError:
        return None

    if not line_range:
        return content

    start, end = _parse_line_range(line_range)
    if start is None or end is None:
        return None

    lines = content.splitlines()
    if end > len(lines):
        return None

    return "\n".join(lines[start - 1 : end])


def _drop_code_fields(rec: dict[str, Any]) -> None:
    rec.pop("code_file_path", None)
    rec.pop("code_line_numbers", None)
    rec.pop("code_snippet", None)


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


# Backward-compat shim: a few code paths and tests still import the older
# `validate_code_reference`/`MAX_SNIPPET_BYTES` symbols. Keep thin
# wrappers so that import surface doesn't change behavior unrelated to
# the campaign-apply fix.

MAX_SNIPPET_BYTES = 50 * 1024


def validate_code_reference(
    code_file_path: str | None,
    code_line_numbers: str | None,
    working_dir: Path,
) -> dict[str, Any] | None:
    """Legacy helper kept for callers outside campaign apply.

    Returns a dict shaped like ``EvidenceCodeContext`` (without the
    ``code_snippet`` field — Q2). Returns None when the reference is
    invalid.
    """
    if not code_file_path:
        return None

    resolved = working_dir / code_file_path
    if not resolved.is_file():
        return None

    try:
        resolved = resolved.resolve()
        if not resolved.is_relative_to(working_dir.resolve()):
            return None
    except (OSError, ValueError):
        return None

    context: dict[str, Any] = {"code_file_path": code_file_path}
    if code_line_numbers:
        start, end = _parse_line_range(code_line_numbers)
        if start is not None and end is not None:
            context["code_line_numbers"] = code_line_numbers
    return context
