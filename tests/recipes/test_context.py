"""Tests for the recipe execution context state machine.

Covers WS2 Phase B of the recipe-implementation design:
- ExecutionContext lifecycle: start → activity → end → RecipeResult.
- Auto-expiry after 1 hour with no activity.
- Nesting forbidden: second start raises RecipeContextAlreadyActiveError.
- Cross-session isolation: contexts scoped to ContextStore.session_id.
- Tally helpers (record_evidence_write / record_narrative_write / record_error).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pretorin.recipes import context as ctx_module
from pretorin.recipes.context import ContextStore, RecipeResult, get_default_store, reset_default_store
from pretorin.recipes.errors import (
    RecipeContextAlreadyActiveError,
    RecipeContextExpiredError,
    RecipeContextSessionMismatchError,
)


@pytest.fixture(autouse=True)
def _reset_singleton() -> None:
    reset_default_store()
    yield
    reset_default_store()


@pytest.fixture
def store() -> ContextStore:
    """A fresh ContextStore with a deterministic session id for tests."""
    return ContextStore(session_id="test-session")


# =============================================================================
# start_recipe
# =============================================================================


def test_start_recipe_returns_context_with_ids(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    assert ctx.recipe_id == "x"
    assert ctx.recipe_version == "0.1.0"
    assert ctx.session_id == "test-session"
    assert ctx.context_id  # non-empty
    assert ctx.evidence_count == 0
    assert ctx.narrative_count == 0
    assert ctx.errors == []


def test_start_recipe_stores_params_and_selection(store: ContextStore) -> None:
    ctx = store.start_recipe(
        recipe_id="x",
        recipe_version="0.1.0",
        params={"target": "rhel-9"},
        selection={"selected_recipe": "x", "confidence": "high"},
    )
    assert ctx.params == {"target": "rhel-9"}
    assert ctx.selection == {"selected_recipe": "x", "confidence": "high"}


def test_start_recipe_copies_params_dict(store: ContextStore) -> None:
    """Mutating the caller's params dict after start should not affect the context."""
    caller_params = {"target": "rhel-9"}
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0", params=caller_params)
    caller_params["target"] = "modified"
    assert ctx.params == {"target": "rhel-9"}


# =============================================================================
# Nesting forbidden
# =============================================================================


def test_nesting_forbidden(store: ContextStore) -> None:
    """Second start before first end raises RecipeContextAlreadyActiveError."""
    store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    with pytest.raises(RecipeContextAlreadyActiveError):
        store.start_recipe(recipe_id="y", recipe_version="0.1.0")


def test_can_start_after_end(store: ContextStore) -> None:
    """End the first context, then start a second one."""
    ctx1 = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.end_recipe(ctx1.context_id)
    ctx2 = store.start_recipe(recipe_id="y", recipe_version="0.1.0")
    assert ctx2.recipe_id == "y"


# =============================================================================
# get / end / not-found / cross-session
# =============================================================================


def test_get_returns_context(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    fetched = store.get(ctx.context_id)
    assert fetched.context_id == ctx.context_id


def test_get_unknown_id_raises_expired(store: ContextStore) -> None:
    with pytest.raises(RecipeContextExpiredError):
        store.get("not-a-real-context-id")


def test_get_cross_session_raises(store: ContextStore) -> None:
    """A different session's context_id is rejected."""
    other_store = ContextStore(session_id="other-session")
    other_ctx = other_store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    # Try to fetch from `store` using other_store's context_id.
    # Manually plant the context to simulate the cross-session attack.
    store._contexts[other_ctx.context_id] = other_ctx
    with pytest.raises(RecipeContextSessionMismatchError):
        store.get(other_ctx.context_id)


def test_end_returns_recipe_result(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0", selection={"k": "v"})
    result = store.end_recipe(ctx.context_id)
    assert isinstance(result, RecipeResult)
    assert result.status == "pass"
    assert result.recipe_id == "x"
    assert result.evidence_count == 0
    assert result.selection == {"k": "v"}
    assert result.elapsed_seconds >= 0


def test_end_removes_context(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.end_recipe(ctx.context_id)
    with pytest.raises(RecipeContextExpiredError):
        store.get(ctx.context_id)


def test_end_unknown_id_raises(store: ContextStore) -> None:
    with pytest.raises(RecipeContextExpiredError):
        store.end_recipe("not-a-real-id")


@pytest.mark.parametrize("status", ["pass", "fail", "needs_input"])
def test_end_with_status(store: ContextStore, status: str) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    result = store.end_recipe(ctx.context_id, status=status)
    assert result.status == status


# =============================================================================
# Auto-expiry
# =============================================================================


def test_expired_context_raises_on_get(store: ContextStore, monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock the clock so the 1-hour expiry triggers immediately."""
    fake_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(ctx_module, "_now", lambda: fake_now)
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    # Advance the clock past the 1-hour expiry window.
    monkeypatch.setattr(ctx_module, "_now", lambda: fake_now + timedelta(hours=1, seconds=1))
    with pytest.raises(RecipeContextExpiredError):
        store.get(ctx.context_id)


def test_activity_extends_expiry_window(store: ContextStore, monkeypatch: pytest.MonkeyPatch) -> None:
    """get() updates last_activity_at, pushing the expiry forward."""
    times = [datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)]
    monkeypatch.setattr(ctx_module, "_now", lambda: times[0])
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")

    # Move forward 30 minutes — still alive, get() touches activity.
    times[0] = datetime(2026, 1, 1, 12, 30, 0, tzinfo=timezone.utc)
    fetched = store.get(ctx.context_id)
    assert fetched is not None

    # Move forward another 45 minutes (75 total from start, but only 45 from
    # last activity) — still alive because the get() above bumped activity.
    times[0] = datetime(2026, 1, 1, 13, 15, 0, tzinfo=timezone.utc)
    fetched = store.get(ctx.context_id)
    assert fetched is not None


def test_stale_contexts_swept_on_start(store: ContextStore, monkeypatch: pytest.MonkeyPatch) -> None:
    """A stale context shouldn't block starting a new recipe (sweep clears it)."""
    fake_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(ctx_module, "_now", lambda: fake_now)
    store.start_recipe(recipe_id="x", recipe_version="0.1.0")

    # Move past expiry. The stale context should be swept on next start.
    monkeypatch.setattr(ctx_module, "_now", lambda: fake_now + timedelta(hours=2))
    ctx2 = store.start_recipe(recipe_id="y", recipe_version="0.1.0")
    assert ctx2.recipe_id == "y"


# =============================================================================
# Tally helpers
# =============================================================================


def test_record_evidence_write_increments(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.record_evidence_write(ctx.context_id)
    store.record_evidence_write(ctx.context_id)
    fetched = store.get(ctx.context_id)
    assert fetched.evidence_count == 2


def test_record_narrative_write_increments(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.record_narrative_write(ctx.context_id)
    fetched = store.get(ctx.context_id)
    assert fetched.narrative_count == 1


def test_record_error_appends(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.record_error(ctx.context_id, "first")
    store.record_error(ctx.context_id, "second")
    fetched = store.get(ctx.context_id)
    assert fetched.errors == ["first", "second"]


def test_tally_helpers_no_op_on_unknown_id(store: ContextStore) -> None:
    """No-op rather than raise — write-tool stamping shouldn't blow up on stale ids."""
    store.record_evidence_write("does-not-exist")
    store.record_narrative_write("does-not-exist")
    store.record_error("does-not-exist", "msg")


def test_recipe_result_includes_tallies(store: ContextStore) -> None:
    ctx = store.start_recipe(recipe_id="x", recipe_version="0.1.0")
    store.record_evidence_write(ctx.context_id)
    store.record_evidence_write(ctx.context_id)
    store.record_narrative_write(ctx.context_id)
    store.record_error(ctx.context_id, "warning")
    result = store.end_recipe(ctx.context_id)
    assert result.evidence_count == 2
    assert result.narrative_count == 1
    assert result.errors == ["warning"]


# =============================================================================
# Default singleton
# =============================================================================


def test_default_store_singleton_reuses_instance() -> None:
    s1 = get_default_store()
    s2 = get_default_store()
    assert s1 is s2


def test_reset_default_store_creates_new_singleton() -> None:
    s1 = get_default_store()
    reset_default_store()
    s2 = get_default_store()
    assert s1 is not s2
