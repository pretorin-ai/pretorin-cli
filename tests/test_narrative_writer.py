"""Tests for src/pretorin/narrative/writer.py."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from pretorin.narrative.writer import (
    LocalNarrative,
    NarrativeWriter,
    _parse_frontmatter,
    _safe_path_component,
)


class TestWriteReadRoundTrip:
    """Write/read round-trip tests."""

    def test_write_creates_file(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="AC-02 narrative",
            content="- Item one\n\n```yaml\nkey: value\n```",
        )
        path = writer.write(narr)
        assert path.exists()
        content = path.read_text()
        assert "control_id: ac-02" in content
        assert "framework_id: fedramp-moderate" in content
        assert "platform_synced: false" in content

    def test_read_returns_correct_fields(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        narr = LocalNarrative(
            control_id="sc-07",
            framework_id="nist-800-53-r5",
            name="boundary-protection",
            content="- Firewall rules enforced",
            is_ai_generated=True,
        )
        path = writer.write(narr)
        read_back = writer.read(path)
        assert read_back.control_id == "sc-07"
        assert read_back.framework_id == "nist-800-53-r5"
        assert read_back.is_ai_generated is True
        assert read_back.platform_synced is False
        assert "Firewall rules enforced" in read_back.content

    def test_no_heading_in_output(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="test",
            content="- content only",
        )
        path = writer.write(narr)
        content = path.read_text()
        lines = content.split("\n")
        # After frontmatter, no line should start with #
        in_body = False
        for line in lines:
            if line == "---" and not in_body:
                continue
            if line == "---":
                in_body = True
                continue
            if in_body and line.startswith("# "):
                pytest.fail(f"Heading found in narrative body: {line}")


class TestListLocal:
    """Tests for list_local."""

    def test_list_local_returns_all(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        for i in range(3):
            narr = LocalNarrative(
                control_id=f"ac-0{i}",
                framework_id="fedramp-moderate",
                name=f"narrative-{i}",
                content=f"Content {i}",
            )
            writer.write(narr)
        results = writer.list_local()
        assert len(results) == 3

    def test_list_local_filters_by_framework(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        writer.write(
            LocalNarrative(
                control_id="ac-02",
                framework_id="fedramp-moderate",
                name="n1",
                content="c1",
            )
        )
        writer.write(
            LocalNarrative(
                control_id="ac-02",
                framework_id="nist-800-53-r5",
                name="n2",
                content="c2",
            )
        )
        results = writer.list_local(framework_id="fedramp-moderate")
        assert len(results) == 1
        assert results[0].framework_id == "fedramp-moderate"

    def test_list_local_empty_dir(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path / "nonexistent")
        assert writer.list_local() == []

    def test_list_local_bad_file_skipped(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path)
        with patch.object(writer, "read", side_effect=Exception("bad")):
            # Create a file so rglob finds something
            (tmp_path / "test.md").write_text("bad")
            results = writer.list_local()
        assert results == []


class TestPathSafety:
    """Path traversal and edge cases."""

    def test_path_traversal_raises(self, tmp_path):
        writer = NarrativeWriter(base_dir=tmp_path / "narratives")
        narr = LocalNarrative(
            control_id="ac-02",
            framework_id="valid",
            name="test",
            content="content",
        )
        base_dir = tmp_path / "narratives"
        base_dir.mkdir(parents=True, exist_ok=True)
        (base_dir / "valid" / "ac-02").mkdir(parents=True, exist_ok=True)

        with patch.object(Path, "is_relative_to", return_value=False):
            with pytest.raises(ValueError, match="Path traversal detected"):
                writer.write(narr)

    def test_safe_path_component_raises_on_empty(self):
        with pytest.raises(ValueError, match="Invalid path component"):
            _safe_path_component("...")


class TestParseFrontmatter:
    """Tests for _parse_frontmatter."""

    def test_no_frontmatter(self):
        fm, body = _parse_frontmatter("Just content")
        assert fm == {}
        assert body == "Just content"

    def test_incomplete_frontmatter(self):
        fm, body = _parse_frontmatter("---\nonly one")
        assert fm == {}

    def test_valid_frontmatter(self):
        content = "---\ncontrol_id: ac-02\nis_ai_generated: true\n---\n\nBody text"
        fm, body = _parse_frontmatter(content)
        assert fm["control_id"] == "ac-02"
        assert fm["is_ai_generated"] == "true"
        assert "Body text" in body
