"""Notes sync — push local notes to the Pretorin platform."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from pretorin.client.api import PretorianClient
from pretorin.notes.writer import LocalNote, NotesWriter, _format_frontmatter

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a notes sync operation."""

    pushed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.pushed) + len(self.skipped) + len(self.errors)


class NotesSync:
    """Syncs local note files to the Pretorin platform (append-only)."""

    def __init__(self, notes_dir: Path | None = None, system_id: str | None = None) -> None:
        if system_id:
            self._system_id = system_id
        else:
            from pretorin.client.config import Config

            config = Config()
            self._system_id = config.active_system_id or ""
        if not self._system_id:
            raise ValueError("No active system set. Run: pretorin context set --system <id>")
        self.writer = NotesWriter(notes_dir)

    async def push(
        self,
        client: PretorianClient,
        dry_run: bool = False,
    ) -> SyncResult:
        """Push local notes to the platform.

        Unsynced notes (platform_synced=false) are pushed.
        Notes are append-only on the platform.
        The local file is updated with platform_synced=true after success.

        Args:
            client: Authenticated PretorianClient.
            dry_run: If True, don't actually push anything.

        Returns:
            SyncResult with counts of pushed/skipped/errored items.
        """
        result = SyncResult()
        notes = self.writer.list_local()
        logger.debug("Starting notes sync: %d local items found", len(notes))

        for note in notes:
            label = f"{note.framework_id}/{note.control_id}/{note.name}"

            if note.platform_synced:
                logger.debug("Skipping already-synced note: %s", label)
                result.skipped.append(label)
                continue

            if dry_run:
                result.pushed.append(f"[dry-run] {label}")
                continue

            try:
                await client.add_control_note(
                    system_id=self._system_id,
                    control_id=note.control_id,
                    framework_id=note.framework_id,
                    content=note.content,
                    source="cli",
                )

                if note.path:
                    note.platform_synced = True
                    self._update_frontmatter(note)

                result.pushed.append(label)

            except Exception as e:
                logger.warning("Notes sync error for %s: %s", label, e)
                result.errors.append(f"{label}: {e}")

        logger.debug(
            "Notes sync complete: pushed=%d skipped=%d errors=%d",
            len(result.pushed),
            len(result.skipped),
            len(result.errors),
        )
        return result

    @staticmethod
    def _update_frontmatter(note: LocalNote) -> None:
        """Rewrite a file's frontmatter with updated platform_synced."""
        if not note.path or not note.path.exists():
            return

        content = note.path.read_text()

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                body = parts[2]
                new_fm = _format_frontmatter(note)
                note.path.write_text(f"{new_fm}\n{body}")
