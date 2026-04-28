"""Tests for the snapshot → redact → markdown orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from pretorin.evidence.capture import capture_code, capture_log
from pretorin.evidence.snapshot import SnapshotError
from tests._synthetic_fixtures import AWS_AKIA


class TestCaptureCode:
    def test_basic_code_capture(self, tmp_path: Path):
        src = tmp_path / "auth.py"
        src.write_text(
            "import pyotp\n"
            "def verify_mfa(user, code):\n"
            "    totp = pyotp.TOTP(user.mfa_secret)\n"
            "    return totp.verify(code)\n"
        )
        out = capture_code(
            user_description="MFA verification.",
            file_path=str(src),
            line_range="2-4",
            repository=None,
            commit="abc1234",
            redact_pii=False,
            redact_secrets=True,
        )
        assert "MFA verification." in out
        assert "```python" in out
        assert "def verify_mfa" in out
        # Provenance footer at the end of the description.
        assert "Captured from `" in out
        assert "lines 2-4" in out
        assert "commit `abc1234`" in out

    def test_secret_redacted_in_capture(self, tmp_path: Path):
        src = tmp_path / "secrets.py"
        src.write_text(f"AWS_KEY = '{AWS_AKIA}'\n")
        out = capture_code(
            user_description="Auth key reference.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
        )
        assert AWS_AKIA not in out
        assert "[REDACTED:aws_access_key]" in out
        assert "1 secret redacted" in out

    def test_no_redact_passes_through(self, tmp_path: Path):
        src = tmp_path / "secrets.py"
        src.write_text(f"AWS_KEY = '{AWS_AKIA}'\n")
        out = capture_code(
            user_description="ref",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=False,
        )
        assert AWS_AKIA in out

    def test_binary_refused(self, tmp_path: Path):
        src = tmp_path / "binary.dat"
        src.write_bytes(b"hello\x00\x01\x02world")
        with pytest.raises(SnapshotError, match="binary"):
            capture_code(
                user_description="x",
                file_path=str(src),
                line_range=None,
                repository=None,
                commit=None,
                redact_pii=False,
                redact_secrets=True,
            )

    def test_missing_file_refused(self, tmp_path: Path):
        with pytest.raises(SnapshotError, match="not found"):
            capture_code(
                user_description="x",
                file_path=str(tmp_path / "nope.py"),
                line_range=None,
                repository=None,
                commit=None,
                redact_pii=False,
                redact_secrets=True,
            )


class TestCaptureLog:
    def test_basic_log_tail(self, tmp_path: Path):
        log = tmp_path / "auth.log"
        log.write_text("\n".join(f"2026-04-27T10:00:0{i}Z user{i} login" for i in range(5)) + "\n")
        out = capture_log(
            user_description="Auth events.",
            file_path=str(log),
            tail=3,
            since=None,
            redact_pii=True,
            redact_secrets=True,
        )
        assert "Auth events." in out
        assert "```text" in out
        assert "user4 login" in out

    def test_log_password_keyword_redaction(self, tmp_path: Path):
        """The narrowed redactor catches password assignments, not PII."""
        log = tmp_path / "auth.log"
        log.write_text('config: password = "supersecret9876"\n')
        out = capture_log(
            user_description="Auth events.",
            file_path=str(log),
            tail=10,
            since=None,
            redact_pii=False,
            redact_secrets=True,
        )
        assert "supersecret9876" not in out
        assert "[REDACTED:password]" in out
