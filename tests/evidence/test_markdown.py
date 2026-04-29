"""Tests for evidence/markdown.py — snippet + provenance footer composer."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from pretorin.evidence.markdown import compose
from pretorin.evidence.redact import RedactionResult

_FIXED_TIME = datetime(2026, 4, 29, 14, 30, 0, tzinfo=timezone.utc)


def test_compose_just_snippet_no_footer() -> None:
    """No source_path → just a fenced snippet, no horizontal rule, no footer."""
    body = compose(snippet="x = 1\ny = 2\n", language="python")
    assert "```python" in body
    assert "x = 1" in body
    assert "---" not in body
    assert "Captured from" not in body


def test_compose_with_user_prose() -> None:
    body = compose(
        user_prose="Authentication module enforces MFA.",
        snippet="def require_mfa(): pass",
        language="python",
    )
    assert body.startswith("Authentication module enforces MFA.")
    assert "```python" in body


def test_compose_renders_footer_when_source_path_given() -> None:
    body = compose(
        snippet="...",
        source_path="src/auth/mfa.py",
        captured_at=_FIXED_TIME,
    )
    assert "---" in body
    assert "Captured from `src/auth/mfa.py`" in body
    assert "2026-04-29T14:30:00+00:00" in body


def test_compose_footer_includes_line_range() -> None:
    body = compose(
        snippet="...",
        source_path="src/x.py",
        line_range="42-67",
        captured_at=_FIXED_TIME,
    )
    assert "lines 42-67" in body


def test_compose_footer_truncates_commit_hash() -> None:
    body = compose(
        snippet="...",
        source_path="src/x.py",
        commit_hash="abc1234567890def",
        captured_at=_FIXED_TIME,
    )
    assert "commit `abc1234`" in body
    # Full 16-char hash should NOT appear.
    assert "abc1234567890def" not in body


def test_compose_footer_uncommitted_marker() -> None:
    body = compose(
        snippet="...",
        source_path="src/x.py",
        commit_hash="abc1234",
        is_uncommitted=True,
        captured_at=_FIXED_TIME,
    )
    assert "(uncommitted)" in body


def test_compose_footer_redaction_short_form() -> None:
    redaction = RedactionResult(counts=Counter({"aws_access_key": 1, "github_token": 2}))
    body = compose(
        snippet="...",
        source_path="src/x.py",
        captured_at=_FIXED_TIME,
        redaction=redaction,
    )
    assert "3 secrets redacted" in body


def test_compose_footer_omits_empty_redaction() -> None:
    """RedactionResult with zero matches doesn't add a redaction segment."""
    redaction = RedactionResult()
    body = compose(
        snippet="...",
        source_path="src/x.py",
        captured_at=_FIXED_TIME,
        redaction=redaction,
    )
    assert "redacted" not in body


def test_compose_full_footer() -> None:
    """All optional fields present produce the canonical full-line footer."""
    redaction = RedactionResult(counts=Counter({"password": 1}))
    body = compose(
        user_prose="Auth flow.",
        snippet="def x(): pass",
        language="python",
        source_path="src/auth.py",
        line_range="42-67",
        commit_hash="deadbeef1234",
        is_uncommitted=False,
        captured_at=_FIXED_TIME,
        redaction=redaction,
    )
    # Footer is one italic line, separated by ` · `, after a `---` rule.
    expected_footer = (
        "*Captured from `src/auth.py` · lines 42-67 · commit `deadbee` · 2026-04-29T14:30:00+00:00 · 1 secret redacted*"
    )
    assert expected_footer in body


def test_compose_default_captured_at_is_now_utc() -> None:
    """Without explicit captured_at, footer uses datetime.now(UTC)."""
    body = compose(snippet="...", source_path="src/x.py")
    # Just assert the timezone +00:00 appears in the footer; we don't pin the
    # exact timestamp.
    assert "+00:00" in body


def test_compose_strips_trailing_newlines_from_snippet() -> None:
    body = compose(snippet="x = 1\n\n\n", language="python")
    # Fence closer should immediately follow the last content line, not be
    # pushed down by trailing newlines.
    assert "x = 1\n```\n" in body
