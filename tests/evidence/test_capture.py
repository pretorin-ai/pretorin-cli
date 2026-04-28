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


class TestCaptureCodeEnvResolution:
    """End-to-end env resolution: detect → resolve → compose."""

    def test_safe_env_var_value_visible_in_evidence(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "config.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD", "300")\n')
        out = capture_code(
            user_description="Deletion grace period config.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
        )
        # Variable table at the bottom of the markdown.
        assert "| Variable | Value | Source |" in out
        assert "`DELETION_GRACE_PERIOD`" in out
        assert "`3600`" in out
        # Footer reports the env count.
        assert "1 env var resolved" in out

    def test_secret_named_env_var_value_redacted(self, tmp_path: Path, monkeypatch):
        """Tier-1: name matches denylist → value hidden, name still shown."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk_live_xxxxxxxxxxxxxxxx")
        src = tmp_path / "client.py"
        src.write_text('import os\nclient = OpenAI(api_key=os.environ["OPENAI_API_KEY"])\n')
        out = capture_code(
            user_description="OpenAI client init.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
        )
        # Name is shown so the auditor knows what was referenced.
        assert "`OPENAI_API_KEY`" in out
        # Value is NOT.
        assert "sk_live_xxxxxxxxxxxxxxxx" not in out
        assert "[REDACTED:secret-name]" in out
        assert "1 env redacted" in out

    def test_no_env_refs_no_block(self, tmp_path: Path):
        src = tmp_path / "plain.py"
        src.write_text("def f():\n    return 1\n")
        out = capture_code(
            user_description="A plain function.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
        )
        assert "**Resolved values at capture time:**" not in out
        assert "env var" not in out

    def test_no_redact_does_not_disable_tier2(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Even with --no-redact, env tier-2 still runs.

        The DATABASE_URL value contains embedded credentials. The name
        passes tier-1 (no denylist token), but tier-2 catches the
        `proto://user:pass@host` pattern. --no-redact only governs
        snippet-level secret redaction, not env value safety.
        """
        monkeypatch.setenv("DATABASE_URL", "postgres://user:hunter2@db.example.com:5432/app")
        src = tmp_path / "db.py"
        src.write_text('import os\nurl = os.getenv("DATABASE_URL")\n')
        out = capture_code(
            user_description="DB URL config.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=False,  # snippet redaction OFF
        )
        # Snippet itself is unredacted (per --no-redact contract).
        assert 'os.getenv("DATABASE_URL")' in out
        # But the resolved env value is STILL redacted.
        assert "hunter2" not in out
        assert "[REDACTED:cred_url]" in out

    def test_resolve_env_disabled_omits_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "config.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD")\n')
        out = capture_code(
            user_description="Deletion grace period config.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
            resolve_env=False,
        )
        assert "**Resolved values at capture time:**" not in out
        assert "env var" not in out

    def test_unset_var_with_default_shows_default(self, tmp_path: Path, monkeypatch):
        monkeypatch.delenv("LOG_LEVEL", raising=False)
        src = tmp_path / "logger.py"
        src.write_text('import os\nlevel = os.getenv("LOG_LEVEL", "info")\n')
        out = capture_code(
            user_description="Logger level config.",
            file_path=str(src),
            line_range=None,
            repository=None,
            commit=None,
            redact_pii=False,
            redact_secrets=True,
        )
        # Source default surfaces in the table with the "default" source label.
        assert "| `LOG_LEVEL` | `info` | default |" in out


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
