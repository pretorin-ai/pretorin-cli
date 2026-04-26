"""Evidence writer — creates markdown files with YAML frontmatter."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from pretorin.local_file import (
    parse_frontmatter,
    safe_path_component,
    slugify,
)

# Backward-compatible aliases for existing callers/tests.
_safe_path_component = safe_path_component
_slugify = slugify
_parse_frontmatter = parse_frontmatter

logger = logging.getLogger(__name__)


@dataclass
class LocalEvidence:
    """A locally stored evidence item.

    Issue #79: `evidence_type` is required. Existing on-disk evidence
    files whose frontmatter is missing the field will fail to reconstruct
    with a clean TypeError — add the field manually (the canonical values
    are listed in pretorin.evidence.types.VALID_EVIDENCE_TYPES).
    """

    control_id: str
    framework_id: str
    name: str
    description: str
    evidence_type: str
    status: str = "draft"
    collected_at: str = ""
    platform_id: str | None = None
    path: Path | None = None
    code_file_path: str | None = None
    code_line_numbers: str | None = None
    code_snippet: str | None = None
    code_repository: str | None = None
    code_commit_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.collected_at:
            self.collected_at = datetime.now(timezone.utc).isoformat()


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
    if evidence.code_file_path:
        lines.append(f"code_file_path: {evidence.code_file_path}")
    if evidence.code_line_numbers:
        lines.append(f"code_line_numbers: {evidence.code_line_numbers}")
    if evidence.code_repository:
        lines.append(f"code_repository: {evidence.code_repository}")
    if evidence.code_commit_hash:
        lines.append(f"code_commit_hash: {evidence.code_commit_hash}")
    lines.append("---")
    return "\n".join(lines)


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
        safe_framework = _safe_path_component(evidence.framework_id)
        safe_control = _safe_path_component(evidence.control_id)
        dir_path = self.base_dir / safe_framework / safe_control
        dir_path.mkdir(parents=True, exist_ok=True)

        file_path = dir_path / f"{slug}.md"
        # Final check: resolved path must be under base_dir
        if not file_path.resolve().is_relative_to(self.base_dir.resolve()):
            raise ValueError(f"Path traversal detected: {file_path}")

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

        # Issue #79: legacy on-disk files may be missing `evidence_type`, and
        # previous versions of the CLI silently defaulted to the non-canonical
        # string "documentation" which now fails pydantic validation downstream.
        # Fall back to the canonical "other" and warn loudly so the user knows
        # to fix the frontmatter.
        raw_type = fm.get("evidence_type")
        if not raw_type:
            logger.warning(
                "Evidence file %s is missing 'evidence_type' frontmatter; "
                "defaulting to 'other'. Add the field manually to tag it correctly.",
                path,
            )
            raw_type = "other"

        return LocalEvidence(
            control_id=fm.get("control_id", ""),
            framework_id=fm.get("framework_id", ""),
            name=name,
            description=description,
            evidence_type=raw_type,
            status=fm.get("status", "draft"),
            collected_at=fm.get("collected_at", ""),
            platform_id=fm.get("platform_id"),
            path=path,
            code_file_path=fm.get("code_file_path"),
            code_line_numbers=fm.get("code_line_numbers"),
            code_repository=fm.get("code_repository"),
            code_commit_hash=fm.get("code_commit_hash"),
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
        search_dir = self.base_dir / _safe_path_component(framework_id) if framework_id else self.base_dir

        if not search_dir.exists():
            return []

        for md_file in sorted(search_dir.rglob("*.md")):
            try:
                results.append(self.read(md_file))
            except Exception:
                continue

        return results
