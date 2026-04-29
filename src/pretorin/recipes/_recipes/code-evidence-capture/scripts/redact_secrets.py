"""Redact secrets from supplied text. Wraps pretorin.evidence.redact.redact()."""

from __future__ import annotations

from typing import Any

from pretorin.evidence.redact import redact


async def run(ctx: Any, *, text: str) -> dict[str, Any]:  # noqa: ARG001  # ctx unused for now
    """Run the named-pattern redactor over ``text``.

    Returns:
        dict with:
        - ``redacted_text``: the input with secret-shaped values replaced by
          ``[REDACTED:<kind>]`` placeholders.
        - ``secrets_count``: total number of redactions across all kinds.
        - ``details``: per-kind count dict (e.g.
          ``{"aws_access_key": 2, "password": 1}``) — empty when nothing
          redacted.
    """
    redacted, result = redact(text)
    return {
        "redacted_text": redacted,
        "secrets_count": result.total,
        "details": dict(result.counts) if result.counts else {},
    }
