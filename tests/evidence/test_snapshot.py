"""Tests for pretorin.evidence.snapshot."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from pretorin.evidence.snapshot import (
    DEFAULT_LOG_TAIL,
    MAX_CODE_BYTES,
    SnapshotError,
    _is_binary,
    _line_timestamp,
    _parse_line_range,
    _parse_since,
    read_code,
    read_log,
)


class TestParseLineRange:
    def test_range(self):
        assert _parse_line_range("12-30") == (12, 30)

    def test_single_line(self):
        assert _parse_line_range("42") == (42, 42)

    def test_whitespace(self):
        assert _parse_line_range("  12-30  ") == (12, 30)

    def test_empty_raises(self):
        with pytest.raises(SnapshotError, match="Empty"):
            _parse_line_range("")

    def test_non_numeric_raises(self):
        with pytest.raises(SnapshotError, match="Invalid"):
            _parse_line_range("abc")

    def test_zero_raises(self):
        with pytest.raises(SnapshotError, match="positive"):
            _parse_line_range("0-5")

    def test_reversed_raises(self):
        with pytest.raises(SnapshotError, match="positive"):
            _parse_line_range("30-12")


class TestIsBinary:
    def test_null_byte_is_binary(self):
        assert _is_binary(b"hello\x00world")

    def test_pure_text_is_not_binary(self):
        assert not _is_binary(b"hello world\n")

    def test_invalid_utf8_is_binary(self):
        assert _is_binary(b"\xff\xfe\xfd")

    def test_emoji_is_text(self):
        assert not _is_binary("héllo 🔐".encode())


class TestReadCode:
    def test_whole_file_under_cap(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("def f():\n    return 1\n")
        snap = read_code(p)
        assert snap.text == "def f():\n    return 1\n"
        assert snap.line_range is None
        assert snap.path == str(p)

    def test_partial_range(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("a\nb\nc\nd\ne\n")
        snap = read_code(p, "2-4")
        assert snap.text == "b\nc\nd\n"
        assert snap.line_range == "2-4"
        assert snap.line_count == 3

    def test_single_line_range(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("a\nb\nc\n")
        snap = read_code(p, "2")
        assert snap.text == "b\n"
        assert snap.line_range == "2"

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(SnapshotError, match="not found"):
            read_code(tmp_path / "nope.py")

    def test_directory_rejected(self, tmp_path: Path):
        with pytest.raises(SnapshotError, match="not found"):
            read_code(tmp_path)

    def test_binary_refused(self, tmp_path: Path):
        p = tmp_path / "x.bin"
        p.write_bytes(b"hello\x00world\x01\x02")
        with pytest.raises(SnapshotError, match="binary"):
            read_code(p)

    def test_oversize_without_range(self, tmp_path: Path):
        p = tmp_path / "big.txt"
        p.write_bytes(b"a" * (MAX_CODE_BYTES + 1))
        with pytest.raises(SnapshotError, match="--code-lines"):
            read_code(p)

    def test_oversize_with_range_under_cap_succeeds(self, tmp_path: Path):
        p = tmp_path / "big.txt"
        p.write_text("\n".join(str(i) for i in range(100000)) + "\n")
        snap = read_code(p, "1-3")
        assert snap.text == "0\n1\n2\n"

    def test_range_past_end_of_file(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("a\nb\nc\n")
        with pytest.raises(SnapshotError, match="past end"):
            read_code(p, "10-20")

    def test_range_partial_past_end_clamped(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("a\nb\nc\n")
        snap = read_code(p, "2-10")
        assert snap.text == "b\nc\n"

    def test_unicode_content(self, tmp_path: Path):
        p = tmp_path / "x.py"
        p.write_text("# héllo 🔐\nprint('Ω')\n")
        snap = read_code(p)
        assert "🔐" in snap.text


class TestParseSince:
    def test_z_suffix_python_310_compatible(self):
        dt = _parse_since("2026-04-27T10:00:00Z")
        assert dt == datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)

    def test_offset(self):
        dt = _parse_since("2026-04-27T10:00:00+00:00")
        assert dt == datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)

    def test_no_tz_assumes_utc(self):
        dt = _parse_since("2026-04-27T10:00:00")
        assert dt.tzinfo == timezone.utc

    def test_invalid_raises(self):
        with pytest.raises(SnapshotError, match="--log-since"):
            _parse_since("yesterday")


class TestLineTimestamp:
    def test_z_suffix(self):
        ts = _line_timestamp("2026-04-27T10:00:00Z user logged in\n")
        assert ts == datetime(2026, 4, 27, 10, 0, 0, tzinfo=timezone.utc)

    def test_offset(self):
        ts = _line_timestamp("2026-04-27T10:00:00+00:00 something\n")
        assert ts is not None

    def test_no_timestamp_returns_none(self):
        assert _line_timestamp("just a log line\n") is None

    def test_empty_line(self):
        assert _line_timestamp("\n") is None


class TestReadLog:
    def test_default_tail(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        p.write_text("\n".join(f"line {i}" for i in range(500)) + "\n")
        snap = read_log(p)
        assert snap.line_count == DEFAULT_LOG_TAIL

    def test_explicit_tail(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        p.write_text("\n".join(f"line {i}" for i in range(50)) + "\n")
        snap = read_log(p, tail=10)
        assert snap.line_count == 10
        assert "line 49" in snap.text
        assert "line 39" not in snap.text or snap.text.startswith("line 40")

    def test_tail_larger_than_file(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        p.write_text("a\nb\nc\n")
        snap = read_log(p, tail=100)
        assert snap.line_count == 3

    def test_since_filter(self, tmp_path: Path):
        cutoff = datetime(2026, 4, 27, 12, 0, 0, tzinfo=timezone.utc)
        before = (cutoff - timedelta(hours=1)).isoformat()
        after = (cutoff + timedelta(hours=1)).isoformat()
        p = tmp_path / "log.txt"
        p.write_text(f"{before} early entry\n{after} late entry 1\n{after} late entry 2\nno timestamp here\n")
        snap = read_log(p, since=cutoff.isoformat())
        assert snap.line_count == 2
        assert "early entry" not in snap.text
        assert "late entry 1" in snap.text

    def test_both_tail_and_since_raises(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        p.write_text("x\n")
        with pytest.raises(SnapshotError, match="not both"):
            read_log(p, tail=10, since="2026-01-01T00:00:00Z")

    def test_negative_tail_raises(self, tmp_path: Path):
        p = tmp_path / "log.txt"
        p.write_text("x\n")
        with pytest.raises(SnapshotError, match="positive"):
            read_log(p, tail=0)

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(SnapshotError, match="not found"):
            read_log(tmp_path / "nope.log")

    def test_oversize_log_refused(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        p = tmp_path / "huge.log"
        p.write_bytes(b"a\n" * 10)
        monkeypatch.setattr("pretorin.evidence.snapshot.MAX_LOG_BYTES", 5)
        with pytest.raises(SnapshotError, match="--log-tail"):
            read_log(p)

    def test_binary_log_refused(self, tmp_path: Path):
        p = tmp_path / "bin.log"
        p.write_bytes(b"hello\x00world\n")
        with pytest.raises(SnapshotError, match="binary"):
            read_log(p)
