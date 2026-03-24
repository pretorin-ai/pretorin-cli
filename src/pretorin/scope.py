"""Run-local execution scope for parallel-safe agent execution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionScope:
    """Immutable, pre-validated execution scope.

    Resolved once at the runner boundary and threaded through subtasks
    so that parallel agent runs never race on shared config state.
    """

    system_id: str
    framework_id: str
