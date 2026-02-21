"""Evidence sync — push local evidence to the Pretorin platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pretorin.client.api import PretorianClient
from pretorin.client.models import EvidenceCreate
from pretorin.evidence.writer import EvidenceWriter, LocalEvidence, _format_frontmatter


@dataclass
class SyncResult:
    """Result of an evidence sync operation."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped) + len(self.errors)


class EvidenceSync:
    """Syncs local evidence files to the Pretorin platform."""

    def __init__(self, evidence_dir: Path | None = None) -> None:
        self.writer = EvidenceWriter(evidence_dir)

    async def push(
        self,
        client: PretorianClient,
        dry_run: bool = False,
    ) -> SyncResult:
        """Push local evidence to the platform.

        New evidence (no platform_id) gets created on the platform.
        The local file is updated with the platform_id in frontmatter.

        Args:
            client: Authenticated PretorianClient.
            dry_run: If True, don't actually create anything.

        Returns:
            SyncResult with counts of created/skipped/errored items.
        """
        result = SyncResult()
        evidence_items = self.writer.list_local()

        for ev in evidence_items:
            if ev.platform_id:
                result.skipped.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}")
                continue

            if dry_run:
                result.created.append(f"[dry-run] {ev.framework_id}/{ev.control_id}/{ev.name}")
                continue

            try:
                create_data = EvidenceCreate(
                    name=ev.name,
                    description=ev.description,
                    evidence_type=ev.evidence_type,
                    source="cli",
                    control_id=ev.control_id,
                    framework_id=ev.framework_id,
                )
                response = await client.create_evidence("", create_data)
                platform_id = response.get("id", "")

                if platform_id and ev.path:
                    # Update local file with platform_id
                    ev.platform_id = platform_id
                    self._update_frontmatter(ev)

                result.created.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}")

            except Exception as e:
                result.errors.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}: {e}")

        return result

    @staticmethod
    def _update_frontmatter(evidence: LocalEvidence) -> None:
        """Rewrite a file's frontmatter with updated platform_id."""
        if not evidence.path or not evidence.path.exists():
            return

        content = evidence.path.read_text()

        # Split on frontmatter delimiters
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
                new_fm = _format_frontmatter(evidence)
                evidence.path.write_text(f"{new_fm}\n{body}")
