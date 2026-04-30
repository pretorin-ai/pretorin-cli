"""Minimal valid unified.json template for `pretorin frameworks init-custom`."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def minimal_unified(framework_id: str, title: str | None = None) -> dict[str, Any]:
    """Build the smallest unified.json that passes the schema and the platform.

    Includes one sample family with one sample control so the user has a
    concrete shape to extend rather than starting from blank.
    """
    return {
        "framework_id": framework_id,
        "version": "1.0",
        "source_format": "custom",
        "generated": _utcnow_iso(),
        "metadata": {
            "title": title or framework_id,
            "description": "TODO: describe this framework.",
            "publisher": "TODO: publishing organization",
            "version": "0.1.0",
            "last_modified": _utcnow_iso(),
        },
        "families": [
            {
                "id": "ac",
                "title": "Access Control",
                "description": "TODO: describe this family.",
                "controls": [
                    {
                        "id": "ac-01",
                        "title": "Sample Control",
                        "status": "active",
                        "family": "Access Control",
                        "family_id": "ac",
                        "statement": "TODO: write the control statement.",
                        "guidance": "",
                        "parameters": [],
                        "enhancements": [],
                        "references": [],
                        "related_controls": [],
                    }
                ],
            }
        ],
    }


__all__ = ["minimal_unified"]
