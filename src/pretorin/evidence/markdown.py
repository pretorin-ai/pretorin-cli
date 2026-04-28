"""Compose the markdown body that auditors see for code/log evidence.

Issue #88. Output shape (capture-mandatory rule):

    <user prose>

    ```<language>
    <redacted snippet>
    ```

    ---
    *Captured from `<path>` [lines <N-M>] [· commit `<short>` [(uncommitted)]]
     · <RFC3339 UTC> [· <redactions>] [· truncated]*

The italic footer is the single visible trace of source provenance for
the auditor. It carries file path, optional line range, optional commit
hash, capture timestamp, and any redaction / truncation summary on one
line under a horizontal rule. Matches the design in the issue body.

The footer is rendered whenever ``source`` carries a path. With no
source and no redactions / truncation it's omitted (composer used as
plain prose+code-block formatter).

No headings anywhere. The footer uses ``*...*`` italics so it doesn't
trip ``validate_audit_markdown``'s no-headings rule.

Composed output is capped at :data:`DESCRIPTION_MAX_BYTES` (16KB,
conservative vs the issue's 64KB guess; revisit when the platform's
actual ``description`` column max is known). When the cap fires, the
snippet body is truncated, a marker comment is appended, and the footer
records ``truncated``. The user prose and footer are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from pretorin.evidence.redact import RedactionSummary

DESCRIPTION_MAX_BYTES: Final[int] = 16 * 1024


_LANGUAGE_BY_SUFFIX: Final[dict[str, str]] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cs": "csharp",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "fish",
    ".ps1": "powershell",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".tf": "hcl",
    ".dockerfile": "dockerfile",
    ".md": "markdown",
    ".log": "text",
}


def language_for_path(path: str | None) -> str:
    """Infer a fenced-code-block language tag from a filename."""
    if not path:
        return "text"
    suffix = Path(path).suffix.lower()
    if suffix:
        return _LANGUAGE_BY_SUFFIX.get(suffix, "text")
    name = Path(path).name.lower()
    if name == "dockerfile":
        return "dockerfile"
    return "text"


@dataclass(frozen=True)
class SourceMeta:
    """Provenance fields for the prelude."""

    path: str
    line_range: str | None = None
    commit: str | None = None
    uncommitted: bool = False  # captured from a working tree with edits


def _short_commit(commit: str | None) -> str | None:
    if not commit:
        return None
    return commit[:7]


def _format_footer(
    source: SourceMeta | None,
    captured_at: datetime | None,
    summary: RedactionSummary,
    *,
    truncated: bool = False,
) -> str | None:
    """Italic single-line footer with source provenance + redaction summary.

    Combines path, line range, commit (short, with optional
    "(uncommitted)" marker), capture timestamp, redaction count, and
    truncation flag into one bullet-separated italic line, beneath a
    horizontal rule.

    Returns ``None`` only when there's nothing to report — no source,
    no redactions, no truncation — so the caller can drop the footer
    entirely.
    """
    parts: list[str] = []

    if source is not None:
        if source.line_range:
            parts.append(f"Captured from `{source.path}` lines {source.line_range}")
        else:
            parts.append(f"Captured from `{source.path}`")
        short = _short_commit(source.commit)
        if short:
            commit_segment = f"commit `{short}`"
            if source.uncommitted:
                commit_segment += " (uncommitted)"
            parts.append(commit_segment)
        ts = (captured_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
        parts.append(ts.strftime("%Y-%m-%dT%H:%M:%SZ"))

    redaction_text = summary.short_form()
    if truncated and redaction_text:
        redaction_text = f"{redaction_text}, truncated"
    elif truncated:
        redaction_text = "truncated"
    if redaction_text:
        parts.append(redaction_text)

    if not parts:
        return None
    return "*" + " · ".join(parts) + "*"


def compose(
    user_description: str,
    snippet: str,
    *,
    language: str,
    source: SourceMeta | None = None,
    redaction: RedactionSummary,
    captured_at: datetime | None = None,
    max_bytes: int = DESCRIPTION_MAX_BYTES,
) -> str:
    """Compose the audit-ready evidence description markdown.

    Args:
        user_description: The author's prose describing what the snippet shows.
        snippet: Redacted source/log content. Must NOT contain unbalanced
            triple-backticks; the snapshot+redact pipeline produces text
            that won't, but composer treats input as opaque.
        language: Fenced-block language tag, e.g. ``"python"``.
        source: Provenance fields rendered into the italic footer.
            When None and there are no redactions/truncation, the
            footer is omitted entirely.
        redaction: Summary of redactions performed during capture.
        captured_at: UTC capture timestamp. Defaults to ``datetime.now(UTC)``.
        max_bytes: Hard cap on the composed output. Truncates the snippet
            body (preserving prose + footer) when exceeded.

    Returns:
        Markdown text suitable for ``description`` on an evidence record.
    """
    ts = captured_at or datetime.now(timezone.utc)
    body = (user_description or "").rstrip()

    fence = "```"
    code_block_template = f"\n\n{fence}{language}\n{{}}\n{fence}\n"

    def _assemble(snippet_body: str, *, truncated: bool) -> str:
        footer = _format_footer(source, ts, redaction, truncated=truncated)
        out = f"{body}{code_block_template.format(snippet_body)}"
        if footer is not None:
            out += f"\n---\n{footer}\n"
        return out

    composed_no_truncation = _assemble(snippet, truncated=False)
    if len(composed_no_truncation.encode("utf-8")) <= max_bytes:
        return composed_no_truncation

    truncated_marker = "\n# ... truncated, see source for full content"
    scaffold = _assemble("", truncated=True)
    overhead = len(scaffold.encode("utf-8"))
    budget = max_bytes - overhead - len(truncated_marker.encode("utf-8"))
    if budget <= 0:
        return _assemble(truncated_marker.lstrip(), truncated=True)

    snippet_bytes = snippet.encode("utf-8")
    truncated_snippet_bytes = snippet_bytes[:budget]
    # Avoid splitting a multi-byte UTF-8 codepoint at the boundary.
    truncated_snippet = truncated_snippet_bytes.decode("utf-8", errors="ignore")
    # Drop a partial trailing line so the truncation marker is on its own line.
    if "\n" in truncated_snippet:
        truncated_snippet = truncated_snippet.rsplit("\n", 1)[0] + "\n"
    return _assemble(truncated_snippet + truncated_marker.lstrip(), truncated=True)
