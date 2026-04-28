"""Coverage tests for src/pretorin/evidence/writer.py.

Covers line 37 (_safe_path_component ValueError), line 73 (_parse_frontmatter
no ---), line 77 (_parse_frontmatter < 3 parts), line 114 (write path traversal),
line 175 (list_local base_dir missing), line 181 (list_local search_dir missing),
lines 186-187 (list_local read exception).
"""

from __future__ import annotations

import logging
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
            evidence_type="policy_document",
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
            evidence_type="policy_document",
        )
        # Patch file_path.resolve() to return something outside base_dir
        from unittest.mock import patch

        # We need to test the actual path traversal check. We can create a symlink scenario.
        # Instead, let's mock the is_relative_to check
        base_dir = tmp_path / "evidence"
        base_dir.mkdir(parents=True, exist_ok=True)
        framework_dir = base_dir / "valid" / "ac-02"
        framework_dir.mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "is_relative_to", return_value=False):
            with pytest.raises(ValueError, match="Path traversal detected"):
                writer.write(ev)


class TestEvidenceWriterReadLegacyFrontmatter:
    """Issue #79: legacy files missing evidence_type must not crash; default to 'other' + warn."""

    def test_legacy_file_missing_evidence_type_defaults_to_other_with_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        file_path = tmp_path / "legacy.md"
        file_path.write_text(
            "---\ncontrol_id: ac-02\nframework_id: fedramp-moderate\nstatus: draft\n"
            "collected_at: 2026-01-01T00:00:00\n---\n\n# Legacy Evidence\n\n- item"
        )
        writer = EvidenceWriter(base_dir=tmp_path)
        with caplog.at_level(logging.WARNING, logger="pretorin.evidence.writer"):
            ev = writer.read(file_path)
        assert ev.evidence_type == "other"
        assert any("missing 'evidence_type' frontmatter" in record.message for record in caplog.records)


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
            evidence_type="policy_document",
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
            evidence_type="policy_document",
        )
        ev2 = LocalEvidence(
            control_id="sc-07",
            framework_id="nist-800-53-r5",
            name="Evidence 2",
            description="Desc 2",
            evidence_type="policy_document",
        )
        writer.write(ev1)
        writer.write(ev2)

        results = writer.list_local(framework_id="fedramp-moderate")
        assert len(results) == 1
        assert results[0].framework_id == "fedramp-moderate"


class TestCodeSnippetRoundTrip:
    """Issue #89: code_snippet must survive write → read round-trip.

    The custom frontmatter parser is line-based (`key: value`), so a
    multi-line snippet has to be encoded. The fix base64-encodes under
    `code_snippet_b64`. These tests pin the round-trip behavior across
    every byzantine input the parser could choke on.
    """

    def _make(self, snippet: str | None) -> LocalEvidence:
        return LocalEvidence(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="Snippet test",
            description="prose",
            evidence_type="code_snippet",
            code_snippet=snippet,
        )

    def test_multiline_snippet_roundtrips(self, tmp_path):
        snippet = "def verify_mfa(user, code):\n    totp = pyotp.TOTP(user.mfa_secret)\n    return totp.verify(code)\n"
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(snippet))
        assert writer.read(path).code_snippet == snippet

    def test_snippet_with_fences_roundtrips(self, tmp_path):
        snippet = "Some prose with fences:\n```python\nprint('x')\n```\nafter"
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(snippet))
        assert writer.read(path).code_snippet == snippet

    def test_snippet_with_unicode_roundtrips(self, tmp_path):
        snippet = "héllo 🔐 Ωmega ✓"
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(snippet))
        assert writer.read(path).code_snippet == snippet

    def test_snippet_with_frontmatter_delimiter_roundtrips(self, tmp_path):
        """Critical: a `---` line inside the snippet must not be mistaken
        for a frontmatter terminator after b64 encoding."""
        snippet = "before\n---\nafter\n"
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(snippet))
        assert writer.read(path).code_snippet == snippet

    def test_snippet_with_yaml_significant_chars_roundtrips(self, tmp_path):
        snippet = "key: value\n- list item\n* another: thing\n# heading-looking"
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(snippet))
        assert writer.read(path).code_snippet == snippet

    def test_empty_snippet_writes_no_key(self, tmp_path):
        """None/empty snippet should not produce a `code_snippet_b64:` line."""
        writer = EvidenceWriter(base_dir=tmp_path)
        path = writer.write(self._make(None))
        assert "code_snippet_b64" not in path.read_text()
        assert writer.read(path).code_snippet is None

    def test_corrupt_b64_returns_none_with_warning(self, tmp_path, caplog: pytest.LogCaptureFixture) -> None:
        """A malformed b64 value must not crash read; log warning, return None."""
        file_path = tmp_path / "corrupt.md"
        file_path.write_text(
            "---\ncontrol_id: ac-02\nframework_id: fm-1\nevidence_type: code_snippet\n"
            "status: draft\ncollected_at: 2026-01-01T00:00:00\n"
            "code_snippet_b64: !!!not-base64!!!\n---\n\n# Title\n\nbody"
        )
        writer = EvidenceWriter(base_dir=tmp_path)
        with caplog.at_level(logging.WARNING, logger="pretorin.evidence.writer"):
            ev = writer.read(file_path)
        assert ev.code_snippet is None
        assert any("code_snippet_b64" in r.message for r in caplog.records)
