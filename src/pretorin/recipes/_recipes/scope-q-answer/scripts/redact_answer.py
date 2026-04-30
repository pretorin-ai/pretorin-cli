"""redact_answer script for the scope-q-answer recipe."""

from __future__ import annotations

from typing import Any

from pretorin.evidence.redact import redact_secrets


async def run(ctx: Any, *, answer_text: str) -> dict[str, Any]:
    """Run answer text through the standard secret-redaction pipeline."""
    result = redact_secrets(answer_text)
    return {
        "redacted": result.redacted,
        "redaction_summary": result.to_audit_summary().model_dump(),
    }
