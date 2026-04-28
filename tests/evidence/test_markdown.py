"""Tests for pretorin.evidence.markdown."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from pretorin.evidence.markdown import (
    DESCRIPTION_MAX_BYTES,
    SourceMeta,
    compose,
    language_for_path,
)
from pretorin.evidence.redact import RedactionSummary

_FIXED_TS = datetime(2026, 4, 27, 18, 32, 11, tzinfo=timezone.utc)


def _summary(**counts: int) -> RedactionSummary:
    s = RedactionSummary()
    for k, v in counts.items():
        s.counts[k] = v
    return s


class TestLanguageForPath:
    @pytest.mark.parametrize(
        "path,lang",
        [
            ("app/auth.py", "python"),
            ("config/db.yaml", "yaml"),
            ("config/db.yml", "yaml"),
            ("infra/main.tf", "hcl"),
            ("frontend/x.tsx", "tsx"),
            ("scripts/run.sh", "bash"),
            ("/var/log/auth.log", "text"),
            ("Dockerfile", "dockerfile"),
            ("unknown.xyz", "text"),
            ("noextension", "text"),
            (None, "text"),
            ("", "text"),
        ],
    )
    def test_inference(self, path, lang):
        assert language_for_path(path) == lang


class TestCompose:
    """Composed shape: prose, fenced block, HR, italic footer with
    source provenance + redaction summary on one line."""

    def test_happy_path(self):
        out = compose(
            "TOTP-based MFA verification used by the login flow.",
            "def verify_mfa(user, code):\n    return True\n",
            language="python",
            source=SourceMeta(path="app/auth.py", line_range="12-14", commit="a1b2c3d456789"),
            redaction=_summary(aws_access_key=1),
            captured_at=_FIXED_TS,
        )
        assert out.startswith("TOTP-based MFA verification")
        assert "```python" in out
        assert "def verify_mfa" in out
        assert "\n---\n" in out
        # Footer line carries everything.
        last_line = [ln for ln in out.splitlines() if ln.strip()][-1]
        assert last_line.startswith("*")
        assert last_line.endswith("*")
        assert "Captured from `app/auth.py` lines 12-14" in last_line
        assert "commit `a1b2c3d`" in last_line  # short hash
        assert "2026-04-27T18:32:11Z" in last_line
        assert "1 secret redacted" in last_line

    def test_no_source_no_redaction_drops_footer(self):
        out = compose(
            "prose",
            "x = 1",
            language="python",
            source=None,
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        assert "Captured from" not in out
        assert "\n---\n" not in out
        assert not out.rstrip().endswith("*")

    def test_no_headings(self):
        out = compose(
            "user prose",
            "x = 1",
            language="python",
            source=SourceMeta(path="x.py"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        text_no_code = re.sub(r"```[\s\S]*?```", "", out)
        assert not re.search(r"^\s*#{1,6}\s+\S", text_no_code, re.MULTILINE)

    def test_footer_drops_missing_line_range(self):
        out = compose(
            "prose",
            "whole file",
            language="text",
            source=SourceMeta(path="notes.txt"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        assert "lines" not in out
        assert "Captured from `notes.txt`" in out

    def test_footer_drops_missing_commit(self):
        out = compose(
            "prose",
            "x = 1",
            language="python",
            source=SourceMeta(path="x.py", line_range="1-1"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        assert "commit" not in out
        assert "··" not in out

    def test_uncommitted_marker(self):
        out = compose(
            "prose",
            "x = 1",
            language="python",
            source=SourceMeta(path="x.py", commit="abc1234", uncommitted=True),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        assert "(uncommitted)" in out

    def test_truncation_marker_on_oversize(self):
        big_snippet = "line\n" * 5000
        out = compose(
            "p",
            big_snippet,
            language="text",
            source=SourceMeta(path="big.txt"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
            max_bytes=2048,
        )
        assert len(out.encode("utf-8")) <= 2048
        assert "truncated" in out
        assert out.rstrip().endswith("*")

    def test_truncation_with_redaction_combines_summary(self):
        out = compose(
            "p",
            "x" * 10000,
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=_summary(aws_access_key=2),
            captured_at=_FIXED_TS,
            max_bytes=512,
        )
        assert "secrets redacted" in out
        assert "truncated" in out

    def test_default_cap_constant(self):
        assert DESCRIPTION_MAX_BYTES == 16 * 1024

    def test_rfc3339_utc_timestamp(self):
        out = compose(
            "p",
            "code",
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        assert re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", out)

    def test_footer_position_after_code_block(self):
        out = compose(
            "p",
            "code",
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=RedactionSummary(),
            captured_at=_FIXED_TS,
        )
        idx_close = out.rindex("```")
        idx_hr = out.index("\n---\n", idx_close)
        assert idx_hr > idx_close
