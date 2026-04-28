"""Compose the markdown body that auditors see for code/log evidence.

Issue #88 (capture-mandatory rule) + #92 (env-var resolution +
cross-file symbol tracing + unified variable table), all shipping
in 0.17.0.

Output shape (capture-mandatory rule):

    <user prose>

    ```<language>
    <redacted original snippet>
    ```

    [```<language>                        ← one fence per traced definition
    # <relative_path>:<line>
    <redacted definition slice>
    ```
    ...]

    [| Variable | Value | Source |        ← unified table when refs exist
     |---|---|---|
     | `NAME`         | `value`                | env / inline / path:line / "—" |
     ...]

    ---
    *Captured from `<path>` [lines <N-M>] [· commit `<short>` [(uncommitted)]]
     · <RFC3339 UTC> [· <redactions>] [· <env counts>] [· <symbol counts>]
     [· truncated]*

The italic footer is the single visible trace of source provenance for
the auditor. It carries file path, optional line range, optional commit
hash, capture timestamp, and any redaction / env-resolution /
symbol-tracing / truncation summary on one line under a horizontal
rule.

The footer is rendered whenever ``source`` carries a path. With no
source and no redactions / truncation it's omitted (composer used as
plain prose+code-block formatter).

The unified **Variable** table replaces the earlier bullet list. It
merges env-var references (resolved against the local process env or
inline definition) with cross-file symbol references (resolved by
walking the captured file's git repo). One row per detected variable,
with a Source column distinguishing where the value came from. The
table is preserved across truncation: the original snippet truncates
first, then any definition snippets, then the table.

No headings anywhere. The footer uses ``*...*`` italics so it doesn't
trip ``validate_audit_markdown``'s no-headings rule.

Composed output is capped at :data:`DESCRIPTION_MAX_BYTES` (16KB,
conservative vs the issue's 64KB guess; revisit when the platform's
actual ``description`` column max is known). When the cap fires, the
snippet body is truncated, a marker comment is appended, and the footer
records ``truncated``. The user prose, definition snippets (best
effort), variable table, and footer are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

from pretorin.evidence.env_resolve import EnvSummary
from pretorin.evidence.redact import RedactionSummary
from pretorin.evidence.symbol_resolve import Definition, SymbolSummary

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
    env_summary: EnvSummary | None = None,
    symbols: SymbolSummary | None = None,
    *,
    truncated: bool = False,
) -> str | None:
    """Italic single-line footer with source provenance + redaction summary.

    Combines path, line range, commit (short, with optional
    "(uncommitted)" marker), capture timestamp, redaction count, env
    resolution counts, symbol-tracing counts, and truncation flag into
    one bullet-separated italic line, beneath a horizontal rule.

    Returns ``None`` only when there's nothing to report.
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
    if redaction_text:
        parts.append(redaction_text)

    if env_summary is not None:
        env_text = env_summary.short_form()
        if env_text:
            parts.append(env_text)

    if symbols is not None:
        sym_text = symbols.short_form()
        if sym_text:
            parts.append(sym_text)

    if truncated:
        parts.append("truncated")

    if not parts:
        return None
    return "*" + " · ".join(parts) + "*"


# --- Definition snippet + variable table rendering --------------------------


_TABLE_VALUE_DISPLAY_CAP: Final[int] = 200


def _escape_pipe(s: str) -> str:
    """Escape pipe chars so a value doesn't break the markdown table row."""
    return s.replace("|", "\\|")


def _flatten_newlines(s: str) -> str:
    """Replace any newline form with a single space.

    Multi-line values (PEM blocks, heredocs, anything with embedded
    ``\\n``) would otherwise produce a literal multi-line cell, which
    most markdown renderers interpret as table-end. Flatten so the row
    stays one line; the auditor sees the original via the snippet
    fence above the table.
    """
    return s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def _truncate_value(s: str, cap: int = _TABLE_VALUE_DISPLAY_CAP) -> str:
    if len(s) <= cap:
        return s
    return s[: cap - 1] + "…"


def _wrap_code(s: str) -> str:
    """Wrap a value in backticks for a markdown code span.

    When the value itself contains a backtick, switch to a double-
    backtick wrapper (CommonMark allows this and is the canonical
    escape). Pads single space on each side so the inner backtick
    isn't adjacent to the wrapper backticks.
    """
    if "`" in s:
        return f"`` {s} ``"
    return f"`{s}`"


def _format_table_value(s: str) -> str:
    """Apply the full pipeline to a value before it enters a table cell."""
    return _wrap_code(_truncate_value(_escape_pipe(_flatten_newlines(s))))


def _render_definitions(
    definitions: list[Definition],
    language: str,
) -> str:
    """Render one fenced code block per traced definition.

    Each fence carries a ``# <path>:<line>`` header so the auditor can
    jump to the source. The slice itself is already redacted (handled
    in :mod:`symbol_resolve`).
    """
    if not definitions:
        return ""
    fence = "```"
    blocks: list[str] = []
    for d in definitions:
        body = d.snippet.rstrip("\n")
        header = f"# {d.file_path}:{d.line}"
        blocks.append(f"\n\n{fence}{language}\n{header}\n{body}\n{fence}\n")
    return "".join(blocks)


def _render_variable_table(
    env_summary: EnvSummary | None,
    symbols: SymbolSummary | None,
) -> str:
    """Merge env vars and traced symbols into one markdown table.

    Columns: Variable, Value, Source. Returns an empty string when
    there's nothing to show.
    """
    rows: list[tuple[str, str, str]] = []  # (name, value, source)

    rendered_names: set[str] = set()

    # Symbols are added FIRST when present so a name with both an env-var
    # reference and a cross-file definition prefers the symbol entry —
    # the file:line source location is more informative than "env".
    if symbols is not None:
        for d in symbols.definitions:
            if d.name in rendered_names:
                continue
            rendered_names.add(d.name)
            value = _format_table_value(d.value) if d.value else "`<no value>`"
            rows.append((d.name, value, f"`{d.file_path}:{d.line}`"))
        for n in symbols.not_found:
            if n in rendered_names:
                continue
            rendered_names.add(n)
            rows.append((n, "`<not found>`", "—"))

    if env_summary is not None:
        for ref in env_summary.refs:
            if ref.name in rendered_names:
                continue
            rendered_names.add(ref.name)
            if ref.redacted_kind is not None:
                value = f"`[REDACTED:{ref.redacted_kind}]`"
            elif ref.is_unset:
                value = "`<unset>`"
            elif ref.value is not None:
                value = _format_table_value(ref.value)
            else:
                value = "`<unset>`"
            if ref.from_inline:
                source = "inline"
            elif ref.used_default:
                source = "default"
            elif ref.is_unset:
                source = "—"
            else:
                source = "env"
            rows.append((ref.name, value, source))

    if not rows:
        return ""

    lines = [
        "| Variable | Value | Source |",
        "|---|---|---|",
    ]
    for name, value, source in rows:
        lines.append(f"| `{_escape_pipe(name)}` | {value} | {source} |")
    return "\n".join(lines)


def compose(
    user_description: str,
    snippet: str,
    *,
    language: str,
    source: SourceMeta | None = None,
    redaction: RedactionSummary,
    env_summary: EnvSummary | None = None,
    symbols: SymbolSummary | None = None,
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
        redaction: Summary of redactions performed during capture.
        env_summary: Optional resolved env-var references — merged with
            ``symbols`` into the unified variable table at the bottom.
        symbols: Optional cross-file symbol-tracing summary. Each
            successfully-resolved definition gets its own fenced block
            after the original snippet; all references (resolved or
            not) feed into the variable table.
        captured_at: UTC capture timestamp. Defaults to ``datetime.now(UTC)``.
        max_bytes: Hard cap on the composed output. Truncation order:
            original snippet body first, definition snippets second,
            variable table preserved.

    Returns:
        Markdown text suitable for ``description`` on an evidence record.
    """
    ts = captured_at or datetime.now(timezone.utc)
    body = (user_description or "").rstrip()

    definitions_block = _render_definitions(
        symbols.definitions if symbols is not None else [],
        language,
    )
    table_block = _render_variable_table(env_summary, symbols)

    fence = "```"
    code_block_template = f"\n\n{fence}{language}\n{{}}\n{fence}\n"

    def _assemble(
        snippet_body: str,
        defs_block: str,
        *,
        truncated: bool,
    ) -> str:
        footer = _format_footer(source, ts, redaction, env_summary, symbols, truncated=truncated)
        out = f"{body}{code_block_template.format(snippet_body)}"
        if defs_block:
            out += defs_block
        if table_block:
            out += f"\n{table_block}\n"
        if footer is not None:
            out += f"\n---\n{footer}\n"
        return out

    composed_no_truncation = _assemble(snippet, definitions_block, truncated=False)
    if len(composed_no_truncation.encode("utf-8")) <= max_bytes:
        return composed_no_truncation

    truncated_marker = "\n# ... truncated, see source for full content"

    # Truncation strategy: keep the table (densest compliance signal),
    # then preserve definition snippets where possible, then truncate
    # the original snippet body to fit.
    #
    # Pass 1: try with full definitions block. If the snippet fits with
    # that overhead, render it.
    scaffold_full_defs = _assemble("", definitions_block, truncated=True)
    overhead_full_defs = len(scaffold_full_defs.encode("utf-8"))
    budget_full_defs = max_bytes - overhead_full_defs - len(truncated_marker.encode("utf-8"))
    if budget_full_defs > 0:
        truncated_snippet = _slice_to_budget(snippet, budget_full_defs)
        return _assemble(
            truncated_snippet + truncated_marker.lstrip(),
            definitions_block,
            truncated=True,
        )

    # Pass 2: the definitions block alone is too big. Drop definitions
    # progressively from the end (latest defs lose first) until we have
    # room for at least the truncated marker.
    if symbols is not None and symbols.definitions:
        defs = list(symbols.definitions)
        while defs:
            defs.pop()
            partial_block = _render_definitions(defs, language)
            scaffold = _assemble("", partial_block, truncated=True)
            overhead = len(scaffold.encode("utf-8"))
            budget = max_bytes - overhead - len(truncated_marker.encode("utf-8"))
            if budget > 0:
                truncated_snippet = _slice_to_budget(snippet, budget)
                return _assemble(
                    truncated_snippet + truncated_marker.lstrip(),
                    partial_block,
                    truncated=True,
                )

    # Pass 3: even the table + footer alone don't fit (extremely small
    # max_bytes). Fall back to the bare-bones marker.
    return _assemble(truncated_marker.lstrip(), "", truncated=True)


def _slice_to_budget(snippet: str, budget: int) -> str:
    """UTF-8-safe truncation that drops a trailing partial line.

    Shared between the truncation passes above so the slicing stays in
    one place.
    """
    snippet_bytes = snippet.encode("utf-8")
    truncated_bytes = snippet_bytes[:budget]
    truncated = truncated_bytes.decode("utf-8", errors="ignore")
    if "\n" in truncated:
        truncated = truncated.rsplit("\n", 1)[0] + "\n"
    return truncated
