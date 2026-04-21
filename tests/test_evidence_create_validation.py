"""Tests for evidence create markdown validation."""

from __future__ import annotations

from unittest.mock import patch

from typer.testing import CliRunner

from pretorin.cli.evidence import app

runner = CliRunner()


class TestEvidenceCreateValidation:
    def test_rejects_plain_text(self):
        """Evidence create should reject description with no rich elements."""
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "plain text with no markdown",
                "-t",
                "policy_document",
            ],
        )
        assert result.exit_code != 0
        assert "Validation failed" in result.output or "rich" in result.output.lower()

    def test_accepts_list_item(self, tmp_path):
        """Evidence create should accept description with a list item."""
        with patch("pretorin.evidence.writer.EvidenceWriter.write", return_value=tmp_path / "test.md"):
            result = runner.invoke(
                app,
                [
                    "create",
                    "ac-02",
                    "fedramp-moderate",
                    "-d",
                    "- RBAC configuration verified",
                    "-t",
                    "configuration",
                ],
            )
            assert result.exit_code == 0

    def test_rejects_headings(self):
        """Evidence create should reject description with headings."""
        result = runner.invoke(
            app,
            [
                "create",
                "ac-02",
                "fedramp-moderate",
                "-d",
                "# Heading\n- list item",
                "-t",
                "policy_document",
            ],
        )
        assert result.exit_code != 0
        assert "Validation failed" in result.output or "heading" in result.output.lower()

    def test_accepts_code_block(self, tmp_path):
        """Evidence create should accept description with a code block."""
        with patch("pretorin.evidence.writer.EvidenceWriter.write", return_value=tmp_path / "test.md"):
            result = runner.invoke(
                app,
                [
                    "create",
                    "ac-02",
                    "fedramp-moderate",
                    "-d",
                    "```yaml\nkey: value\n```",
                    "-t",
                    "configuration",
                ],
            )
            assert result.exit_code == 0
