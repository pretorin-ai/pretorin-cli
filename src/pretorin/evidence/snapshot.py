"""Read code or log content from disk for embedding in evidence descriptions.

Issue #88. Two entry points:

- ``read_code(path, line_range)`` — slice a source file, refuse binaries,
  enforce a 256KB cap. Caller passes the slicing range; without it the
  whole file is captured up to the cap (and an error is raised when the
  cap is exceeded so the user knows to pass ``--code-lines``).
- ``read_log(path, tail, since)`` — capture a log tail or a since-window.
  Logs are capped at 50MB (vs 256KB for source files) since real
  production logs are routinely multi-megabyte. Tail uses
  ``collections.deque`` over the file iterator — simpler than seek-from-end,
  correct on UTF-8 boundaries, fast enough at the 50MB cap.

Both raise :class:`SnapshotError` on user-facing failures (missing path,
binary content, oversize). Callers should map the exception to a clean
CLI error and abort before any platform write happens.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

MAX_CODE_BYTES: Final[int] = 256 * 1024
MAX_LOG_BYTES: Final[int] = 50 * 1024 * 1024
DEFAULT_LOG_TAIL: Final[int] = 200


class SnapshotError(Exception):
    """User-actionable error from snapshot capture."""


@dataclass(frozen=True)
class CodeSnapshot:
    """A captured slice of a source file."""

    text: str
    path: str
    line_range: str | None  # human-readable, e.g. "12-30" or None for whole file
    line_count: int


@dataclass(frozen=True)
class LogSnapshot:
    """A captured slice of a log file."""

    text: str
    path: str
    line_count: int
    captured_at: datetime


def _parse_line_range(spec: str) -> tuple[int, int]:
    """Parse a 1-indexed inclusive range like ``"12-30"`` or ``"42"``.

    Both endpoints must be positive and start <= end.
    """
    raw = spec.strip()
    if not raw:
        raise SnapshotError("Empty --code-lines value.")
    if "-" in raw:
        head, _, tail = raw.partition("-")
        try:
            start, end = int(head), int(tail)
        except ValueError as exc:
            raise SnapshotError(f"Invalid --code-lines '{spec}'; expected N or N-M.") from exc
    else:
        try:
            start = end = int(raw)
        except ValueError as exc:
            raise SnapshotError(f"Invalid --code-lines '{spec}'; expected N or N-M.") from exc
    if start < 1 or end < start:
        raise SnapshotError(f"Invalid --code-lines '{spec}'; must be positive and start <= end.")
    return start, end


def _is_binary(sample: bytes) -> bool:
    """Return True if the byte sample looks binary.

    Two heuristics: any null byte (definitive), or failure to decode as
    UTF-8 (covers most legitimate text encodings these days).
    """
    if b"\x00" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def read_code(path: str | Path, line_range: str | None = None) -> CodeSnapshot:
    """Read a source file slice for inline evidence capture.

    Args:
        path: Path to the source file.
        line_range: Optional 1-indexed inclusive range like ``"12-30"`` or ``"42"``.
            When omitted, the whole file is captured if it fits under
            :data:`MAX_CODE_BYTES`; otherwise an error tells the user to slice.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise SnapshotError(f"Source file not found: {path}")

    raw = p.read_bytes()
    if _is_binary(raw[:8192]):
        raise SnapshotError(f"Refusing to capture binary file: {path}. Capture is intended for text/source content.")

    if line_range is None:
        if len(raw) > MAX_CODE_BYTES:
            raise SnapshotError(
                f"File {path} is {len(raw)} bytes (> {MAX_CODE_BYTES}); pass --code-lines to capture a slice."
            )
        text = raw.decode("utf-8")
        return CodeSnapshot(
            text=text,
            path=str(path),
            line_range=None,
            line_count=text.count("\n") + (1 if text and not text.endswith("\n") else 0),
        )

    start, end = _parse_line_range(line_range)
    text = raw.decode("utf-8")
    lines = text.splitlines(keepends=True)
    if start > len(lines):
        raise SnapshotError(f"--code-lines {line_range} starts past end of {path} (file has {len(lines)} lines).")
    end_idx = min(end, len(lines))
    sliced = "".join(lines[start - 1 : end_idx])
    if len(sliced.encode("utf-8")) > MAX_CODE_BYTES:
        raise SnapshotError(f"Selected slice of {path} exceeds {MAX_CODE_BYTES} bytes; narrow --code-lines.")
    return CodeSnapshot(
        text=sliced,
        path=str(path),
        line_range=f"{start}-{end_idx}" if end_idx > start else f"{start}",
        line_count=end_idx - start + 1,
    )


def _parse_since(spec: str) -> datetime:
    """Parse an RFC3339 timestamp into a timezone-aware UTC datetime.

    Python 3.10's ``datetime.fromisoformat`` does NOT accept a trailing
    ``Z`` (only 3.11+). Strip and substitute ``+00:00`` first.
    """
    raw = spec.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise SnapshotError(
            f"Invalid --log-since '{spec}'; expected RFC3339 timestamp like '2026-04-27T10:00:00Z'."
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _line_timestamp(line: str) -> datetime | None:
    """Best-effort parse of a leading RFC3339 timestamp on a log line.

    Handles the common shape ``2026-04-27T10:00:00[.fff][Z|±HH:MM] ...``.
    Returns None when no leading timestamp is present.
    """
    head = line[:35].strip()
    if not head:
        return None
    parts = head.split(maxsplit=1)
    candidate = parts[0]
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def read_log(
    path: str | Path,
    tail: int | None = None,
    since: str | None = None,
) -> LogSnapshot:
    """Read a slice of a log file by tail or since-timestamp.

    Args:
        path: Path to the log file.
        tail: Capture the last N lines.
        since: RFC3339 timestamp; capture lines whose leading timestamp
            is >= the value. Lines without a parseable timestamp are
            skipped during the since filter.

    Exactly one of ``tail`` / ``since`` should be provided. When neither
    is given, defaults to ``tail=DEFAULT_LOG_TAIL``.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise SnapshotError(f"Log file not found: {path}")

    size = p.stat().st_size
    if size > MAX_LOG_BYTES:
        raise SnapshotError(
            f"Log file {path} is {size} bytes (> {MAX_LOG_BYTES}); narrow with --log-tail or --log-since, or pre-slice."
        )

    if tail is not None and since is not None:
        raise SnapshotError("Pass either --log-tail or --log-since, not both.")
    if tail is None and since is None:
        tail = DEFAULT_LOG_TAIL

    sample = p.read_bytes()[:8192]
    if _is_binary(sample):
        raise SnapshotError(f"Refusing to capture binary log: {path}")

    captured: list[str]
    if tail is not None:
        if tail <= 0:
            raise SnapshotError("--log-tail must be a positive integer.")
        with p.open("r", encoding="utf-8", errors="replace") as f:
            captured = list(deque(f, maxlen=tail))
    else:
        assert since is not None
        cutoff = _parse_since(since)
        captured = []
        with p.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                ts = _line_timestamp(line)
                if ts is not None and ts >= cutoff:
                    captured.append(line)

    text = "".join(captured)
    return LogSnapshot(
        text=text,
        path=str(path),
        line_count=len(captured),
        captured_at=datetime.now(timezone.utc),
    )
