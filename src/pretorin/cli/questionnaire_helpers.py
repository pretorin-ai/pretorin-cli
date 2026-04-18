"""Shared helpers for questionnaire-based CLI commands (scope, policy)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import typer

from pretorin.client.config import Config


def platform_base_url() -> str:
    """Derive the platform UI base URL from the configured API base URL."""
    base_url = Config().platform_api_base_url.rstrip("/")
    for suffix in ("/api/v1/public", "/api/v1"):
        if base_url.endswith(suffix):
            return base_url[: -len(suffix)]
    return base_url


def validate_working_directory(path: str) -> Path:
    """Resolve *path* and raise :class:`typer.BadParameter` if it doesn't exist."""
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise typer.BadParameter(f"path does not exist: {resolved}")
    return resolved


def answer_map(payload: dict[str, Any] | None) -> dict[str, str | None]:
    """Extract ``{question_id: answer}`` from a questionnaire payload."""
    questions = (payload or {}).get("questions", [])
    return {str(item.get("id")): item.get("answer") for item in questions if isinstance(item, dict) and item.get("id")}


def normalize_text(value: str | None) -> str:
    """Strip leading/trailing whitespace, collapsing *None* to ``""``."""
    return (value or "").strip()
