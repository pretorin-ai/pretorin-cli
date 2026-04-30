"""Recipe execution context — the audit-metadata stamping mechanism.

Per the design's WS2 §5 ("Audit-metadata stamping mechanism via idempotent
recipe execution context"):

- ``pretorin_start_recipe(recipe_id, recipe_version, params)`` returns a
  ``context_id``. Server-side state keyed by ``context_id`` includes recipe
  id/version, params, MCP session id (for scope), creation timestamp, and
  the running ``RecipeSelection`` record.
- The calling agent passes ``recipe_context_id=<context_id>`` explicitly on
  subsequent platform-API write calls. Stamping is via explicit param, not
  implicit session state — drop-prevents wrong-stamping after session
  resumption or context churn.
- **Auto-expiry** after 1 hour with no activity. Stale ``context_id`` raises
  a clear error rather than silently using stale recipe metadata.
- **Nesting forbidden**: a second ``pretorin_start_recipe`` call before the
  first is closed raises ``RecipeContextAlreadyActiveError``. One recipe per
  logical task in v1; nesting is a v2 question.
- **Cross-session isolation**: contexts are scoped to MCP session id. New
  session, new state. Prevents the orphan-context-from-prior-session class
  of bugs.

For pretorin's stdio MCP transport, "session" is effectively the process
boundary — each MCP client connection spawns its own ``pretorin mcp-serve``
subprocess with its own ContextStore. The session_id field is informational
(set to the process's startup token) and provides the cross-session check
even though stdio transport already gives us process isolation; this lets
the same code path work for future HTTP/SSE transport without a rewrite.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import RLock
from typing import Any

from pretorin.recipes.errors import (
    RecipeContextAlreadyActiveError,
    RecipeContextExpiredError,
    RecipeContextSessionMismatchError,
)

logger = logging.getLogger(__name__)


# 1-hour auto-expiry per design. Activity (write tool calls referencing the
# context_id) extends the window; idle contexts expire and raise on next access.
_EXPIRY = timedelta(hours=1)


def _now() -> datetime:
    """Wrapped for tests to monkeypatch a fixed clock."""
    return datetime.now(timezone.utc)


@dataclass
class ExecutionContext:
    """One active recipe invocation's server-side state.

    Constructed by ``ContextStore.start_recipe``; mutated only via
    ``ContextStore.touch`` / ``record_evidence_write`` etc. so the lock
    guarantees consistency.
    """

    context_id: str
    recipe_id: str
    recipe_version: str
    params: dict[str, Any]
    session_id: str
    started_at: datetime
    last_activity_at: datetime
    selection: dict[str, Any] | None = None
    """The structured ``RecipeSelection`` record from the engagement layer (WS0).

    Populated by ``pretorin_start_recipe``'s caller when the recipe was picked
    via a workflow agent decision. None for direct ``pretorin recipe run``
    invocations from the CLI.
    """

    evidence_count: int = 0
    """Tally of platform write calls stamped with this context's recipe metadata."""

    narrative_count: int = 0

    errors: list[str] = field(default_factory=list)
    """Accumulator for non-fatal errors recorded during the recipe's execution."""

    def is_expired(self, *, now: datetime | None = None) -> bool:
        """True when (now - last_activity_at) >= 1 hour."""
        return (now or _now()) - self.last_activity_at >= _EXPIRY


@dataclass
class RecipeResult:
    """Returned by ``ContextStore.end_recipe``; the recipe invocation's summary.

    Per RFC 0001 §"Execution model" step 8 ("RecipeResult").
    """

    status: str  # "pass" | "fail" | "needs_input"
    recipe_id: str
    recipe_version: str
    evidence_count: int
    narrative_count: int
    errors: list[str]
    selection: dict[str, Any] | None
    elapsed_seconds: float


def _generate_context_id() -> str:
    """Opaque random identifier for one recipe invocation."""
    return uuid.uuid4().hex


def _generate_session_id() -> str:
    """Process-startup session id used for cross-session isolation.

    For stdio MCP transport this is per-process; cross-session isolation comes
    from process boundary plus this token. Future HTTP/SSE transports replace
    this with a per-connection token without touching the rest of the code.
    """
    return f"pid-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class ContextStore:
    """Thread-safe in-process store of active recipe execution contexts.

    Module-level singleton via ``get_default_store()``. Stdio MCP servers run
    as one process per client connection so a process-level singleton matches
    the "one session" reality of pretorin's transport.
    """

    def __init__(self, *, session_id: str | None = None) -> None:
        self._lock = RLock()
        self._contexts: dict[str, ExecutionContext] = {}
        # session_id is fixed at store construction; for tests, override.
        self._session_id = session_id or _generate_session_id()

    @property
    def session_id(self) -> str:
        return self._session_id

    def start_recipe(
        self,
        *,
        recipe_id: str,
        recipe_version: str,
        params: dict[str, Any] | None = None,
        selection: dict[str, Any] | None = None,
    ) -> ExecutionContext:
        """Open a new recipe execution context.

        Raises ``RecipeContextAlreadyActiveError`` if any context belonging to
        this session is currently active (nesting forbidden in v1). Stale
        contexts are garbage-collected before the active-check.
        """
        with self._lock:
            self._sweep_stale_locked()
            for ctx in self._contexts.values():
                if ctx.session_id == self._session_id and not ctx.is_expired():
                    raise RecipeContextAlreadyActiveError(
                        f"Recipe context {ctx.context_id} for {ctx.recipe_id!r} is "
                        "still active. Call pretorin_end_recipe first; nesting is "
                        "forbidden in v1."
                    )
            now = _now()
            ctx = ExecutionContext(
                context_id=_generate_context_id(),
                recipe_id=recipe_id,
                recipe_version=recipe_version,
                params=dict(params or {}),
                session_id=self._session_id,
                started_at=now,
                last_activity_at=now,
                selection=dict(selection) if selection else None,
            )
            self._contexts[ctx.context_id] = ctx
            return ctx

    def get(self, context_id: str) -> ExecutionContext:
        """Look up an active context by id.

        Validates session id match and not-expired. Raises
        ``RecipeContextSessionMismatchError`` or ``RecipeContextExpiredError``
        on those conditions; returns the touched context (last_activity_at
        bumped) on success.
        """
        with self._lock:
            ctx = self._contexts.get(context_id)
            if ctx is None:
                # Unknown id — treat as expired/nonexistent. From the caller's
                # perspective there's no useful distinction.
                raise RecipeContextExpiredError(
                    f"Recipe context {context_id!r} is unknown or expired. "
                    "Call pretorin_start_recipe to obtain a fresh context."
                )
            if ctx.session_id != self._session_id:
                raise RecipeContextSessionMismatchError(
                    f"Recipe context {context_id!r} was created in a different "
                    f"session ({ctx.session_id}). Cross-session use is forbidden."
                )
            if ctx.is_expired():
                # Expired — drop from store and raise.
                del self._contexts[context_id]
                raise RecipeContextExpiredError(
                    f"Recipe context {context_id!r} expired (no activity for ≥ 1 hour). "
                    "Call pretorin_start_recipe to obtain a fresh context."
                )
            ctx.last_activity_at = _now()
            return ctx

    def end_recipe(
        self,
        context_id: str,
        *,
        status: str = "pass",
    ) -> RecipeResult:
        """Close a recipe execution context and return its summary.

        Always removes the context from the store. Raises the same errors as
        ``get`` if the context_id doesn't belong to this session or is
        expired. ``status`` is the caller-supplied disposition.
        """
        with self._lock:
            # ``get`` validates session + expiry; we then delete regardless.
            ctx = self.get(context_id)
            elapsed = (_now() - ctx.started_at).total_seconds()
            del self._contexts[context_id]
            return RecipeResult(
                status=status,
                recipe_id=ctx.recipe_id,
                recipe_version=ctx.recipe_version,
                evidence_count=ctx.evidence_count,
                narrative_count=ctx.narrative_count,
                errors=list(ctx.errors),
                selection=dict(ctx.selection) if ctx.selection else None,
                elapsed_seconds=elapsed,
            )

    def record_evidence_write(self, context_id: str) -> None:
        """Bump the evidence_count tally on a context. Called from the write-tool stamping path."""
        with self._lock:
            ctx = self._contexts.get(context_id)
            if ctx is not None:
                ctx.evidence_count += 1

    def record_narrative_write(self, context_id: str) -> None:
        """Bump the narrative_count tally."""
        with self._lock:
            ctx = self._contexts.get(context_id)
            if ctx is not None:
                ctx.narrative_count += 1

    def record_error(self, context_id: str, message: str) -> None:
        """Append a non-fatal error to the context's accumulator."""
        with self._lock:
            ctx = self._contexts.get(context_id)
            if ctx is not None:
                ctx.errors.append(message)

    def _sweep_stale_locked(self) -> None:
        """Remove expired contexts; called with self._lock held."""
        now = _now()
        stale = [cid for cid, ctx in self._contexts.items() if ctx.is_expired(now=now)]
        for cid in stale:
            logger.debug("Sweeping expired recipe context %s", cid)
            del self._contexts[cid]


# Module-level singleton. Stdio MCP server runs one process per session so a
# single store per process matches the deployment shape. Tests construct fresh
# ContextStore instances when isolation is needed.
_DEFAULT_STORE: ContextStore | None = None


def get_default_store() -> ContextStore:
    """Return the process-singleton ContextStore, creating it on first access."""
    global _DEFAULT_STORE
    if _DEFAULT_STORE is None:
        _DEFAULT_STORE = ContextStore()
    return _DEFAULT_STORE


def reset_default_store() -> None:
    """Drop the singleton (used by tests to clean state)."""
    global _DEFAULT_STORE
    _DEFAULT_STORE = None


__all__ = [
    "ContextStore",
    "ExecutionContext",
    "RecipeResult",
    "get_default_store",
    "reset_default_store",
]
