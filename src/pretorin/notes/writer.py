"""Notes writer — creates markdown files with YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class LocalNote:
    """A locally stored note item."""

    control_id: str
    framework_id: str
    name: str
    content: str
    status: str = "draft"
    platform_synced: bool = False
    created_at: str = ""
    path: Path | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()


def _safe_path_component(text: str) -> str:
    """Sanitize a string for use as a path component (no traversal)."""
    cleaned = text.replace("/", "").replace("\\", "").replace("\0", "")
    cleaned = re.sub(r"\.{2,}", ".", cleaned)
    cleaned = cleaned.strip(". ")
    if not cleaned:
        raise ValueError(f"Invalid path component: {text!r}")
    return cleaned


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].rstrip("-")


def _format_frontmatter(note: LocalNote) -> str:
    """Format YAML frontmatter for a note file."""
    lines = [
        "---",
        f"control_id: {note.control_id}",
        f"framework_id: {note.framework_id}",
        f"status: {note.status}",
        f"platform_synced: {str(note.platform_synced).lower()}",
        f"created_at: {note.created_at}",
    ]
    lines.append("---")
    return "\n".join(lines)


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file."""
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

    fm: dict[str, str] = {}
    for line in fm_text.split("\n"):
        if ":" in line:
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()

    return fm, body


class NotesWriter:
    """Writes and reads local note markdown files."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd() / "notes"

    def write(self, note: LocalNote) -> Path:
        """Write a note item to a markdown file.

        Creates: notes/<framework>/<control-id>/<slug>.md

        Returns:
            Path to the created file.
        """
        slug = _slugify(note.name)
        safe_framework = _safe_path_component(note.framework_id)
        safe_control = _safe_path_component(note.control_id)
        dir_path = self.base_dir / safe_framework / safe_control
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{slug}.md"
        if not file_path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError(f"Path traversal detected: {file_path}")

        frontmatter = _format_frontmatter(note)
        file_content = f"{frontmatter}\n\n{note.content}\n"

        file_path.write_text(file_content)
        note.path = file_path
        return file_path

    def read(self, path: Path) -> LocalNote:
        """Parse a note markdown file back to a LocalNote model."""
        content = path.read_text()
        fm, body = _parse_frontmatter(content)

        return LocalNote(
            control_id=fm.get("control_id", ""),
            framework_id=fm.get("framework_id", ""),
            name=path.stem,
            content=body,
            status=fm.get("status", "draft"),
            platform_synced=fm.get("platform_synced", "false").lower() == "true",
            created_at=fm.get("created_at", ""),
            path=path,
        )

    def list_local(self, framework_id: str | None = None) -> list[LocalNote]:
        """List all local note files."""
        if not self.base_dir.exists():
            return []

        search_dir = self.base_dir / _safe_path_component(framework_id) if framework_id else self.base_dir

        if not search_dir.exists():
            return []

        results = []
        for md_file in sorted(search_dir.rglob("*.md")):
            try:
                results.append(self.read(md_file))
            except Exception:
                continue

        return results
