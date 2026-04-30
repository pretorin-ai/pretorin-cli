"""Compose the auditor-facing markdown body. Wraps pretorin.evidence.markdown.compose()."""

from __future__ import annotations

from collections import Counter
from typing import Any

from pretorin.evidence.markdown import compose
from pretorin.evidence.redact import RedactionResult


async def run(  # noqa: PLR0913  # all params surface in the recipe manifest schema
    ctx: Any,  # noqa: ARG001  # ctx unused for now
    *,
    snippet: str,
    source_path: str,
    language: str = "",
    line_range: str | None = None,
    commit_hash: str | None = None,
    is_uncommitted: bool = False,
    user_prose: str = "",
    secrets_redacted: int = 0,
) -> dict[str, Any]:
    """Compose evidence body markdown.

    Reconstructs a minimal ``RedactionResult`` from ``secrets_redacted`` so the
    footer can include the "N secrets redacted" line. The agent passes the
    count through from the redact_secrets tool's ``secrets_count`` field; the
    per-kind detail isn't needed at footer-rendering time, just the total.
    """
    redaction: RedactionResult | None = None
    if secrets_redacted > 0:
        # Use a single bucketed count so RedactionResult.total returns the
        # right number for short_form(). The label "secret" is fine since we
        # don't know the per-kind breakdown at this point in the recipe.
        redaction = RedactionResult(counts=Counter({"secret": secrets_redacted}))

    body = compose(
        user_prose=user_prose,
        snippet=snippet,
        language=language,
        source_path=source_path,
        line_range=line_range,
        commit_hash=commit_hash,
        is_uncommitted=is_uncommitted,
        redaction=redaction,
    )
    return {"body": body}
