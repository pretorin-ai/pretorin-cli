"""Coverage tests for src/pretorin/evidence/writer.py.

Covers line 37 (_safe_path_component ValueError), line 73 (_parse_frontmatter
no ---), line 77 (_parse_frontmatter < 3 parts), line 114 (write path traversal),
line 175 (list_local base_dir missing), line 181 (list_local search_dir missing),
lines 186-187 (list_local read exception).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pretorin.evidence.writer import (
    EvidenceWriter,
    LocalEvidence,
    _parse_frontmatter,
    _safe_path_component,
)


class TestSafePathComponent:
    """Tests for _safe_path_component."""

    def test_valid_component(self):
        assert _safe_path_component("fedramp-moderate") == "fedramp-moderate"

    def test_removes_slashes(self):
        assert _safe_path_component("a/b") == "ab"

    def test_removes_backslashes(self):
        assert _safe_path_component("a\\b") == "ab"

    def test_removes_null_bytes(self):
        assert _safe_path_component("a\0b") == "ab"

    def test_collapses_dots(self):
        result = _safe_path_component("a..b")
        assert ".." not in result

    def test_raises_on_empty_result(self):
        """Line 37: ValueError when sanitized result is empty."""
        with pytest.raises(ValueError, match="Invalid path component"):
            _safe_path_component("...")

    def test_raises_on_all_slashes(self):
        with pytest.raises(ValueError, match="Invalid path component"):
            _safe_path_component("///")

    def test_raises_on_dots_and_spaces_only(self):
        with pytest.raises(ValueError, match="Invalid path component"):
            _safe_path_component(". . .")


class TestParseFrontmatter:
    """Tests for _parse_frontmatter."""

    def test_no_frontmatter_delimiters(self):
        """Line 73: content doesn't start with ---."""
        fm, body = _parse_frontmatter("Just regular content")
        assert fm == {}
        assert body == "Just regular content"

    def test_fewer_than_three_parts(self):
        """Line 77: split produces fewer than 3 parts."""
        fm, body = _parse_frontmatter("---\nonly one delimiter")
        assert fm == {}
        assert body == "---\nonly one delimiter"

    def test_valid_frontmatter(self):
        content = "---\ncontrol_id: ac-02\nframework_id: fm-1\n---\n\n# Body"
        fm, body = _parse_frontmatter(content)
        assert fm["control_id"] == "ac-02"
        assert fm["framework_id"] == "fm-1"
        assert "# Body" in body


class TestEvidenceWriterWrite:
    """Tests for EvidenceWriter.write."""

    def test_write_creates_file(self, tmp_path):
        writer = EvidenceWriter(base_dir=tmp_path)
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="RBAC Config",
            description="Role mapping policy",
        )
        path = writer.write(ev)
        assert path.exists()
        content = path.read_text()
        assert "control_id: ac-02" in content
        assert "RBAC Config" in content

    def test_write_path_traversal_raises(self, tmp_path):
        """Line 114: path traversal detected raises ValueError."""
        writer = EvidenceWriter(base_dir=tmp_path / "evidence")
        # Create evidence with framework_id that would resolve outside base_dir
        # This is hard to trigger via _safe_path_component, so we patch resolve
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="valid",
            name="Test",
            description="Test desc",
        )
        # Patch file_path.resolve() to return something outside base_dir
        from unittest.mock import patch, PropertyMock

        original_write = writer.write

        # We need to test the actual path traversal check. We can create a symlink scenario.
        # Instead, let's mock the is_relative_to check
        base_dir = tmp_path / "evidence"
        base_dir.mkdir(parents=True, exist_ok=True)
        framework_dir = base_dir / "valid" / "ac-02"
        framework_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "is_relative_to", return_value=False):
            with pytest.raises(ValueError, match="Path traversal detected"):
                writer.write(ev)


class TestEvidenceWriterListLocal:
    """Tests for EvidenceWriter.list_local."""

    def test_list_local_base_dir_missing(self, tmp_path):
        """Line 175: base_dir doesn't exist returns empty list."""
        writer = EvidenceWriter(base_dir=tmp_path / "nonexistent")
        assert writer.list_local() == []

    def test_list_local_search_dir_missing(self, tmp_path):
        """Line 181: framework-specific search_dir doesn't exist returns empty list."""
        base_dir = tmp_path / "evidence"
        base_dir.mkdir()
        writer = EvidenceWriter(base_dir=base_dir)
        assert writer.list_local(framework_id="nonexistent-framework") == []

    def test_list_local_read_exception_continues(self, tmp_path):
        """Lines 186-187: read() exception causes continue."""
        base_dir = tmp_path / "evidence"
        base_dir.mkdir()
        # Create a malformed markdown file
        bad_file = base_dir / "bad.md"
        bad_file.write_text("")  # Empty file, will work but let's make read fail

        writer = EvidenceWriter(base_dir=base_dir)

        # Patch read to raise an exception
        from unittest.mock import patch

        with patch.object(writer, "read", side_effect=Exception("Parse error")):
            result = writer.list_local()
        assert result == []

    def test_list_local_with_valid_files(self, tmp_path):
        """list_local returns evidence from valid files."""
        writer = EvidenceWriter(base_dir=tmp_path)
        ev = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Test Evidence",
            description="Description here",
        )
        writer.write(ev)

        results = writer.list_local()
        assert len(results) == 1
        assert results[0].name == "Test Evidence"

    def test_list_local_filtered_by_framework(self, tmp_path):
        """list_local with framework_id filters to that framework."""
        writer = EvidenceWriter(base_dir=tmp_path)
        ev1 = LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Evidence 1",
            description="Desc 1",
        )
        ev2 = LocalEvidence(
            control_id="sc-07",
            framework_id="nist-800-53-r5",
            name="Evidence 2",
            description="Desc 2",
        )
        writer.write(ev1)
        writer.write(ev2)

        results = writer.list_local(framework_id="fedramp-moderate")
        assert len(results) == 1
        assert results[0].framework_id == "fedramp-moderate"
