"""Narrative sync — push local narratives to the Pretorin platform."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pretorin.client.api import PretorianClient
from pretorin.narrative.writer import LocalNarrative, NarrativeWriter, _format_frontmatter

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a narrative sync operation."""

    pushed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.pushed) + len(self.skipped) + len(self.errors)


class NarrativeSync:
    """Syncs local narrative files to the Pretorin platform."""

    def __init__(self, narrative_dir: Path | None = None) -> None:
        from pretorin.client.config import Config

        config = Config()
        self._system_id = config.active_system_id or ""
        if not self._system_id:
            raise ValueError("No active system set. Run: pretorin context set --system <id>")
        self.writer = NarrativeWriter(narrative_dir)

    async def push(
        self,
        client: PretorianClient,
        dry_run: bool = False,
    ) -> SyncResult:
        """Push local narratives to the platform.

        Unsynced narratives (platform_synced=false) are pushed.
        The local file is updated with platform_synced=true after success.

        Args:
            client: Authenticated PretorianClient.
            dry_run: If True, don't actually push anything.

        Returns:
            SyncResult with counts of pushed/skipped/errored items.
        """
        result = SyncResult()
        narratives = self.writer.list_local()
        logger.debug("Starting narrative sync: %d local items found", len(narratives))

        for narr in narratives:
            label = f"{narr.framework_id}/{narr.control_id}/{narr.name}"

            if narr.platform_synced:
                logger.debug("Skipping already-synced narrative: %s", label)
                result.skipped.append(label)
                continue

            if dry_run:
                result.pushed.append(f"[dry-run] {label}")
                continue

            try:
                await client.update_narrative(
                    system_id=self._system_id,
                    control_id=narr.control_id,
                    framework_id=narr.framework_id,
                    narrative=narr.content,
                    is_ai_generated=narr.is_ai_generated,
                )

                if narr.path:
                    narr.platform_synced = True
                    self._update_frontmatter(narr)

                result.pushed.append(label)

            except Exception as e:
                logger.warning("Narrative sync error for %s: %s", label, e)
                result.errors.append(f"{label}: {e}")

        logger.debug(
            "Narrative sync complete: pushed=%d skipped=%d errors=%d",
            len(result.pushed),
            len(result.skipped),
            len(result.errors),
        )
        return result

    @staticmethod
    def _update_frontmatter(narrative: LocalNarrative) -> None:
        """Rewrite a file's frontmatter with updated platform_synced."""
        if not narrative.path or not narrative.path.exists():
            return

        content = narrative.path.read_text()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
                new_fm = _format_frontmatter(narrative)
                narrative.path.write_text(f"{new_fm}\n{body}")
