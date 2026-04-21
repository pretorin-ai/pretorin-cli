"""Tests for evidence_validation.py — validate_code_reference() and enrich_evidence_recommendations()."""

from __future__ import annotations

from pathlib import Path

import pytest

from pretorin.workflows.evidence_validation import (
    MAX_SNIPPET_BYTES,
    enrich_evidence_recommendations,
    validate_code_reference,
)


class TestValidateCodeReference:
    def test_returns_none_when_no_file_path(self) -> None:
        assert validate_code_reference(None, None, Path("/tmp")) is None

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        result = validate_code_reference("nonexistent.py", None, tmp_path)
        assert result is None

    def test_returns_context_with_valid_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("line1\nline2\nline3\n")
        result = validate_code_reference("test.py", None, tmp_path)
        assert result is not None
        assert result["code_file_path"] == "test.py"
        assert "code_line_numbers" not in result

    def test_reads_actual_file_content_as_snippet(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("alpha\nbeta\ngamma\ndelta\n")
        result = validate_code_reference("test.py", "2-3", tmp_path)
        assert result is not None
        assert result["code_snippet"] == "beta\ngamma"
        assert result["code_line_numbers"] == "2-3"

    def test_single_line_range(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("a\nb\nc\n")
        result = validate_code_reference("test.py", "2", tmp_path)
        assert result is not None
        assert result["code_snippet"] == "b"

    def test_drops_line_range_when_out_of_bounds(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("a\nb\nc\n")
        result = validate_code_reference("test.py", "1-100", tmp_path)
        assert result is not None
        assert result["code_file_path"] == "test.py"
        assert "code_line_numbers" not in result
        assert "code_snippet" not in result

    def test_drops_invalid_line_format(self, tmp_path: Path) -> None:
        f = tmp_path / "test.py"
        f.write_text("a\nb\n")
        result = validate_code_reference("test.py", "abc", tmp_path)
        assert result is not None
        assert "code_line_numbers" not in result

    def test_truncates_large_snippets(self, tmp_path: Path) -> None:
        f = tmp_path / "large.py"
        # Write a file larger than MAX_SNIPPET_BYTES
        line = "x" * 100 + "\n"
        num_lines = (MAX_SNIPPET_BYTES // len(line.encode())) + 100
        f.write_text(line * num_lines)
        result = validate_code_reference("large.py", f"1-{num_lines}", tmp_path)
        assert result is not None
        assert "[TRUNCATED" in result["code_snippet"]

    def test_path_traversal_blocked(self, tmp_path: Path) -> None:
        # Create a file outside the working dir
        parent = tmp_path.parent / "secret.txt"
        parent.write_text("secret")
        result = validate_code_reference("../secret.txt", None, tmp_path)
        assert result is None

    def test_symlink_traversal_blocked(self, tmp_path: Path) -> None:
        target = tmp_path.parent / "secret2.txt"
        target.write_text("secret")
        link = tmp_path / "link.txt"
        link.symlink_to(target)
        result = validate_code_reference("link.txt", None, tmp_path)
        assert result is None


class TestEnrichEvidenceRecommendations:
    def test_enriches_valid_reference(self, tmp_path: Path) -> None:
        f = tmp_path / "config.yaml"
        f.write_text("key: value\nother: data\n")
        recs = [{"name": "Config", "code_file_path": "config.yaml", "code_line_numbers": "1-2"}]
        enrich_evidence_recommendations(recs, tmp_path)
        assert recs[0]["code_snippet"] == "key: value\nother: data"

    def test_drops_invalid_reference(self, tmp_path: Path) -> None:
        recs = [{"name": "Missing", "code_file_path": "nope.py", "code_line_numbers": "1-5"}]
        enrich_evidence_recommendations(recs, tmp_path)
        assert "code_file_path" not in recs[0]
        assert "code_snippet" not in recs[0]

    def test_leaves_recs_without_file_path_unchanged(self, tmp_path: Path) -> None:
        recs = [{"name": "Policy", "description": "A policy doc"}]
        enrich_evidence_recommendations(recs, tmp_path)
        assert recs[0] == {"name": "Policy", "description": "A policy doc"}

    def test_mixed_valid_and_invalid(self, tmp_path: Path) -> None:
        f = tmp_path / "real.py"
        f.write_text("print('hello')\n")
        recs = [
            {"name": "Valid", "code_file_path": "real.py", "code_line_numbers": "1"},
            {"name": "Invalid", "code_file_path": "fake.py"},
        ]
        enrich_evidence_recommendations(recs, tmp_path)
        assert recs[0]["code_snippet"] == "print('hello')"
        assert "code_file_path" not in recs[1]
