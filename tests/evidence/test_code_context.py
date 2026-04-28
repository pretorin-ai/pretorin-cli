"""Tests for pretorin.evidence.code_context."""

from __future__ import annotations

from pretorin.evidence.code_context import build_code_context


def test_empty():
    assert build_code_context() == {}


def test_only_populated_keys():
    ctx = build_code_context(code_file_path="app/auth.py", code_line_numbers="12-30")
    assert ctx == {"code_file_path": "app/auth.py", "code_line_numbers": "12-30"}


def test_none_skipped():
    ctx = build_code_context(code_file_path="x.py", code_repository=None, code_commit_hash=None)
    assert "code_repository" not in ctx
    assert "code_commit_hash" not in ctx


def test_empty_string_skipped():
    """Empty strings should be treated as missing — the platform's idempotency
    key includes these fields and we don't want '' to be a distinct value."""
    ctx = build_code_context(code_file_path="", code_snippet="")
    assert ctx == {}


def test_full_payload():
    ctx = build_code_context(
        code_file_path="x.py",
        code_line_numbers="1-5",
        code_snippet="def f(): pass",
        code_repository="https://github.com/foo/bar",
        code_commit_hash="abc1234",
    )
    assert set(ctx.keys()) == {
        "code_file_path",
        "code_line_numbers",
        "code_snippet",
        "code_repository",
        "code_commit_hash",
    }
