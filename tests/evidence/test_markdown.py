"""Tests for pretorin.evidence.markdown."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from pretorin.evidence.env_resolve import EnvSummary, ResolvedRef
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


def _env_summary_with(*refs: ResolvedRef) -> EnvSummary:
    s = EnvSummary()
    for r in refs:
        s.refs.append(r)
        if r.redacted_kind is not None:
            s.redacted += 1
        elif r.is_unset:
            s.unset += 1
        else:
            s.resolved += 1
    return s


class TestComposeEnvSummary:
    """compose() renders the resolved-values block above the footer rule."""

    def test_resolved_table_between_fence_and_rule(self):
        env_summary = _env_summary_with(
            ResolvedRef(
                name="DELETION_GRACE_PERIOD",
                value="3600",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = compose(
            "Grace period config.",
            'GRACE = os.getenv("DELETION_GRACE_PERIOD", "300")\n',
            language="python",
            source=SourceMeta(path="app/config.py", line_range="10-10"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
        )
        idx_close = out.rindex("```")
        idx_table = out.index("| Variable | Value | Source |")
        idx_hr = out.index("\n---\n")
        assert idx_close < idx_table < idx_hr

    def test_footer_carries_env_count(self):
        env_summary = _env_summary_with(
            ResolvedRef(
                name="X",
                value="1",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = compose(
            "p",
            "code",
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
        )
        last_line = [ln for ln in out.splitlines() if ln.strip()][-1]
        assert "1 env var resolved" in last_line

    def test_footer_carries_both_redaction_and_env_counts(self):
        env_summary = _env_summary_with(
            ResolvedRef(
                name="X",
                value="1",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = compose(
            "p",
            "code",
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=_summary(aws_access_key=2),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
        )
        last_line = [ln for ln in out.splitlines() if ln.strip()][-1]
        assert "2 secrets redacted" in last_line
        assert "1 env var resolved" in last_line

    def test_no_env_summary_omits_block(self):
        out = compose(
            "p",
            "code",
            language="text",
            source=SourceMeta(path="x.txt"),
            redaction=RedactionSummary(),
            env_summary=None,
            captured_at=_FIXED_TS,
        )
        assert "Resolved values" not in out

    def test_table_escapes_backticks_in_value(self):
        """B14: a value containing a backtick must use double-backtick
        wrapping per CommonMark, otherwise the inner backtick closes the
        code span early and the markdown renders garbage."""
        env_summary = _env_summary_with(
            ResolvedRef(
                name="CMD",
                value="echo `whoami`",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = compose(
            "shell command snippet",
            "echo $CMD\n",
            language="bash",
            source=SourceMeta(path="run.sh"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
        )
        # Value cell uses `` ` `` wrapping so the inner backtick survives.
        assert "`` echo `whoami` ``" in out

    def test_table_dedupes_name_present_in_both_env_and_symbols(self):
        """LG1: when a name is detected by env_resolve AND symbol_resolve
        (rare — `os.getenv("X")` plus `from foo import X` in same file),
        the table renders one row, preferring the symbol entry because
        its file:line source is more informative than 'env'."""
        from pretorin.evidence.symbol_resolve import Definition, SymbolSummary

        env_summary = _env_summary_with(
            ResolvedRef(
                name="MAX_RETRIES",
                value="5",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        symbols = SymbolSummary()
        symbols.definitions.append(
            Definition(name="MAX_RETRIES", file_path="app/config.py", line=12, value="5", snippet="MAX_RETRIES = 5")
        )
        out = compose(
            "p",
            "x = MAX_RETRIES\n",
            language="python",
            source=SourceMeta(path="app/main.py"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            symbols=symbols,
            captured_at=_FIXED_TS,
        )
        # The name appears only once in the table (count rows).
        # The symbol's file:line source wins over the env source label.
        assert out.count("`MAX_RETRIES`") == 1
        assert "`app/config.py:12`" in out

    def test_table_flattens_newlines_in_value(self):
        """B15: multi-line values would otherwise break the table row."""
        env_summary = _env_summary_with(
            ResolvedRef(
                name="MULTILINE",
                value="line1\nline2\nline3",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = compose(
            "config",
            "echo $MULTILINE\n",
            language="bash",
            source=SourceMeta(path="run.sh"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
        )
        # Newlines in the value are replaced with spaces.
        assert "line1 line2 line3" in out
        # And the multi-line form does NOT appear.
        assert "line1\nline2" not in out

    def test_truncation_preserves_resolved_table(self):
        """Snippet truncates first; the variable table reaches the auditor intact."""
        env_summary = _env_summary_with(
            ResolvedRef(
                name="DELETION_GRACE_PERIOD",
                value="3600",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            ),
            ResolvedRef(
                name="OPENAI_API_KEY",
                value=None,
                redacted_kind="secret-name",
                used_default=False,
                is_unset=False,
            ),
        )
        out = compose(
            "p",
            "x" * 10000,
            language="text",
            source=SourceMeta(path="big.txt"),
            redaction=RedactionSummary(),
            env_summary=env_summary,
            captured_at=_FIXED_TS,
            max_bytes=2048,
        )
        assert len(out.encode("utf-8")) <= 2048
        assert "truncated" in out
        # The variable table survived truncation.
        assert "| Variable | Value | Source |" in out
        assert "`DELETION_GRACE_PERIOD`" in out
        assert "`3600`" in out
        assert "`[REDACTED:secret-name]`" in out
