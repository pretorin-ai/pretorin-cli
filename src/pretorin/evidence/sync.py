"""Evidence sync — push local evidence to the Pretorin platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pretorin.client.api import PretorianClient
from pretorin.client.models import EvidenceCreate, MonitoringEventCreate
from pretorin.evidence.writer import EvidenceWriter, LocalEvidence, _format_frontmatter

# Evidence statuses that indicate the control needs review
_NEEDS_REVIEW_STATUSES = {"draft", "needs_review", "flagged"}


@dataclass
class SyncResult:
    """Result of an evidence sync operation."""

    created: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.created) + len(self.skipped) + len(self.errors)


class EvidenceSync:
    """Syncs local evidence files to the Pretorin platform."""

    def __init__(self, evidence_dir: Path | None = None) -> None:
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

        New evidence (no platform_id) gets created on the platform.
        The local file is updated with the platform_id in frontmatter.
        If evidence has a review-requiring status (draft, needs_review, flagged),
        the associated control is set to in_progress and a monitoring event is created.

        Args:
            client: Authenticated PretorianClient.
            dry_run: If True, don't actually create anything.

        Returns:
            SyncResult with counts of created/skipped/errored items.
        """
        result = SyncResult()
        evidence_items = self.writer.list_local()

        # Track controls that got new evidence needing review
        controls_needing_review: dict[str, str] = {}  # control_id -> framework_id

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
                response = await client.create_evidence(self._system_id, create_data)
                platform_id = response.get("id", "")

                if platform_id:
                    # Link evidence to the control
                    if ev.control_id:
                        try:
                            await client.link_evidence_to_control(
                                evidence_id=platform_id,
                                control_id=ev.control_id,
                                system_id=self._system_id,
                                framework_id=ev.framework_id,
                            )
                        except Exception:
                            pass  # Link failure is non-fatal

                    if ev.path:
                        # Update local file with platform_id
                        ev.platform_id = platform_id
                        self._update_frontmatter(ev)

                result.created.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}")

                # Track controls that need review based on evidence status
                if ev.status in _NEEDS_REVIEW_STATUSES and ev.control_id:
                    controls_needing_review[ev.control_id] = ev.framework_id

            except Exception as e:
                result.errors.append(f"{ev.framework_id}/{ev.control_id}/{ev.name}: {e}")

        # Update control statuses and create monitoring events for controls needing review
        if not dry_run:
            for control_id, framework_id in controls_needing_review.items():
                await self._flag_control_for_review(client, control_id, framework_id, result)

        return result

    async def _flag_control_for_review(
        self,
        client: PretorianClient,
        control_id: str,
        framework_id: str,
        result: SyncResult,
    ) -> None:
        """Update control status and create a monitoring event for review."""
        label = f"{framework_id}/{control_id}"

        # Update control status to partially_implemented (triggers regression detection)
        try:
            await client.update_control_status(
                system_id=self._system_id,
                control_id=control_id,
                status="partially_implemented",
                framework_id=framework_id,
            )
        except Exception as e:
            result.errors.append(f"{label} status update: {e}")
            return

        # Create monitoring event
        try:
            event = MonitoringEventCreate(
                event_type="compliance_check",
                title=f"New evidence requires review: {control_id.upper()}",
                description=(
                    f"CLI evidence push added new findings for control "
                    f"{control_id.upper()} ({framework_id}). "
                    f"Control status set to partially_implemented pending review."
                ),
                severity="high",
                control_id=control_id,
            )
            await client.create_monitoring_event(self._system_id, event)
            result.events.append(label)
        except Exception as e:
            result.errors.append(f"{label} monitoring event: {e}")

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
