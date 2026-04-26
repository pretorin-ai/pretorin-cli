"""Narrative writer — creates markdown files with YAML frontmatter."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pretorin.local_file import (
    parse_frontmatter,
    safe_path_component,
    slugify,
)

# Backward-compatible aliases so existing callers/tests can still import
# the underscore-prefixed names from this module.
_safe_path_component = safe_path_component
_slugify = slugify
_parse_frontmatter = parse_frontmatter


@dataclass
class LocalNarrative:
    """A locally stored narrative item."""

    control_id: str
    framework_id: str
    name: str
    content: str
    status: str = "draft"
    is_ai_generated: bool = False
    platform_synced: bool = False
    created_at: str = ""
    path: Path | None = None

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


def _format_frontmatter(narrative: LocalNarrative) -> str:
    """Format YAML frontmatter for a narrative file."""
    lines = [
        "---",
        f"control_id: {narrative.control_id}",
        f"framework_id: {narrative.framework_id}",
        f"status: {narrative.status}",
        f"is_ai_generated: {str(narrative.is_ai_generated).lower()}",
        f"platform_synced: {str(narrative.platform_synced).lower()}",
        f"created_at: {narrative.created_at}",
    ]
    lines.append("---")
    return "\n".join(lines)


class NarrativeWriter:
    """Writes and reads local narrative markdown files."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd() / "narratives"

    def write(self, narrative: LocalNarrative) -> Path:
        """Write a narrative item to a markdown file.

        Creates: narratives/<framework>/<control-id>/<slug>.md

        Returns:
            Path to the created file.
        """
        slug = _slugify(narrative.name)
        safe_framework = _safe_path_component(narrative.framework_id)
        safe_control = _safe_path_component(narrative.control_id)
        dir_path = self.base_dir / safe_framework / safe_control
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{slug}.md"
        if not file_path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError(f"Path traversal detected: {file_path}")

        frontmatter = _format_frontmatter(narrative)
        # No heading — headings are forbidden in narratives
        file_content = f"{frontmatter}\n\n{narrative.content}\n"

        file_path.write_text(file_content)
        narrative.path = file_path
        return file_path

    def read(self, path: Path) -> LocalNarrative:
        """Parse a narrative markdown file back to a LocalNarrative model."""
        content = path.read_text()
        fm, body = _parse_frontmatter(content)

        return LocalNarrative(
            control_id=fm.get("control_id", ""),
            framework_id=fm.get("framework_id", ""),
            name=path.stem,
            content=body,
            status=fm.get("status", "draft"),
            is_ai_generated=fm.get("is_ai_generated", "false").lower() == "true",
            platform_synced=fm.get("platform_synced", "false").lower() == "true",
            created_at=fm.get("created_at", ""),
            path=path,
        )

    def list_local(self, framework_id: str | None = None) -> list[LocalNarrative]:
        """List all local narrative files."""
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
