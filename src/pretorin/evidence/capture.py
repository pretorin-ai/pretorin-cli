"""Orchestrate snapshot → redact → markdown for the CLI capture flow.

Issue #88. The CLI calls :func:`capture_code` or :func:`capture_log` to
turn a `--code-file` / `--log-file` plus the user prose into the final
``description`` markdown that gets pushed to the platform. Splitting
this out of the CLI command keeps the typer entry-point shallow and
the orchestration unit-testable.

Decision Q2 (eng review 2026-04-27): the redacted snippet lives ONLY in
the composed ``description`` markdown. The structured ``code_snippet``
API field stays empty for the new feature.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from pretorin.evidence.env_resolve import EnvSummary, resolve_from_text
from pretorin.evidence.markdown import SourceMeta, compose, language_for_path
from pretorin.evidence.redact import redact
from pretorin.evidence.snapshot import (
    CodeSnapshot,
    LogSnapshot,
    read_code,
    read_log,
)
from pretorin.evidence.symbol_resolve import SymbolSummary, resolve_symbols

logger = logging.getLogger(__name__)


def _has_uncommitted_changes(path: str) -> bool:
    """Best-effort check: does the working tree differ from HEAD for ``path``?

    Returns False on any git error so the footer never lies. Uses a tight
    timeout so a misconfigured git environment doesn't hang the CLI.
    """
    if not shutil.which("git"):
        return False
    p = Path(path)
    cwd = p.parent if p.is_absolute() else Path.cwd()
    try:
        result = subprocess.run(
            ["git", "diff", "--quiet", "HEAD", "--", str(path)],
            cwd=cwd,
            timeout=2,
            capture_output=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    # `git diff --quiet` returns 0 when no diff, 1 when diff present.
    return result.returncode == 1


def capture_code(
    *,
    user_description: str,
    file_path: str,
    line_range: str | None,
    repository: str | None,
    commit: str | None,
    redact_pii: bool,
    redact_secrets: bool,
    resolve_env: bool = True,
    trace_defs: bool = True,
) -> str:
    """Read, redact, and compose a ``description`` for ``--code-file`` capture.

    Returns the composed markdown. Raises :class:`SnapshotError` (re-raised
    from :mod:`snapshot`) when the file can't be captured.

    When ``resolve_env`` is True (the default), env-var references in
    the snippet are resolved against the calling process's
    ``os.environ`` and rendered into the unified variable table.
    Tier-2 value redaction runs *independently* of ``redact_secrets``
    so a confirmed ``--no-redact`` snippet never leaks credentials out
    of resolved env values.

    When ``trace_defs`` is True (the default), Python module-constant
    references in the snippet are traced to their definition files in
    the captured file's git repo. Each found definition gets its own
    fenced code block embedded after the original snippet. Tier-1 / tier-2
    redaction runs on each definition slice. Symbol tracing soft-fails
    on any error so a malformed snippet or a slow filesystem never
    aborts the user's evidence write.
    """
    snap: CodeSnapshot = read_code(file_path, line_range)
    language = language_for_path(file_path)
    env_summary: EnvSummary | None = None
    if resolve_env:
        env_summary = resolve_from_text(snap.text, language)
    symbol_summary: SymbolSummary | None = None
    if trace_defs:
        try:
            symbol_summary = resolve_symbols(snap.text, language, file_path)
        except Exception as exc:  # pragma: no cover — defensive; module already soft-fails
            logger.warning("evidence.capture.symbol_resolve_failed", extra={"error": str(exc)})
            symbol_summary = None
    redacted, summary = redact(snap.text, pii=redact_pii, redact_secrets=redact_secrets)
    source = SourceMeta(
        path=file_path,
        line_range=snap.line_range,
        commit=commit,
        uncommitted=bool(commit) and _has_uncommitted_changes(file_path),
    )
    return compose(
        user_description,
        redacted,
        language=language,
        source=source,
        redaction=summary,
        env_summary=env_summary,
        symbols=symbol_summary,
    )


def capture_log(
    *,
    user_description: str,
    file_path: str,
    tail: int | None,
    since: str | None,
    redact_pii: bool,
    redact_secrets: bool,
) -> str:
    """Read, redact, and compose a ``description`` for ``--log-file`` capture.

    PII redaction defaults to ON for logs (caller passes the resolved value).
    """
    snap: LogSnapshot = read_log(file_path, tail=tail, since=since)
    redacted, summary = redact(snap.text, pii=redact_pii, redact_secrets=redact_secrets)
    source = SourceMeta(
        path=file_path,
        line_range=f"last {snap.line_count} lines" if tail is not None else None,
    )
    return compose(
        user_description,
        redacted,
        language=language_for_path(file_path),
        source=source,
        redaction=summary,
    )
