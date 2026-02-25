"""Evidence writer — creates markdown files with YAML frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class LocalEvidence:
    """A locally stored evidence item."""

    control_id: str
    framework_id: str
    name: str
    description: str
    evidence_type: str = "documentation"
    status: str = "draft"
    collected_at: str = ""
    platform_id: str | None = None
    path: Path | None = None

    def __post_init__(self) -> None:
        if not self.collected_at:
            self.collected_at = datetime.now(UTC).isoformat()


def _slugify(text: str) -> str:
    """Convert text to a filesystem-safe slug."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:80].rstrip("-")


def _format_frontmatter(evidence: LocalEvidence) -> str:
    """Format YAML frontmatter for an evidence file."""
    lines = [
        "---",
        f"control_id: {evidence.control_id}",
        f"framework_id: {evidence.framework_id}",
        f"evidence_type: {evidence.evidence_type}",
        f"status: {evidence.status}",
        f"collected_at: {evidence.collected_at}",
    ]
    if evidence.platform_id:
        lines.append(f"platform_id: {evidence.platform_id}")
    lines.append("---")
    return "\n".join(lines)


def _parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter from a markdown file.

    Returns:
        Tuple of (frontmatter dict, body text).
    """
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


class EvidenceWriter:
    """Writes and reads local evidence markdown files."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or Path.cwd() / "evidence"

    def write(self, evidence: LocalEvidence) -> Path:
        """Write an evidence item to a markdown file.

        Creates: evidence/<framework>/<control-id>/<slug>.md

        Returns:
            Path to the created file.
        """
        slug = _slugify(evidence.name)
        dir_path = self.base_dir / evidence.framework_id / evidence.control_id
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{slug}.md"

        frontmatter = _format_frontmatter(evidence)
        content = f"{frontmatter}\n\n# {evidence.name}\n\n{evidence.description}\n"

        file_path.write_text(content)
        evidence.path = file_path
        return file_path

    def read(self, path: Path) -> LocalEvidence:
        """Parse an evidence markdown file back to a LocalEvidence model.

        Args:
            path: Path to the evidence markdown file.

        Returns:
            LocalEvidence parsed from the file.
        """
        content = path.read_text()
        fm, body = _parse_frontmatter(content)

        # Extract name from first heading
        name = ""
        for line in body.split("\n"):
            if line.startswith("# "):
                name = line[2:].strip()
                break

        # Extract description (everything after the first heading)
        desc_lines = []
        found_heading = False
        for line in body.split("\n"):
            if line.startswith("# ") and not found_heading:
                found_heading = True
                continue
            if found_heading:
                desc_lines.append(line)
        description = "\n".join(desc_lines).strip()

        return LocalEvidence(
            control_id=fm.get("control_id", ""),
            framework_id=fm.get("framework_id", ""),
            name=name,
            description=description,
            evidence_type=fm.get("evidence_type", "documentation"),
            status=fm.get("status", "draft"),
            collected_at=fm.get("collected_at", ""),
            platform_id=fm.get("platform_id"),
            path=path,
        )

    def list_local(self, framework_id: str | None = None) -> list[LocalEvidence]:
        """List all local evidence files.

        Args:
            framework_id: Optional filter by framework.

        Returns:
            List of LocalEvidence items.
        """
        if not self.base_dir.exists():
            return []

        results = []
        search_dir = self.base_dir / framework_id if framework_id else self.base_dir

        if not search_dir.exists():
            return []

        for md_file in sorted(search_dir.rglob("*.md")):
            try:
                results.append(self.read(md_file))
            except Exception:
                continue

        return results
