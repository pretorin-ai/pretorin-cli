"""Tests that the CLI `evidence create` / `upsert` hard-error on missing -t.

Issue #79: defaults were removed across all write paths. The CLI is the
only path that hard-errors (other paths run the AI-drift normalizer);
this file pins the error UX.
"""

from __future__ import annotations

from typer.testing import CliRunner

from pretorin.cli.evidence import app

runner = CliRunner()


class TestEvidenceCreateRequiresType:
    def test_missing_type_exits_nonzero(self) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "- RBAC configuration verified",
            ],
        )
        assert result.exit_code != 0
        # Typer emits "Missing option" natively for required options.
        combined = result.output or ""
        assert "Missing option" in combined or "required" in combined.lower()

    def test_invalid_type_shows_full_canonical_list(self) -> None:
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "- RBAC configuration verified",
                "-t",
                "bogus_type",
            ],
        )
        assert result.exit_code != 0
        combined = result.output or ""
        # The error should list canonical types so the user can self-correct.
        assert "policy_document" in combined
        assert "screenshot" in combined
        assert "configuration" in combined


class TestEvidenceUpsertRequiresType:
    def test_missing_type_exits_nonzero(self) -> None:
        result = runner.invoke(
            app,
            [
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "-n",
                "RBAC",
                "-d",
                "- role map",
            ],
        )
        assert result.exit_code != 0
        combined = result.output or ""
        assert "Missing option" in combined or "required" in combined.lower()

    def test_invalid_type_shows_full_canonical_list(self) -> None:
        result = runner.invoke(
            app,
            [
                "upsert",
                "ac-02",
                "fedramp-moderate",
                "-n",
                "RBAC",
                "-d",
                "- role map",
                "-t",
                "bogus_type",
            ],
        )
        assert result.exit_code != 0
        combined = result.output or ""
        assert "policy_document" in combined
        assert "log_file" in combined
