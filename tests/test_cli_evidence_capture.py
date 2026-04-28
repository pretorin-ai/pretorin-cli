"""CLI-level tests for the #88 capture flow.

Covers the new --capture / --no-capture / --log-file / --no-redact
behaviors on `pretorin evidence upsert` and `pretorin evidence create`.
The `_maybe_capture` helper is exercised end-to-end through the CLI
runner so we catch flag-routing bugs.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from pretorin.cli.evidence import _confirm_no_redact, _maybe_capture, app
from pretorin.evidence import redact as redact_mod
from tests._synthetic_fixtures import AWS_AKIA

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_backend_log(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(redact_mod, "_BACKEND_LOGGED", False)


class TestMaybeCaptureUnit:
    """Direct tests for _maybe_capture without the CLI runner.

    Hard rule (post-rework 2026-04-27): when --code-file or --log-file is
    passed, capture is mandatory. There is no opt-out path.
    """

    def test_returns_input_when_no_source(self):
        out = _maybe_capture(
            description="prose",
            code_file=None,
            code_lines=None,
            code_commit=None,
            log_file=None,
            log_tail=None,
            log_since=None,
            redact_pii=None,
            no_redact=False,
        )
        assert out == "prose"

    def test_code_file_always_captures(self, tmp_path: Path):
        src = tmp_path / "x.py"
        src.write_text("def f():\n    return 1\n")
        out = _maybe_capture(
            description="prose",
            code_file=str(src),
            code_lines=None,
            code_commit=None,
            log_file=None,
            log_tail=None,
            log_since=None,
            redact_pii=None,
            no_redact=False,
        )
        assert "```python" in out
        assert "def f()" in out
        assert "Captured from " in out

    def test_log_file_always_captures(self, tmp_path: Path):
        log = tmp_path / "auth.log"
        log.write_text("2026-04-27T10:00:00Z user login\n")
        out = _maybe_capture(
            description="prose",
            code_file=None,
            code_lines=None,
            code_commit=None,
            log_file=str(log),
            log_tail=10,
            log_since=None,
            redact_pii=None,
            no_redact=False,
        )
        assert "```text" in out
        assert "Captured from " in out


class TestCliCaptureFlags:
    """Smoke tests exercising the full CLI command path."""

    def test_create_with_code_file_auto_captures(self, tmp_path: Path, monkeypatch):
        """No --capture flag needed; capture fires automatically."""
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "auth.py"
        src.write_text("def verify(): return True\n")
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "MFA verification logic.",
                "-t",
                "code_snippet",
                "--code-file",
                str(src),
            ],
        )
        assert result.exit_code == 0, result.output
        files = list((tmp_path / "evidence").rglob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "```python" in content
        assert "def verify()" in content
        # Provenance footer rendered into the description body.
        assert "Captured from " in content
        # Structured frontmatter still carries the path.
        assert "code_file_path: " in content

    def test_no_capture_flag_is_unrecognized(self, tmp_path: Path, monkeypatch):
        """The --no-capture flag was removed in the rework. Passing it errors."""
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "auth.py"
        src.write_text("def verify(): return True\n")
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "x",
                "-t",
                "code_snippet",
                "--code-file",
                str(src),
                "--no-capture",
            ],
        )
        assert result.exit_code != 0
        assert "no such option" in result.output.lower() or "no-capture" in result.output.lower()

    def test_create_capture_binary_aborts(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "x.bin"
        src.write_bytes(b"hello\x00world")
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "x",
                "-t",
                "code_snippet",
                "--code-file",
                str(src),
            ],
        )
        assert result.exit_code == 1
        assert "binary" in result.output.lower()

    def test_create_capture_missing_file_aborts(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "x",
                "-t",
                "code_snippet",
                "--code-file",
                str(tmp_path / "nope.py"),
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_create_with_log_file_capture_symmetry(self, tmp_path: Path, monkeypatch):
        """`evidence create --log-file --log-tail N` embeds the log tail
        in the local file's description, just like upsert."""
        monkeypatch.chdir(tmp_path)
        log = tmp_path / "auth.log"
        log.write_text("\n".join(f"2026-04-27T10:00:0{i}Z user{i} login" for i in range(5)) + "\n")
        result = runner.invoke(
            app,
            [
                "create",
                "au-02",
                "fedramp-moderate",
                "-d",
                "Authentication audit trail sample.",
                "-t",
                "log_file",
                "--log-file",
                str(log),
                "--log-tail",
                "3",
            ],
        )
        assert result.exit_code == 0, result.output
        files = list((tmp_path / "evidence").rglob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "```text" in content
        assert "user4 login" in content
        assert "Captured from " in content


class TestEnvResolutionFlag:
    """--no-resolve-env wiring through the CLI down to capture_code()."""

    def test_default_resolves_safe_env_var(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "config.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD")\n')
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "Grace period config.",
                "-t",
                "configuration",
                "--code-file",
                str(src),
            ],
        )
        assert result.exit_code == 0, result.output
        files = list((tmp_path / "evidence").rglob("*.md"))
        content = files[0].read_text()
        assert "| Variable | Value | Source |" in content
        assert "`DELETION_GRACE_PERIOD`" in content
        assert "`3600`" in content

    def test_default_redacts_secret_named_env_var(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("OPENAI_API_KEY", "sk_live_xxxxxxxxxxxx")
        src = tmp_path / "client.py"
        src.write_text('import os\nclient = OpenAI(api_key=os.environ["OPENAI_API_KEY"])\n')
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "Client init.",
                "-t",
                "code_snippet",
                "--code-file",
                str(src),
            ],
        )
        assert result.exit_code == 0, result.output
        content = list((tmp_path / "evidence").rglob("*.md"))[0].read_text()
        assert "sk_live_xxxxxxxxxxxx" not in content
        assert "[REDACTED:secret-name]" in content

    def test_no_resolve_env_omits_block(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "config.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD")\n')
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "Grace period config.",
                "-t",
                "configuration",
                "--code-file",
                str(src),
                "--no-resolve-env",
            ],
        )
        assert result.exit_code == 0, result.output
        content = list((tmp_path / "evidence").rglob("*.md"))[0].read_text()
        assert "**Resolved values at capture time:**" not in content
        assert "env var" not in content

    def test_log_capture_does_not_resolve_env(self, tmp_path: Path, monkeypatch):
        """Resolution is for code captures only — log lines are runtime output."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        log = tmp_path / "auth.log"
        # Even if the log line happens to contain an env-var reference,
        # we don't resolve it — logs are values already.
        log.write_text('2026-04-27T10:00:00Z startup grace=os.getenv("DELETION_GRACE_PERIOD")\n')
        result = runner.invoke(
            app,
            [
                "create",
                "au-02",
                "fedramp-moderate",
                "-d",
                "Auth events.",
                "-t",
                "log_file",
                "--log-file",
                str(log),
                "--log-tail",
                "10",
            ],
        )
        assert result.exit_code == 0, result.output
        content = list((tmp_path / "evidence").rglob("*.md"))[0].read_text()
        assert "**Resolved values at capture time:**" not in content


class TestMaybeCaptureNoResolveEnvUnit:
    """Direct unit test for the no_resolve_env arg threading."""

    def test_no_resolve_env_threads_through(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "x.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD")\n')
        out = _maybe_capture(
            description="prose",
            code_file=str(src),
            code_lines=None,
            code_commit=None,
            log_file=None,
            log_tail=None,
            log_since=None,
            redact_pii=None,
            no_redact=False,
            no_resolve_env=True,
        )
        assert "Resolved values" not in out

    def test_resolve_env_default_on(self, tmp_path: Path, monkeypatch):
        monkeypatch.setenv("DELETION_GRACE_PERIOD", "3600")
        src = tmp_path / "x.py"
        src.write_text('import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD")\n')
        out = _maybe_capture(
            description="prose",
            code_file=str(src),
            code_lines=None,
            code_commit=None,
            log_file=None,
            log_tail=None,
            log_since=None,
            redact_pii=None,
            no_redact=False,
        )
        assert "| Variable | Value | Source |" in out
        assert "`DELETION_GRACE_PERIOD`" in out
        assert "`3600`" in out


class TestNoRedactConfirmation:
    """`--no-redact` requires interactive confirm in TTY, refused in CI."""

    def test_no_redact_in_non_tty_rejected(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        src = tmp_path / "secrets.py"
        src.write_text(f"KEY = '{AWS_AKIA}'\n")
        # CliRunner runs with non-TTY stdin by default — perfect for this test.
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "Auth key reference.",
                "-t",
                "code_snippet",
                "--code-file",
                str(src),
                "--no-redact",
            ],
        )
        assert result.exit_code == 1
        assert "interactive" in result.output.lower()

    def test_confirm_no_redact_unit_decline_aborts(self, monkeypatch):
        """Unit-level: simulate TTY + user declines."""
        import typer

        monkeypatch.setattr("typer.confirm", lambda *a, **kw: False)
        with pytest.raises(typer.Exit) as exc:
            _confirm_no_redact(non_interactive=False)
        assert exc.value.exit_code == 1

    def test_confirm_no_redact_unit_accept_proceeds(self, monkeypatch):
        """Unit-level: simulate TTY + user confirms; function returns normally."""
        monkeypatch.setattr("typer.confirm", lambda *a, **kw: True)
        # Should not raise.
        _confirm_no_redact(non_interactive=False)

    def test_confirm_no_redact_non_interactive_rejects(self):
        """Unit-level: explicit non-interactive flag rejects without prompting."""
        import typer

        with pytest.raises(typer.Exit) as exc:
            _confirm_no_redact(non_interactive=True)
        assert exc.value.exit_code == 1
