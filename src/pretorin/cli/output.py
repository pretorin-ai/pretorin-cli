"""JSON output mode helpers for Pretorin CLI."""

from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import BaseModel

_json_mode: bool = False


def set_json_mode(enabled: bool) -> None:
    """Enable or disable JSON output mode."""
    global _json_mode
    _json_mode = enabled


def is_json_mode() -> bool:
    """Check if JSON output mode is enabled."""
    return _json_mode


def print_json(data: Any) -> None:
    """Print data as formatted JSON to stdout.

    Handles Pydantic models, lists of models, and plain dicts/lists.
    """
    serialized: Any
    if isinstance(data, BaseModel):
        serialized = data.model_dump(mode="json")
    elif isinstance(data, list):
        serialized = [item.model_dump(mode="json") if isinstance(item, BaseModel) else item for item in data]
    elif isinstance(data, dict):
        serialized = {k: v.model_dump(mode="json") if isinstance(v, BaseModel) else v for k, v in data.items()}
    else:
        serialized = data

    json.dump(serialized, sys.stdout, indent=2, default=str)
    sys.stdout.write("\n")
