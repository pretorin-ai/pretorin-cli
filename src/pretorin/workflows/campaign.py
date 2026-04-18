"""Shared campaign orchestration for CLI and MCP-driven execution."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import logging
import sys
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, cast

from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pretorin.cli.context import resolve_execution_context
from pretorin.cli.output import is_json_mode
from pretorin.client import PretorianClient
from pretorin.client.api import PretorianClientError
from pretorin.client.models import EvidenceBatchItemCreate, OrgPolicyQuestionnaireResponse, ScopeResponse
from pretorin.scope import ExecutionScope
from pretorin.utils import normalize_control_id

logger = logging.getLogger(__name__)

ROMEBOT_COLOR = "#EAB536"
OUTPUT_AUTO = "auto"
OUTPUT_LIVE = "live"
OUTPUT_COMPACT = "compact"
OUTPUT_JSON = "json"
ITEM_PENDING = "pending"
ITEM_CLAIMED = "claimed"
ITEM_PROPOSED = "proposed"
ITEM_SUCCEEDED = "succeeded"
ITEM_FAILED = "failed"
ITEM_SKIPPED = "skipped"
LEASE_TTL_SECONDS = 300


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_after(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _slugify(value: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-") or "campaign"


def _safe_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _safe_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_safe_json(item) for item in value]
    return value


def _safe_json_dict(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], _safe_json(value))


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


@dataclass
class WorkflowContextSnapshot:
    """Read model of the platform workflow inputs for one campaign."""

    domain: str
    subject: str
    scope: dict[str, str] = field(default_factory=dict)
    workflow_state: dict[str, Any] = field(default_factory=dict)
    analytics_summary: dict[str, Any] = field(default_factory=dict)
    family_analytics: dict[str, Any] = field(default_factory=dict)
    extras: dict[str, Any] = field(default_factory=dict)
    platform_api_base_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_dict(asdict(self))


@dataclass
class CampaignRunRequest:
    """Normalized request for one campaign run."""

    domain: str
    mode: str
    apply: bool
    output: str
    concurrency: int
    max_retries: int
    checkpoint_path: Path
    working_directory: Path
    system: str | None = None
    framework_id: str | None = None
    family_id: str | None = None
    control_ids: list[str] = field(default_factory=list)
    all_controls: bool = False
    artifacts: str = "both"
    review_job: str | None = None
    policy_ids: list[str] = field(default_factory=list)
    all_incomplete: bool = False

    def identity(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "mode": self.mode,
            "apply": self.apply,
            "system": self.system,
            "framework_id": self.framework_id,
            "family_id": self.family_id,
            "control_ids": list(self.control_ids),
            "all_controls": self.all_controls,
            "artifacts": self.artifacts,
            "review_job": self.review_job,
            "policy_ids": list(self.policy_ids),
            "all_incomplete": self.all_incomplete,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self.identity()
        payload.update(
            {
                "output": self.output,
                "concurrency": self.concurrency,
                "max_retries": self.max_retries,
                "checkpoint_path": str(self.checkpoint_path),
                "working_directory": str(self.working_directory),
            }
        )
        return _safe_json_dict(payload)


@dataclass
class CampaignItem:
    """One unit of campaign work."""

    item_id: str
    label: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_dict(asdict(self))


@dataclass
class CampaignEvent:
    """Structured lifecycle event emitted by the runner."""

    event_type: str
    domain: str
    mode: str
    message: str
    item_id: str | None = None
    label: str | None = None
    attempt: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    at: str = field(default_factory=_utcnow)

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_dict(asdict(self))


@dataclass
class CampaignItemState:
    """Checkpointed per-item state."""

    item: dict[str, Any]
    status: str = ITEM_PENDING
    attempts: int = 0
    proposal: dict[str, Any] = field(default_factory=dict)
    receipts: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    claimed_at: str | None = None
    lease_owner: str | None = None
    lease_expires_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_dict(asdict(self))


@dataclass
class CampaignCheckpoint:
    """On-disk operational state for resuming campaigns."""

    version: int
    identity: dict[str, Any]
    request: dict[str, Any]
    output: str
    created_at: str
    updated_at: str
    workflow_snapshot: dict[str, Any]
    items: dict[str, CampaignItemState] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "version": self.version,
            "identity": self.identity,
            "request": self.request,
            "output": self.output,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "workflow_snapshot": self.workflow_snapshot,
            "items": {item_id: state.to_dict() for item_id, state in self.items.items()},
            "events": self.events,
        }
        return _safe_json_dict(payload)


@dataclass
class CampaignRunSummary:
    """Campaign summary for CLI and MCP consumers."""

    domain: str
    mode: str
    apply: bool
    output_mode: str
    checkpoint_path: str
    workflow_snapshot: dict[str, Any]
    total: int
    pending: int
    claimed: int
    proposed: int
    succeeded: int
    failed: int
    skipped: int
    retries_used: int
    items: dict[str, dict[str, Any]]
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    claimed_items: list[dict[str, Any]] = field(default_factory=list)
    status_snapshot: str = ""
    prepared_only: bool = False
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _safe_json_dict(asdict(self))


class CampaignPresenter:
    """Presentation interface for campaign runs."""

    def start(self, request: CampaignRunRequest, snapshot: WorkflowContextSnapshot, total: int) -> None:
        """Handle run start."""

    def handle(self, event: CampaignEvent, checkpoint: CampaignCheckpoint) -> None:
        """Handle one event."""

    def finish(self, summary: CampaignRunSummary) -> None:
        """Handle run completion."""

    def close(self) -> None:
        """Release any presentation resources."""


class CompactCampaignPresenter(CampaignPresenter):
    """Append-only presenter for transcripts and non-TTY environments."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def start(self, request: CampaignRunRequest, snapshot: WorkflowContextSnapshot, total: int) -> None:
        self.console.print(
            f"[{ROMEBOT_COLOR}][°□°][/{ROMEBOT_COLOR}] "
            f"{snapshot.subject} | {request.domain}:{request.mode} | "
            f"{'apply' if request.apply else 'preview'} | {total} item(s)"
        )

    def handle(self, event: CampaignEvent, checkpoint: CampaignCheckpoint) -> None:
        label = event.label or event.item_id or "campaign"
        attempt = f" attempt={event.attempt}" if event.attempt else ""
        self.console.print(f"{label}: {event.event_type}{attempt} - {event.message}")

    def finish(self, summary: CampaignRunSummary) -> None:
        tail = "prepared for external execution" if summary.prepared_only else "completed"
        self.console.print(
            f"[{ROMEBOT_COLOR}][°◡°]/[/{ROMEBOT_COLOR}] "
            f"{tail} {summary.domain}:{summary.mode} | "
            f"pending={summary.pending} claimed={summary.claimed} proposed={summary.proposed} "
            f"succeeded={summary.succeeded} failed={summary.failed} skipped={summary.skipped}"
        )


class LiveCampaignPresenter(CampaignPresenter):
    """TTY-oriented dashboard presenter."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._live: Live | None = None
        self._request: CampaignRunRequest | None = None
        self._snapshot: WorkflowContextSnapshot | None = None
        self._total = 0
        self._recent: deque[str] = deque(maxlen=8)
        self._active: dict[str, str] = {}
        self._milestones: set[int] = set()

    def start(self, request: CampaignRunRequest, snapshot: WorkflowContextSnapshot, total: int) -> None:
        self._request = request
        self._snapshot = snapshot
        self._total = total
        run_mode = "apply" if request.apply else "preview"
        self._recent.append(f"Prepared {request.domain}:{request.mode} in {run_mode} mode")
        self._live = Live(self._render(None), console=self.console, refresh_per_second=8, transient=False)
        self._live.start()

    def handle(self, event: CampaignEvent, checkpoint: CampaignCheckpoint) -> None:
        if event.item_id and event.event_type in {"item_claimed", "item_started", "item_retrying"}:
            self._active[event.item_id] = event.message
        elif event.item_id and event.event_type in {"item_proposed", "item_applied", "item_failed", "item_skipped"}:
            self._active.pop(event.item_id, None)
        self._recent.append(f"{event.label or event.item_id or 'campaign'}: {event.message}")
        counts = _status_counts(checkpoint)
        completed = counts[ITEM_PROPOSED] + counts[ITEM_SUCCEEDED] + counts[ITEM_FAILED] + counts[ITEM_SKIPPED]
        if self._total:
            pct = int((completed / self._total) * 100)
            for milestone in (25, 50, 100):
                if pct >= milestone and milestone not in self._milestones:
                    self._milestones.add(milestone)
                    self._recent.append(f"Milestone reached: {milestone}%")
        if self._live:
            self._live.update(self._render(checkpoint))

    def finish(self, summary: CampaignRunSummary) -> None:
        self._recent.append(
            f"pending={summary.pending}, proposed={summary.proposed}, "
            f"succeeded={summary.succeeded}, failed={summary.failed}"
        )
        if self._live:
            self._live.update(self._render_summary(summary))
        self.close()

    def close(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _render(self, checkpoint: CampaignCheckpoint | None) -> Group:
        if self._request is None or self._snapshot is None:
            return Group(Text("Launching campaign..."))

        header = Panel(
            (
                f"[bold]{self._snapshot.subject}[/bold]\n"
                f"Workflow stage: {self._snapshot.workflow_state.get('lifecycle_stage', 'unknown')} | "
                f"Mode: {self._request.mode} | "
                f"Run: {'apply' if self._request.apply else 'preview'} | "
                f"Concurrency: {self._request.concurrency}"
            ),
            title=f"[{ROMEBOT_COLOR}][°□°][/{ROMEBOT_COLOR}] Platform Workflow Campaign",
            border_style="#FF9010",
        )
        stats = Table(title="Campaign Progress", show_header=True, header_style="bold")
        for name in ("Pending", "Claimed", "Proposed", "Succeeded", "Failed", "Skipped", "Retries"):
            stats.add_column(name, justify="right")

        retries = 0
        if checkpoint is not None:
            counts = _status_counts(checkpoint)
            retries = sum(max(state.attempts - 1, 0) for state in checkpoint.items.values())
        else:
            counts = {
                ITEM_PENDING: self._total,
                ITEM_CLAIMED: 0,
                ITEM_PROPOSED: 0,
                ITEM_SUCCEEDED: 0,
                ITEM_FAILED: 0,
                ITEM_SKIPPED: 0,
            }
        stats.add_row(
            str(counts[ITEM_PENDING]),
            str(counts[ITEM_CLAIMED]),
            str(counts[ITEM_PROPOSED]),
            str(counts[ITEM_SUCCEEDED]),
            str(counts[ITEM_FAILED]),
            str(counts[ITEM_SKIPPED]),
            str(retries),
        )

        workers = Table(title="Active Workers", show_header=True, header_style="bold")
        workers.add_column("Item", style="cyan")
        workers.add_column("Status")
        if self._active:
            for item_id, message in sorted(self._active.items()):
                workers.add_row(item_id, message)
        else:
            workers.add_row("-", "Waiting for work...")

        events_panel = Panel("\n".join(self._recent) if self._recent else "Campaign starting...", title="Recent Events")
        return Group(header, stats, workers, events_panel)

    def _render_summary(self, summary: CampaignRunSummary) -> Group:
        title = "Campaign Ready" if summary.prepared_only else "Campaign Complete"
        summary_panel = Panel(
            (
                f"[bold]{summary.workflow_snapshot.get('subject', '')}[/bold]\n"
                f"Pending: {summary.pending}\n"
                f"Claimed: {summary.claimed}\n"
                f"Proposed: {summary.proposed}\n"
                f"Succeeded: {summary.succeeded}\n"
                f"Failed: {summary.failed}\n"
                f"Checkpoint: {summary.checkpoint_path}"
            ),
            title=f"[{ROMEBOT_COLOR}][°◡°]/[/{ROMEBOT_COLOR}] {title}",
            border_style="#95D7E0",
        )
        events_panel = Panel("\n".join(self._recent), title="Recent Events")
        return Group(summary_panel, events_panel)


def resolve_output_mode(requested: str) -> str:
    """Resolve output mode including TTY-aware auto behavior."""
    if is_json_mode():
        return OUTPUT_JSON
    if requested == OUTPUT_AUTO:
        return OUTPUT_LIVE if sys.stdout.isatty() else OUTPUT_COMPACT
    if requested == OUTPUT_LIVE and not sys.stdout.isatty():
        return OUTPUT_COMPACT
    return requested


def default_checkpoint_path(domain: str, mode: str) -> Path:
    """Create a default checkpoint file path for a campaign."""
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(".pretorin") / "campaigns" / f"{_slugify(domain)}-{_slugify(mode)}-{stamp}.json"


def _select_presenter(output_mode: str) -> CampaignPresenter | None:
    if output_mode == OUTPUT_LIVE:
        return LiveCampaignPresenter()
    if output_mode == OUTPUT_COMPACT:
        return CompactCampaignPresenter()
    return None


def _builtin_executor_available() -> bool:
    """Return whether the optional builtin executor runtime is installed."""
    return importlib.util.find_spec("openai_codex_sdk") is not None


def _ensure_checkpoint_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _normalize_loaded_status(status: str) -> str:
    if status == "running":
        return ITEM_CLAIMED
    if status not in {ITEM_PENDING, ITEM_CLAIMED, ITEM_PROPOSED, ITEM_SUCCEEDED, ITEM_FAILED, ITEM_SKIPPED}:
        return ITEM_PENDING
    return status


def _load_checkpoint(path: Path) -> CampaignCheckpoint | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text())
    items: dict[str, CampaignItemState] = {}
    for item_id, item_state in payload.get("items", {}).items():
        loaded = CampaignItemState(**item_state)
        loaded.status = _normalize_loaded_status(loaded.status)
        items[item_id] = loaded
    return CampaignCheckpoint(
        version=int(payload.get("version", 1)),
        identity=payload.get("identity", {}),
        request=payload.get("request", {}),
        output=str(payload.get("output", OUTPUT_COMPACT)),
        created_at=str(payload.get("created_at", _utcnow())),
        updated_at=str(payload.get("updated_at", _utcnow())),
        workflow_snapshot=payload.get("workflow_snapshot", {}),
        items=items,
        events=payload.get("events", []),
    )


def _write_checkpoint(path: Path, checkpoint: CampaignCheckpoint) -> None:
    checkpoint.updated_at = _utcnow()
    _ensure_checkpoint_parent(path)
    path.write_text(json.dumps(checkpoint.to_dict(), indent=2, default=str) + "\n")


def _new_checkpoint(
    request: CampaignRunRequest,
    snapshot: WorkflowContextSnapshot,
    items: list[CampaignItem],
) -> CampaignCheckpoint:
    now = _utcnow()
    return CampaignCheckpoint(
        version=2,
        identity=request.identity(),
        request=request.to_dict(),
        output=request.output,
        created_at=now,
        updated_at=now,
        workflow_snapshot=snapshot.to_dict(),
        items={item.item_id: CampaignItemState(item=item.to_dict()) for item in items},
        events=[],
    )


def _request_from_checkpoint(path: Path, checkpoint: CampaignCheckpoint) -> CampaignRunRequest:
    request = checkpoint.request
    return CampaignRunRequest(
        domain=str(checkpoint.identity.get("domain", request.get("domain", "controls"))),
        mode=str(checkpoint.identity.get("mode", request.get("mode", "initial"))),
        apply=bool(checkpoint.identity.get("apply", request.get("apply", False))),
        output=str(checkpoint.output),
        concurrency=int(request.get("concurrency", 4)),
        max_retries=int(request.get("max_retries", 2)),
        checkpoint_path=path,
        working_directory=Path(str(request.get("working_directory", Path.cwd()))),
        system=request.get("system"),
        framework_id=request.get("framework_id"),
        family_id=request.get("family_id"),
        control_ids=[str(item) for item in request.get("control_ids", [])],
        all_controls=bool(request.get("all_controls", False)),
        artifacts=str(request.get("artifacts", "both")),
        review_job=request.get("review_job"),
        policy_ids=[str(item) for item in request.get("policy_ids", [])],
        all_incomplete=bool(request.get("all_incomplete", False)),
    )


def _record_event(
    checkpoint: CampaignCheckpoint,
    presenter: CampaignPresenter | None,
    event_type: str,
    message: str,
    *,
    item: CampaignItem | None = None,
    attempt: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    event = CampaignEvent(
        event_type=event_type,
        domain=str(checkpoint.identity.get("domain", "campaign")),
        mode=str(checkpoint.identity.get("mode", "run")),
        message=message,
        item_id=item.item_id if item else None,
        label=item.label if item else None,
        attempt=attempt,
        metadata=metadata or {},
    )
    checkpoint.events.append(event.to_dict())
    if presenter is not None:
        presenter.handle(event, checkpoint)


def _validate_checkpoint_identity(checkpoint: CampaignCheckpoint, request: CampaignRunRequest) -> None:
    if checkpoint.identity != request.identity():
        raise PretorianClientError(
            "Checkpoint identity does not match this campaign request. "
            "Use the original mode, scope, selectors, and apply/preview setting to resume."
        )


def _validate_checkpoint_environment(client: PretorianClient, snapshot: WorkflowContextSnapshot) -> None:
    """Verify the checkpoint's API environment matches the current client."""
    checkpoint_url = snapshot.platform_api_base_url
    if not checkpoint_url:
        logger.warning(
            "Campaign checkpoint does not include platform_api_base_url; "
            "cannot verify environment affinity. Consider re-preparing."
        )
        return
    current_url = client.api_base_url
    if checkpoint_url.rstrip("/") != current_url.rstrip("/"):
        raise PretorianClientError(
            f"This checkpoint was prepared against '{checkpoint_url}' but the current "
            f"API environment is '{current_url}'. Re-prepare the campaign against the "
            f"correct environment."
        )


def _lease_expired(item_state: CampaignItemState) -> bool:
    if item_state.lease_expires_at is None:
        return False
    expires = _parse_timestamp(item_state.lease_expires_at)
    return expires is not None and expires <= datetime.now(timezone.utc)


def _release_item_lease(item_state: CampaignItemState) -> None:
    item_state.lease_owner = None
    item_state.lease_expires_at = None


def _status_counts(checkpoint: CampaignCheckpoint) -> dict[str, int]:
    counts = {
        ITEM_PENDING: 0,
        ITEM_CLAIMED: 0,
        ITEM_PROPOSED: 0,
        ITEM_SUCCEEDED: 0,
        ITEM_FAILED: 0,
        ITEM_SKIPPED: 0,
    }
    for state in checkpoint.items.values():
        status = _normalize_loaded_status(state.status)
        counts[status] = counts.get(status, 0) + 1
    return counts


def _claimed_items(checkpoint: CampaignCheckpoint) -> list[dict[str, Any]]:
    claimed: list[dict[str, Any]] = []
    for item_id, state in checkpoint.items.items():
        if state.status == ITEM_CLAIMED and state.lease_owner:
            claimed.append(
                {
                    "item_id": item_id,
                    "label": state.item.get("label", item_id),
                    "lease_owner": state.lease_owner,
                    "lease_expires_at": state.lease_expires_at,
                }
            )
    return claimed


def render_campaign_snapshot(checkpoint: CampaignCheckpoint, checkpoint_path: Path) -> str:
    """Render a stable plain-text campaign snapshot for transcripts."""
    counts = _status_counts(checkpoint)
    lines = [
        f"Campaign: {checkpoint.identity.get('domain')}:{checkpoint.identity.get('mode')}",
        f"Subject: {checkpoint.workflow_snapshot.get('subject', '')}",
        f"Checkpoint: {checkpoint_path}",
        (
            "Counts: "
            f"pending={counts[ITEM_PENDING]} claimed={counts[ITEM_CLAIMED]} proposed={counts[ITEM_PROPOSED]} "
            f"succeeded={counts[ITEM_SUCCEEDED]} failed={counts[ITEM_FAILED]} skipped={counts[ITEM_SKIPPED]}"
        ),
    ]
    claimed = _claimed_items(checkpoint)
    if claimed:
        lines.append("Claims:")
        for entry in claimed[:5]:
            lines.append(f"- {entry['label']} by {entry['lease_owner']} until {entry['lease_expires_at']}")
    failures = [
        f"- {state.item.get('label', item_id)}: {state.last_error}"
        for item_id, state in checkpoint.items.items()
        if state.status == ITEM_FAILED and state.last_error
    ]
    if failures:
        lines.append("Failures:")
        lines.extend(failures[:5])
    recent = checkpoint.events[-5:]
    if recent:
        lines.append("Recent Events:")
        for event in recent:
            label = event.get("label") or event.get("item_id") or "campaign"
            lines.append(f"- {label}: {event.get('message', '')}")
    return "\n".join(lines)


def _summary_next_steps(checkpoint: CampaignCheckpoint, checkpoint_path: Path, prepared_only: bool) -> list[str]:
    if not prepared_only:
        return []
    return [
        f"Use MCP tools starting with `pretorin_get_campaign_status` against `{checkpoint_path}`.",
        (
            "Claim work with `pretorin_claim_campaign_items` and fetch item context "
            "with `pretorin_get_campaign_item_context`."
        ),
        "Submit proposals with `pretorin_submit_campaign_proposal`, then persist with `pretorin_apply_campaign`.",
        f"Attach locally with `pretorin campaign status --checkpoint {checkpoint_path}`.",
    ]


def build_campaign_summary(
    checkpoint: CampaignCheckpoint,
    checkpoint_path: Path,
    *,
    output_mode: str | None = None,
    prepared_only: bool = False,
    apply_override: bool | None = None,
) -> CampaignRunSummary:
    """Build a campaign summary from a checkpoint."""
    counts = _status_counts(checkpoint)
    retries_used = sum(max(state.attempts - 1, 0) for state in checkpoint.items.values())
    request = _request_from_checkpoint(checkpoint_path, checkpoint)
    return CampaignRunSummary(
        domain=str(checkpoint.identity.get("domain", request.domain)),
        mode=str(checkpoint.identity.get("mode", request.mode)),
        apply=apply_override if apply_override is not None else bool(checkpoint.identity.get("apply", request.apply)),
        output_mode=output_mode or checkpoint.output,
        checkpoint_path=str(checkpoint_path),
        workflow_snapshot=checkpoint.workflow_snapshot,
        total=len(checkpoint.items),
        pending=counts[ITEM_PENDING],
        claimed=counts[ITEM_CLAIMED],
        proposed=counts[ITEM_PROPOSED],
        succeeded=counts[ITEM_SUCCEEDED],
        failed=counts[ITEM_FAILED],
        skipped=counts[ITEM_SKIPPED],
        retries_used=retries_used,
        items={item_id: state.to_dict() for item_id, state in checkpoint.items.items()},
        recent_events=checkpoint.events[-10:],
        claimed_items=_claimed_items(checkpoint),
        status_snapshot=render_campaign_snapshot(checkpoint, checkpoint_path),
        prepared_only=prepared_only,
        next_steps=_summary_next_steps(checkpoint, checkpoint_path, prepared_only),
    )


def get_campaign_status(checkpoint_path: Path) -> CampaignRunSummary:
    """Load and summarize a campaign checkpoint."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    return build_campaign_summary(checkpoint, checkpoint_path)


def _scope_question_targets(scope: ScopeResponse) -> set[str]:
    review = scope.scope_review
    if review is None or not review.recommended_changes:
        raise PretorianClientError("No persisted scope review findings are available for review-fix mode.")
    matched: set[str] = set()
    question_ids = {question.id for question in scope.scope_questions}
    for change in review.recommended_changes:
        section = (change.section or "").strip().lower()
        for question in scope.scope_questions:
            if question.section.lower() == section or question.section_title.lower() == section:
                matched.add(question.id)
    return matched or question_ids


def _policy_question_targets(questionnaire: OrgPolicyQuestionnaireResponse) -> set[str]:
    review = questionnaire.policy_review
    template = questionnaire.template
    if review is None or not review.recommended_changes:
        raise PretorianClientError("No persisted policy review findings are available for review-fix mode.")
    if template is None:
        raise PretorianClientError("Policy template metadata is required for review-fix mode.")

    title_to_id = {section.title.lower(): section.section_id for section in template.sections}
    matched: set[str] = set()
    all_ids = {question.question_id for question in template.questions}
    for change in review.recommended_changes:
        section = (change.section or "").strip().lower()
        section_id = title_to_id.get(section, section)
        for question in template.questions:
            if question.section_id == section_id or section_id in question.additional_section_ids:
                matched.add(question.question_id)
    return matched or all_ids


def _scope_updates(
    scope: ScopeResponse,
    proposal: dict[str, Any],
    target_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    existing_answers = {
        str(item.get("id")): item.get("answer")
        for item in (scope.scope_qa_responses or {}).get("questions", [])
        if isinstance(item, dict)
    }
    updates: list[dict[str, str]] = []
    for item in proposal.get("questions", []):
        if not isinstance(item, dict):
            continue
        question_id = str(item.get("question_id", ""))
        if not question_id or (target_ids is not None and question_id not in target_ids):
            continue
        proposed_answer = item.get("proposed_answer")
        if proposed_answer is None:
            continue
        if (existing_answers.get(question_id) or "").strip() == str(proposed_answer).strip():
            continue
        updates.append({"question_id": question_id, "answer": str(proposed_answer)})
    return updates


def _policy_updates(
    questionnaire: OrgPolicyQuestionnaireResponse,
    proposal: dict[str, Any],
    target_ids: set[str] | None = None,
) -> list[dict[str, str]]:
    existing_answers = {
        str(item.get("id")): item.get("answer")
        for item in (questionnaire.policy_qa_responses or {}).get("questions", [])
        if isinstance(item, dict)
    }
    updates: list[dict[str, str]] = []
    for item in proposal.get("questions", []):
        if not isinstance(item, dict):
            continue
        question_id = str(item.get("question_id", ""))
        if not question_id or (target_ids is not None and question_id not in target_ids):
            continue
        proposed_answer = item.get("proposed_answer")
        if proposed_answer is None:
            continue
        if (existing_answers.get(question_id) or "").strip() == str(proposed_answer).strip():
            continue
        updates.append({"question_id": question_id, "answer": str(proposed_answer)})
    return updates


def _extract_control_review_findings(payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    if isinstance(payload.get("findings"), list):
        findings.extend(item for item in payload["findings"] if isinstance(item, dict))
    if isinstance(payload.get("results"), list):
        for result in payload["results"]:
            if isinstance(result, dict) and isinstance(result.get("findings"), list):
                findings.extend(item for item in result["findings"] if isinstance(item, dict))
    control_map: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        control_id = finding.get("target_ref") or finding.get("control_id")
        if not control_id:
            affected = finding.get("affected_control_ids") or finding.get("control_ids") or []
            if isinstance(affected, list) and affected:
                control_id = affected[0]
        if not control_id:
            continue
        normalized = normalize_control_id(str(control_id))
        control_map.setdefault(normalized, []).append(finding)
    return control_map


def _control_completion_note(mode: str, changed: list[str]) -> str:
    changes = ", ".join(changed) if changed else "no material changes"
    return f"Campaign {mode} applied. Updated: {changes}."


def _successful_batch_result(result: dict[str, Any]) -> bool:
    if result.get("error"):
        return False
    status = str(result.get("status", "")).lower()
    return status in {"ok", "success", "created", "linked", "reused"}


def _existing_evidence_indices(item_state: CampaignItemState) -> set[int]:
    receipts = item_state.receipts.get("evidence_batch")
    if not isinstance(receipts, list):
        return set()
    return {int(entry["index"]) for entry in receipts if isinstance(entry, dict) and "index" in entry}


async def _prepare_controls_context(
    client: PretorianClient,
    request: CampaignRunRequest,
) -> tuple[WorkflowContextSnapshot, list[CampaignItem]]:
    if request.system is None or request.framework_id is None:
        raise PretorianClientError("Control campaigns require --system and --framework-id.")
    system_id, framework_id = await resolve_execution_context(
        client,
        system=request.system,
        framework=request.framework_id,
    )
    system_name = (await client.get_system(system_id)).name
    scope = ExecutionScope(system_id=system_id, framework_id=framework_id)
    workflow_state = await client.get_workflow_state(system_id, framework_id)
    analytics_summary = await client.get_analytics_summary(system_id, framework_id)
    family_analytics = await client.get_family_analytics(system_id, framework_id)

    target_sources = sum(
        1 for flag in (bool(request.family_id), bool(request.control_ids), request.all_controls) if flag
    )
    if target_sources != 1:
        raise PretorianClientError("Exactly one of --family, --controls, or --all-controls is required.")

    if request.family_id:
        summaries = await client.list_controls(framework_id, request.family_id)
        family_bundle = await client.get_family_bundle(system_id, request.family_id, framework_id)
    elif request.control_ids:
        normalized = [normalize_control_id(control_id) for control_id in request.control_ids]
        all_controls = await client.list_controls(framework_id)
        summaries = [control for control in all_controls if control.id in normalized]
        family_bundle = {}
    else:
        summaries = await client.list_controls(framework_id)
        family_bundle = {}

    if not summaries:
        raise PretorianClientError("No controls matched the requested selector.")

    control_ids = [summary.id for summary in summaries]
    extras: dict[str, Any] = {"resolved_scope": {"system_id": system_id, "framework_id": framework_id}}
    if request.family_id:
        extras["family_bundle"] = _safe_json(family_bundle)
    if len(control_ids) > 1:
        extras["controls_batch"] = (await client.get_controls_batch(framework_id, control_ids)).model_dump(mode="json")

    items = [
        CampaignItem(
            item_id=control_id,
            label=control_id.upper(),
            kind="control",
            payload={"system_id": system_id, "framework_id": framework_id, "scope": _safe_json(asdict(scope))},
        )
        for control_id in control_ids
    ]
    snapshot = WorkflowContextSnapshot(
        domain="controls",
        subject=f"{system_name} / {framework_id}",
        scope={"system_id": system_id, "framework_id": framework_id},
        workflow_state=workflow_state,
        analytics_summary=analytics_summary,
        family_analytics=family_analytics,
        extras=extras,
        platform_api_base_url=client.api_base_url,
    )
    return snapshot, items


async def _prepare_policy_context(
    client: PretorianClient,
    request: CampaignRunRequest,
) -> tuple[WorkflowContextSnapshot, list[CampaignItem]]:
    listing = await client.list_org_policies()
    if request.policy_ids and request.all_incomplete:
        raise PretorianClientError("Use either --policies or --all-incomplete, not both.")
    if request.policy_ids:
        wanted = set(request.policy_ids)
        selected = [policy for policy in listing.policies if policy.id in wanted]
    else:
        selected = [policy for policy in listing.policies if (policy.policy_qa_status or "not_started") != "complete"]

    if not selected:
        raise PretorianClientError("No policies matched the requested selector.")

    extras: dict[str, Any] = {"policy_ids": [policy.id for policy in selected]}
    workflow_states: dict[str, Any] = {}
    questionnaires: dict[str, Any] = {}
    items: list[CampaignItem] = []
    for policy in selected:
        workflow_states[policy.id] = await client.get_policy_workflow_state(policy.id)
        questionnaire = await client.get_org_policy_questionnaire(policy.id)
        questionnaires[policy.id] = questionnaire.model_dump(mode="json")
        items.append(CampaignItem(item_id=policy.id, label=policy.name, kind="policy"))
    extras["policy_workflow_states"] = workflow_states
    extras["questionnaires"] = questionnaires
    snapshot = WorkflowContextSnapshot(
        domain="policy",
        subject=f"{len(items)} policy workflow(s)",
        workflow_state={"policy_ids": [policy.id for policy in selected]},
        extras=extras,
        platform_api_base_url=client.api_base_url,
    )
    return snapshot, items


async def _prepare_scope_context(
    client: PretorianClient,
    request: CampaignRunRequest,
) -> tuple[WorkflowContextSnapshot, list[CampaignItem]]:
    if request.system is None or request.framework_id is None:
        raise PretorianClientError("Scope campaigns require --system and --framework-id.")
    system_id, framework_id = await resolve_execution_context(
        client,
        system=request.system,
        framework=request.framework_id,
    )
    system_name = (await client.get_system(system_id)).name
    workflow_state = await client.get_workflow_state(system_id, framework_id)
    scope = await client.get_scope(system_id, framework_id)
    snapshot = WorkflowContextSnapshot(
        domain="scope",
        subject=f"{system_name} / {framework_id}",
        scope={"system_id": system_id, "framework_id": framework_id},
        workflow_state=workflow_state,
        extras={"scope": scope.model_dump(mode="json")},
        platform_api_base_url=client.api_base_url,
    )
    items = [
        CampaignItem(
            item_id=question.id,
            label=question.id,
            kind="scope-question",
            payload={"system_id": system_id, "framework_id": framework_id},
        )
        for question in scope.scope_questions
    ]
    return snapshot, items


async def _prepare_snapshot_and_items(
    client: PretorianClient,
    request: CampaignRunRequest,
) -> tuple[WorkflowContextSnapshot, list[CampaignItem]]:
    if request.domain == "controls":
        snapshot, items = await _prepare_controls_context(client, request)
        if request.mode == "review-fix":
            if not request.review_job:
                raise PretorianClientError("--review-job is required for controls --mode review-fix.")
            review_results = await client.get_family_review_results(snapshot.scope["system_id"], request.review_job)
            review_findings = _extract_control_review_findings(review_results)
            if not review_findings:
                raise PretorianClientError("No control review findings were found in the supplied review job.")
            snapshot.extras["review_results"] = _safe_json(review_results)
            snapshot.extras["review_findings"] = review_findings
            items = [item for item in items if item.item_id in review_findings]
            if not items:
                raise PretorianClientError("The requested selector did not intersect with any review findings.")
        return snapshot, items
    if request.domain == "policy":
        return await _prepare_policy_context(client, request)
    return await _prepare_scope_context(client, request)


async def prepare_campaign(
    client: PretorianClient,
    request: CampaignRunRequest,
    *,
    presenter: CampaignPresenter | None = None,
) -> CampaignCheckpoint:
    """Prepare a campaign checkpoint for external or builtin execution."""
    request.output = resolve_output_mode(request.output)
    snapshot, items = await _prepare_snapshot_and_items(client, request)

    checkpoint = _load_checkpoint(request.checkpoint_path)
    if checkpoint is None:
        checkpoint = _new_checkpoint(request, snapshot, items)
        _record_event(checkpoint, presenter, "run_prepared", "Campaign prepared")
        _write_checkpoint(request.checkpoint_path, checkpoint)
    else:
        _validate_checkpoint_identity(checkpoint, request)
        checkpoint.output = request.output
        checkpoint.request = request.to_dict()
        # Backfill platform_api_base_url for legacy checkpoints.
        ws = checkpoint.workflow_snapshot
        if not ws.get("platform_api_base_url"):
            ws["platform_api_base_url"] = client.api_base_url
        _record_event(checkpoint, presenter, "run_attached", "Attached to existing checkpoint")
        _write_checkpoint(request.checkpoint_path, checkpoint)

    if presenter is not None:
        presenter.start(request, snapshot, len(items))
    return checkpoint


def claim_campaign_items(
    checkpoint_path: Path,
    *,
    max_items: int,
    lease_owner: str,
    lease_ttl_seconds: int = LEASE_TTL_SECONDS,
    presenter: CampaignPresenter | None = None,
) -> dict[str, Any]:
    """Claim campaign items for external or builtin execution."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")

    claimed: list[dict[str, Any]] = []
    for item_id, item_state in checkpoint.items.items():
        if len(claimed) >= max_items:
            break
        if item_state.status in {ITEM_SUCCEEDED, ITEM_SKIPPED, ITEM_PROPOSED}:
            continue
        if item_state.status == ITEM_CLAIMED and not _lease_expired(item_state):
            continue
        if item_state.status == ITEM_CLAIMED and _lease_expired(item_state):
            item_state.status = ITEM_PENDING
            _release_item_lease(item_state)
        item_state.status = ITEM_CLAIMED
        item_state.claimed_at = _utcnow()
        item_state.lease_owner = lease_owner
        item_state.lease_expires_at = _utc_after(lease_ttl_seconds)
        item = CampaignItem(**item_state.item)
        _record_event(
            checkpoint,
            presenter,
            "item_claimed",
            f"Claimed by {lease_owner}",
            item=item,
            metadata={"lease_expires_at": item_state.lease_expires_at},
        )
        claimed.append(
            {
                "item_id": item_id,
                "label": item_state.item.get("label", item_id),
                "lease_owner": lease_owner,
                "lease_expires_at": item_state.lease_expires_at,
                "item": item_state.item,
            }
        )
    _write_checkpoint(checkpoint_path, checkpoint)
    return {
        "checkpoint_path": str(checkpoint_path),
        "claimed": claimed,
        "counts": _status_counts(checkpoint),
        "status_snapshot": render_campaign_snapshot(checkpoint, checkpoint_path),
    }


def _validate_submitted_proposal(checkpoint: CampaignCheckpoint, proposal: dict[str, Any]) -> None:
    if not isinstance(proposal, dict):
        raise PretorianClientError("proposal must be a JSON object.")
    domain = str(checkpoint.identity.get("domain", ""))
    if domain in {"policy", "scope"} and not isinstance(proposal.get("questions"), list):
        raise PretorianClientError("policy and scope campaign proposals must include a questions list.")


def submit_campaign_proposal(
    checkpoint_path: Path,
    *,
    item_id: str,
    proposal: dict[str, Any],
    presenter: CampaignPresenter | None = None,
) -> dict[str, Any]:
    """Persist a proposal generated by an external or builtin executor."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    item_state = checkpoint.items.get(item_id)
    if item_state is None:
        raise PretorianClientError(f"Campaign item not found: {item_id}")
    _validate_submitted_proposal(checkpoint, proposal)
    item_state.proposal = _safe_json(proposal)
    item_state.status = ITEM_PROPOSED
    item_state.last_error = None
    item_state.completed_at = _utcnow()
    _release_item_lease(item_state)
    item = CampaignItem(**item_state.item)
    _record_event(checkpoint, presenter, "item_proposed", "Stored proposal", item=item)
    _write_checkpoint(checkpoint_path, checkpoint)
    return {
        "checkpoint_path": str(checkpoint_path),
        "item_id": item_id,
        "status": item_state.status,
        "proposal_keys": sorted(item_state.proposal.keys()),
    }


async def _control_item_context(
    client: PretorianClient,
    checkpoint: CampaignCheckpoint,
    item_id: str,
) -> dict[str, Any]:
    system_id = str(checkpoint.workflow_snapshot.get("scope", {}).get("system_id", ""))
    framework_id = str(checkpoint.workflow_snapshot.get("scope", {}).get("framework_id", ""))
    context = await client.get_control_context(system_id, item_id, framework_id)
    implementation = await client.get_control_implementation(system_id, item_id, framework_id)
    notes = await client.list_control_notes(system_id, item_id, framework_id)
    evidence = await client.list_evidence(system_id, framework_id, control_id=item_id, limit=50)
    instructions = [
        "Use observable facts from the workspace and the supplied Pretorin context.",
        "Return ONLY JSON.",
        (
            'Shape: {"narrative_draft": "<markdown or null>", '
            '"evidence_gap_assessment": "<markdown or null>", '
            '"recommended_notes": ["<plain text note>"], '
            '"evidence_recommendations": [{"name": "...", "evidence_type": "...", "description": "<markdown>"}]}'
        ),
    ]
    if checkpoint.identity.get("mode") == "notes-fix":
        instructions.append("Address the open platform notes and improve the control narrative and evidence plan.")
    elif checkpoint.identity.get("mode") == "review-fix":
        instructions.append("Address the supplied family review findings and remediate only the cited gaps.")
    else:
        instructions.append("Draft an initial narrative and evidence plan for this control.")
    findings = (
        checkpoint.workflow_snapshot.get("extras", {}).get("review_findings", {}).get(item_id, [])
        if checkpoint.identity.get("mode") == "review-fix"
        else []
    )
    return {
        "instructions": "\n".join(instructions),
        "control_context": context.model_dump(mode="json"),
        "control_implementation": implementation.model_dump(mode="json"),
        "control_notes": _safe_json(notes),
        "evidence": [item.model_dump(mode="json") for item in evidence],
        "review_findings": _safe_json(findings),
    }


async def _policy_item_context(
    client: PretorianClient,
    checkpoint: CampaignCheckpoint,
    item_id: str,
) -> dict[str, Any]:
    questionnaire = await client.get_org_policy_questionnaire(item_id)
    target_ids = (
        sorted(_policy_question_targets(questionnaire)) if checkpoint.identity.get("mode") == "review-fix" else []
    )
    instructions = [
        "Use observable facts from the workspace and the persisted Pretorin questionnaire state.",
        "Return ONLY JSON.",
        (
            'Shape: {"questions": [{"question_id": "<id>", "proposed_answer": "<string or null>", '
            '"confidence": "high|medium|low", "evidence_summary": "<support>", '
            '"needs_manual_input": true, "manual_input_reason": "<why>"}], "summary": "<summary>"}'
        ),
    ]
    if checkpoint.identity.get("mode") == "review-fix":
        instructions.append("Focus on the questions implicated by the persisted policy review findings.")
    else:
        instructions.append("Draft improved answers for this policy questionnaire from workspace facts.")
    return {
        "instructions": "\n".join(instructions),
        "policy_id": item_id,
        "target_question_ids": target_ids,
        "questionnaire": questionnaire.model_dump(mode="json"),
    }


async def _scope_item_context(
    client: PretorianClient,
    checkpoint: CampaignCheckpoint,
    item_id: str,
) -> dict[str, Any]:
    system_id = str(checkpoint.workflow_snapshot.get("scope", {}).get("system_id", ""))
    framework_id = str(checkpoint.workflow_snapshot.get("scope", {}).get("framework_id", ""))
    scope = await client.get_scope(system_id, framework_id)
    target = next((question for question in scope.scope_questions if question.id == item_id), None)
    if target is None:
        raise PretorianClientError(f"Scope question not found: {item_id}")
    target_ids = (
        sorted(_scope_question_targets(scope)) if checkpoint.identity.get("mode") == "review-fix" else [item_id]
    )
    instructions = [
        "Use observable facts from the workspace and the persisted Pretorin scope questionnaire state.",
        "Return ONLY JSON.",
        (
            'Shape: {"questions": [{"question_id": "<id>", "proposed_answer": "<string or null>", '
            '"confidence": "high|medium|low", "evidence_summary": "<support>", '
            '"needs_manual_input": true, "manual_input_reason": "<why>"}], "summary": "<summary>"}'
        ),
        "Return at least one entry for the targeted question if you can support an answer.",
    ]
    if checkpoint.identity.get("mode") == "review-fix":
        instructions.append("Focus on the question IDs implicated by the persisted scope review findings.")
    return {
        "instructions": "\n".join(instructions),
        "system_id": system_id,
        "framework_id": framework_id,
        "target_question_ids": target_ids,
        "target_question": target.model_dump(mode="json"),
        "scope": scope.model_dump(mode="json"),
    }


async def get_campaign_item_context(
    client: PretorianClient,
    checkpoint_path: Path,
    *,
    item_id: str,
) -> dict[str, Any]:
    """Return full execution context for one campaign item."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    _validate_checkpoint_environment(client, WorkflowContextSnapshot(**checkpoint.workflow_snapshot))
    item_state = checkpoint.items.get(item_id)
    if item_state is None:
        raise PretorianClientError(f"Campaign item not found: {item_id}")

    if checkpoint.identity.get("domain") == "controls":
        context = await _control_item_context(client, checkpoint, item_id)
    elif checkpoint.identity.get("domain") == "policy":
        context = await _policy_item_context(client, checkpoint, item_id)
    else:
        context = await _scope_item_context(client, checkpoint, item_id)

    return {
        "checkpoint_path": str(checkpoint_path),
        "domain": checkpoint.identity.get("domain"),
        "mode": checkpoint.identity.get("mode"),
        "apply": checkpoint.identity.get("apply"),
        "workflow_snapshot": checkpoint.workflow_snapshot,
        "item": item_state.item,
        "item_state": item_state.to_dict(),
        "context": context,
    }


async def _apply_control_item(
    client: PretorianClient,
    request: CampaignRunRequest,
    item: CampaignItem,
    item_state: CampaignItemState,
    snapshot: WorkflowContextSnapshot,
) -> bool:
    system_id = str(snapshot.scope["system_id"])
    framework_id = str(snapshot.scope["framework_id"])
    proposal = item_state.proposal
    receipts = dict(item_state.receipts)
    changed_parts: list[str] = []
    changed = False

    if request.artifacts in {"narratives", "both"} and proposal.get("narrative_draft") and "narrative" not in receipts:
        await client.update_narrative(
            system_id=system_id,
            control_id=item.item_id,
            framework_id=framework_id,
            narrative=str(proposal["narrative_draft"]),
            is_ai_generated=True,
        )
        receipts["narrative"] = {"applied_at": _utcnow()}
        changed = True
        changed_parts.append("narrative")

    evidence_recommendations = proposal.get("evidence_recommendations") or []
    existing_indices = _existing_evidence_indices(item_state)
    batch_items = [
        EvidenceBatchItemCreate(
            name=str(rec["name"]),
            description=str(rec["description"]),
            control_id=item.item_id,
            evidence_type=str(rec.get("evidence_type", "policy_document")),
        )
        for index, rec in enumerate(evidence_recommendations)
        if isinstance(rec, dict) and request.artifacts in {"evidence", "both"} and index not in existing_indices
    ]
    if batch_items:
        batch_result = await client.create_evidence_batch(system_id, framework_id, batch_items)
        prior_results = receipts.get("evidence_batch", [])
        if not isinstance(prior_results, list):
            prior_results = []
        failed_indexes: list[int] = []
        pending_indexes = [idx for idx in range(len(evidence_recommendations)) if idx not in existing_indices]
        for offset, batch_item_result in enumerate(batch_result.results):
            index = pending_indexes[offset]
            result_payload = batch_item_result.model_dump(mode="json")
            result_payload["index"] = index
            if _successful_batch_result(result_payload):
                prior_results.append(result_payload)
                changed = True
            else:
                failed_indexes.append(index)
        receipts["evidence_batch"] = prior_results
        if failed_indexes:
            raise PretorianClientError(f"Evidence batch partially failed for {item.item_id}: indexes {failed_indexes}")
        changed_parts.append("evidence")

    if changed and "completion_note" not in receipts:
        note_result = await client.add_control_note(
            system_id=system_id,
            control_id=item.item_id,
            framework_id=framework_id,
            content=_control_completion_note(request.mode, changed_parts),
            source="cli",
        )
        receipts["completion_note"] = _safe_json_dict(note_result)
        changed_parts.append("note")

    item_state.receipts = _safe_json(receipts)
    return changed


async def _apply_policy_item(
    client: PretorianClient,
    request: CampaignRunRequest,
    item: CampaignItem,
    item_state: CampaignItemState,
) -> bool:
    questionnaire = await client.get_org_policy_questionnaire(item.item_id)
    target_ids: set[str] | None = None
    if request.mode == "review-fix":
        target_ids = _policy_question_targets(questionnaire)
    updates = _policy_updates(questionnaire, item_state.proposal, target_ids=target_ids)
    receipts = dict(item_state.receipts)
    if updates and "patch" not in receipts:
        await client.patch_org_policy_qa(item.item_id, updates)
        receipts["patch"] = {"updated_questions": [entry["question_id"] for entry in updates], "applied_at": _utcnow()}
        item_state.receipts = _safe_json(receipts)
        return True
    item_state.receipts = _safe_json(receipts)
    return bool(updates)


async def _apply_scope_item(
    client: PretorianClient,
    request: CampaignRunRequest,
    item: CampaignItem,
    item_state: CampaignItemState,
    snapshot: WorkflowContextSnapshot,
) -> bool:
    system_id = str(snapshot.scope["system_id"])
    framework_id = str(snapshot.scope["framework_id"])
    scope = await client.get_scope(system_id, framework_id)
    target_ids: set[str] | None = None
    if request.mode == "review-fix":
        target_ids = _scope_question_targets(scope)
    updates = _scope_updates(scope, item_state.proposal, target_ids=target_ids)
    targeted = [update for update in updates if update["question_id"] == item.item_id]
    receipts = dict(item_state.receipts)
    if targeted and "patch" not in receipts:
        await client.patch_scope_qa(system_id, framework_id, targeted)
        receipts["patch"] = {"updated_questions": [entry["question_id"] for entry in targeted], "applied_at": _utcnow()}
        item_state.receipts = _safe_json(receipts)
        return True
    item_state.receipts = _safe_json(receipts)
    return bool(targeted)


async def apply_campaign(
    client: PretorianClient,
    checkpoint_path: Path,
    *,
    item_ids: list[str] | None = None,
    presenter: CampaignPresenter | None = None,
) -> CampaignRunSummary:
    """Persist stored proposals back into platform-owned workflow records."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    request = _request_from_checkpoint(checkpoint_path, checkpoint)
    snapshot = WorkflowContextSnapshot(**checkpoint.workflow_snapshot)
    _validate_checkpoint_environment(client, snapshot)
    selected = set(item_ids or [])

    for item_id, item_state in checkpoint.items.items():
        if selected and item_id not in selected:
            continue
        if item_state.status == ITEM_SUCCEEDED:
            continue
        if not item_state.proposal:
            continue
        item = CampaignItem(**item_state.item)
        try:
            if request.domain == "controls":
                changed = await _apply_control_item(client, request, item, item_state, snapshot)
            elif request.domain == "policy":
                changed = await _apply_policy_item(client, request, item, item_state)
            else:
                changed = await _apply_scope_item(client, request, item, item_state, snapshot)
            item_state.status = ITEM_SUCCEEDED
            item_state.last_error = None
            item_state.completed_at = _utcnow()
            _release_item_lease(item_state)
            _record_event(
                checkpoint,
                presenter,
                "item_applied",
                "Applied changes" if changed else "No material changes to apply",
                item=item,
            )
        except Exception as exc:  # noqa: BLE001
            item_state.status = ITEM_FAILED
            item_state.last_error = str(exc)
            item_state.completed_at = _utcnow()
            _release_item_lease(item_state)
            _record_event(checkpoint, presenter, "item_failed", str(exc), item=item)
        _write_checkpoint(checkpoint_path, checkpoint)

    checkpoint.identity["apply"] = True
    _write_checkpoint(checkpoint_path, checkpoint)

    return build_campaign_summary(checkpoint, checkpoint_path, output_mode=request.output, apply_override=True)


def _mark_item_failed(
    checkpoint_path: Path,
    *,
    item_id: str,
    error: str,
    presenter: CampaignPresenter | None = None,
    attempt: int | None = None,
) -> None:
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    item_state = checkpoint.items.get(item_id)
    if item_state is None:
        raise PretorianClientError(f"Campaign item not found: {item_id}")
    item_state.status = ITEM_FAILED
    item_state.last_error = error
    item_state.completed_at = _utcnow()
    _release_item_lease(item_state)
    _record_event(checkpoint, presenter, "item_failed", error, item=CampaignItem(**item_state.item), attempt=attempt)
    _write_checkpoint(checkpoint_path, checkpoint)


ProposalProvider = Callable[
    [PretorianClient, CampaignRunRequest, CampaignItem, CampaignItemState, WorkflowContextSnapshot],
    Awaitable[dict[str, Any]],
]


async def _execute_claimed_item(
    client: PretorianClient,
    request: CampaignRunRequest,
    snapshot: WorkflowContextSnapshot,
    checkpoint_path: Path,
    item_id: str,
    proposal_provider: ProposalProvider,
    presenter: CampaignPresenter | None,
) -> None:
    for attempt in range(1, request.max_retries + 2):
        checkpoint = _load_checkpoint(checkpoint_path)
        if checkpoint is None:
            raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
        item_state = checkpoint.items[item_id]
        item = CampaignItem(**item_state.item)
        item_state.attempts = max(item_state.attempts, attempt)
        item_state.started_at = item_state.started_at or _utcnow()
        _record_event(checkpoint, presenter, "item_started", "Worker started", item=item, attempt=attempt)
        _write_checkpoint(checkpoint_path, checkpoint)
        try:
            proposal = await proposal_provider(client, request, item, item_state, snapshot)
            submit_campaign_proposal(checkpoint_path, item_id=item_id, proposal=proposal, presenter=presenter)
            if request.apply:
                await apply_campaign(client, checkpoint_path, item_ids=[item_id], presenter=presenter)
            return
        except Exception as exc:  # noqa: BLE001
            if attempt <= request.max_retries:
                retry_checkpoint = _load_checkpoint(checkpoint_path)
                if retry_checkpoint is None:
                    raise
                retry_item = CampaignItem(**retry_checkpoint.items[item_id].item)
                retry_checkpoint.items[item_id].last_error = str(exc)
                _record_event(
                    retry_checkpoint,
                    presenter,
                    "item_retrying",
                    str(exc),
                    item=retry_item,
                    attempt=attempt,
                )
                _write_checkpoint(checkpoint_path, retry_checkpoint)
                continue
            _mark_item_failed(checkpoint_path, item_id=item_id, error=str(exc), presenter=presenter, attempt=attempt)
            return


async def execute_campaign_with_provider(
    client: PretorianClient,
    checkpoint_path: Path,
    *,
    proposal_provider: ProposalProvider,
    presenter: CampaignPresenter | None = None,
    lease_owner: str,
) -> CampaignRunSummary:
    """Execute a prepared campaign using a supplied proposal provider."""
    checkpoint = _load_checkpoint(checkpoint_path)
    if checkpoint is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    request = _request_from_checkpoint(checkpoint_path, checkpoint)
    snapshot = WorkflowContextSnapshot(**checkpoint.workflow_snapshot)

    claim_result = claim_campaign_items(
        checkpoint_path,
        max_items=len(checkpoint.items),
        lease_owner=lease_owner,
        lease_ttl_seconds=LEASE_TTL_SECONDS,
        presenter=presenter,
    )
    claimed_ids = [entry["item_id"] for entry in claim_result["claimed"]]
    if not claimed_ids:
        loaded = _load_checkpoint(checkpoint_path) or checkpoint
        return build_campaign_summary(loaded, checkpoint_path, output_mode=request.output)

    semaphore = asyncio.Semaphore(max(1, request.concurrency))

    async def _bound(item_id: str) -> None:
        async with semaphore:
            await _execute_claimed_item(
                client,
                request,
                snapshot,
                checkpoint_path,
                item_id,
                proposal_provider,
                presenter,
            )

    await asyncio.gather(*[_bound(item_id) for item_id in claimed_ids])
    finished = _load_checkpoint(checkpoint_path)
    if finished is None:
        raise PretorianClientError(f"Campaign checkpoint not found: {checkpoint_path}")
    return build_campaign_summary(finished, checkpoint_path, output_mode=request.output)


async def run_campaign(client: PretorianClient, request: CampaignRunRequest) -> CampaignRunSummary:
    """Prepare a campaign, then optionally auto-execute with the builtin backend."""
    request.output = resolve_output_mode(request.output)
    presenter = _select_presenter(request.output)
    checkpoint = await prepare_campaign(client, request, presenter=presenter)

    if not _builtin_executor_available():
        _record_event(checkpoint, presenter, "run_waiting_external", "Prepared for external agent execution")
        _write_checkpoint(request.checkpoint_path, checkpoint)
        summary = build_campaign_summary(
            checkpoint,
            request.checkpoint_path,
            output_mode=request.output,
            prepared_only=True,
        )
        if presenter is not None:
            presenter.finish(summary)
            presenter.close()
        return summary

    _record_event(checkpoint, presenter, "run_builtin_executor", "Starting builtin executor")
    _write_checkpoint(request.checkpoint_path, checkpoint)
    from pretorin.workflows.campaign_builtin import execute_prepared_campaign

    summary = await execute_prepared_campaign(client, request.checkpoint_path, presenter=presenter)
    if presenter is not None:
        presenter.finish(summary)
        presenter.close()
    return summary
