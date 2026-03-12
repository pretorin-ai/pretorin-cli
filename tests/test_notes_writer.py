"""Tests for src/pretorin/notes/writer.py."""

from __future__ import annotations

from unittest.mock import patch

from pretorin.notes.writer import LocalNote, NotesWriter, _parse_frontmatter


class TestWriteReadRoundTrip:
    def test_write_creates_file(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path)
        note = LocalNote(
            control_id="ac-02",
            framework_id="fedramp-moderate",
            name="sso-gap",
            content="Gap: Missing SSO evidence",
        )
        path = writer.write(note)
        assert path.exists()
        content = path.read_text()
        assert "control_id: ac-02" in content
        assert "platform_synced: false" in content

    def test_read_returns_correct_fields(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path)
        note = LocalNote(
            control_id="sc-07",
            framework_id="nist-800-53-r5",
            name="firewall-gap",
            content="Need firewall config evidence",
        )
        path = writer.write(note)
        read_back = writer.read(path)
        assert read_back.control_id == "sc-07"
        assert read_back.framework_id == "nist-800-53-r5"
        assert read_back.platform_synced is False
        assert "firewall config" in read_back.content


class TestListLocal:
    def test_list_local_returns_all(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path)
        for i in range(2):
            writer.write(
                LocalNote(
                    control_id=f"ac-0{i}",
                    framework_id="fedramp-moderate",
                    name=f"note-{i}",
                    content=f"Content {i}",
                )
            )
        assert len(writer.list_local()) == 2

    def test_list_local_filters_by_framework(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path)
        writer.write(LocalNote(control_id="ac-02", framework_id="fedramp-moderate", name="n1", content="c1"))
        writer.write(LocalNote(control_id="ac-02", framework_id="nist-800-53-r5", name="n2", content="c2"))
        results = writer.list_local(framework_id="fedramp-moderate")
        assert len(results) == 1

    def test_list_local_empty_dir(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path / "nonexistent")
        assert writer.list_local() == []

    def test_list_local_bad_file_skipped(self, tmp_path):
        writer = NotesWriter(base_dir=tmp_path)
        (tmp_path / "bad.md").write_text("bad")
        with patch.object(writer, "read", side_effect=Exception("bad")):
            assert writer.list_local() == []


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        fm, body = _parse_frontmatter("Just content")
        assert fm == {}

    def test_valid_frontmatter(self):
        content = "---\ncontrol_id: ac-02\nplatform_synced: true\n---\n\nBody"
        fm, body = _parse_frontmatter(content)
        assert fm["control_id"] == "ac-02"
        assert fm["platform_synced"] == "true"
