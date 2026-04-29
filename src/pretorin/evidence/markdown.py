"""Compose the markdown body that auditors see for code/log evidence.

Trimmed port of PR #92's markdown.py — kept the snippet + provenance footer
composer; dropped env-resolve, symbol-resolve, and the unified variable
table (out of scope for v1 per the design's WS3 §1, "trim aggressively").

Output shape::

    <user prose>

    ```<language>
    <redacted snippet>
    ```

    ---
    *Captured from `<path>` [lines <N-M>] [· commit `<short>` [(uncommitted)]]
     · <RFC3339 UTC> [· <redaction summary>]*

The italic footer is the single visible trace of source provenance for the
auditor. It carries file path, optional line range, optional commit hash,
capture timestamp, and any redaction summary on one line under a horizontal
rule. Footer is rendered whenever a ``source_path`` is provided; with no
source and no redactions, the composer is just a snippet wrapper.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pretorin.evidence.redact import RedactionResult


def compose(
    *,
    user_prose: str = "",
    snippet: str,
    language: str = "",
    source_path: str | None = None,
    line_range: str | None = None,
    commit_hash: str | None = None,
    is_uncommitted: bool = False,
    captured_at: datetime | None = None,
    redaction: RedactionResult | None = None,
) -> str:
    """Compose evidence body markdown: prose + fenced snippet + provenance footer.

    Args:
        user_prose: Optional preamble text rendered above the code fence.
        snippet: The code/log/config text to include verbatim. Already
            redacted by the caller — this composer does not run redaction.
        language: Fence language tag (``python``, ``yaml``, ``json``, etc.).
            Empty string is fine; just leaves the fence un-tagged.
        source_path: Path or URL the snippet came from. Required for the
            footer to render. None → no footer at all.
        line_range: Optional line range string (``"42-67"``).
        commit_hash: Optional git commit hash. Truncated to 7 chars in the
            footer.
        is_uncommitted: When True, footer shows ``commit X (uncommitted)``
            so the auditor knows the snippet reflects working-tree state.
        captured_at: When the state was actually true. Defaults to now.
        redaction: ``RedactionResult`` from redact() so the footer can
            mention "N secrets redacted". None means no redaction line.

    Returns:
        Composed markdown body as a single string.
    """
    parts: list[str] = []

    if user_prose:
        parts.append(user_prose.rstrip())
        parts.append("")

    fence_tag = language or ""
    parts.append(f"```{fence_tag}")
    parts.append(snippet.rstrip("\n"))
    parts.append("```")

    if source_path:
        parts.append("")
        parts.append("---")
        parts.append(
            _render_footer(
                source_path=source_path,
                line_range=line_range,
                commit_hash=commit_hash,
                is_uncommitted=is_uncommitted,
                captured_at=captured_at if captured_at is not None else datetime.now(timezone.utc),
                redaction=redaction,
            )
        )

    return "\n".join(parts) + "\n"


def _render_footer(
    *,
    source_path: str,
    line_range: str | None,
    commit_hash: str | None,
    is_uncommitted: bool,
    captured_at: datetime,
    redaction: RedactionResult | None,
) -> str:
    """Render the italic one-line provenance footer.

    Format: ``*Captured from `path` [lines N-M] [· commit `abc1234` [(uncommitted)]] · <iso> [· <redactions>]*``
    """
    pieces: list[str] = [f"Captured from `{source_path}`"]
    if line_range:
        pieces.append(f"lines {line_range}")
    if commit_hash:
        short = commit_hash[:7]
        commit_part = f"commit `{short}`"
        if is_uncommitted:
            commit_part += " (uncommitted)"
        pieces.append(commit_part)
    # RFC3339 UTC. Drop microseconds for a cleaner footer.
    pieces.append(captured_at.replace(microsecond=0).isoformat())
    if redaction is not None and redaction.any():
        pieces.append(redaction.short_form())
    return f"*{' · '.join(pieces)}*"


__all__ = ["compose"]
