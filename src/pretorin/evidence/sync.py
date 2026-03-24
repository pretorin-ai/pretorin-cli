"""Evidence sync — push local evidence to the Pretorin platform."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pretorin.client.api import PretorianClient
from pretorin.evidence.writer import EvidenceWriter, LocalEvidence, _format_frontmatter
from pretorin.workflows.compliance_updates import upsert_evidence

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of an evidence sync operation."""

    created: list[str] = field(default_factory=list)
    reused: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    # Deprecated: retained for JSON output compatibility.
    events: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.reused) + len(self.skipped) + len(self.errors)


class EvidenceSync:
    """Syncs local evidence files to the Pretorin platform."""

    def __init__(self, evidence_dir: Path | None = None, system_id: str | None = None) -> None:
        if system_id:
            self._system_id = system_id
        else:
            from pretorin.client.config import Config

            config = Config()
            self._system_id = config.active_system_id or ""
        if not self._system_id:
            raise ValueError("No active system set. Run: pretorin context set --system <id>")
        self.writer = EvidenceWriter(evidence_dir)

    async def push(
        self,
        client: PretorianClient,
        dry_run: bool = False,
    ) -> SyncResult:
        """Push local evidence to the platform.

        New evidence (no platform_id) is upserted to the platform.
        The local file is updated with the platform_id in frontmatter.

        Args:
            client: Authenticated PretorianClient.
            dry_run: If True, don't actually create anything.

        Returns:
            SyncResult with counts of created/skipped/errored items.
        """
        result = SyncResult()
        evidence_items = self.writer.list_local()
        logger.debug("Starting evidence sync: %d local items found", len(evidence_items))

        for ev in evidence_items:
            if ev.platform_id:
                logger.debug("Skipping already-synced evidence: %s/%s/%s", ev.framework_id, ev.control_id, ev.name)
                result.skipped.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}")
                continue

            if dry_run:
                result.created.append(f"[dry-run] {ev.framework_id}/{ev.control_id}/{ev.name}")
                continue

            try:
                sync_result = await upsert_evidence(
                    client,
                    system_id=self._system_id,
                    name=ev.name,
                    description=ev.description,
                    evidence_type=ev.evidence_type,
                    source="cli",
                    control_id=ev.control_id,
                    framework_id=ev.framework_id,
                )
                platform_id = sync_result.evidence_id

                if platform_id:
                    if ev.path:
                        # Update local file with platform_id
                        ev.platform_id = platform_id
                        self._update_frontmatter(ev)

                label = f"{ev.framework_id}/{ev.control_id}/{ev.name}"
                if sync_result.created:
                    result.created.append(label)
                else:
                    result.reused.append(label)
                if sync_result.link_error:
                    result.errors.append(f"{label} link: {sync_result.link_error}")

            except Exception as e:
                logger.warning("Evidence sync error for %s/%s/%s: %s", ev.framework_id, ev.control_id, ev.name, e)
                result.errors.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}: {e}")

        logger.debug(
            "Evidence sync complete: created=%d reused=%d skipped=%d errors=%d",
            len(result.created),
            len(result.reused),
            len(result.skipped),
            len(result.errors),
        )
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
