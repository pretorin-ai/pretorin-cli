"""Helper to build the ``code_context`` dict for evidence API calls.

Issue #88. Three sites construct the same dict (``cli/evidence.py``,
``evidence/sync.py``, and the new capture flow). Centralizing the shape
keeps payloads consistent and removes a class of "forgot to add the new
field" bugs.
"""

from __future__ import annotations

from typing import Any


def build_code_context(
    *,
    code_file_path: str | None = None,
    code_line_numbers: str | None = None,
    code_snippet: str | None = None,
    code_repository: str | None = None,
    code_commit_hash: str | None = None,
) -> dict[str, Any]:
    """Return a ``code_context`` dict containing only the populated fields.

    The platform's idempotency key includes these fields, so passing
    ``None`` and an empty string have different semantics — only emit a
    key when we have a real value.
    """
    ctx: dict[str, Any] = {}
    if code_file_path:
        ctx["code_file_path"] = code_file_path
    if code_line_numbers:
        ctx["code_line_numbers"] = code_line_numbers
    if code_snippet:
        ctx["code_snippet"] = code_snippet
    if code_repository:
        ctx["code_repository"] = code_repository
    if code_commit_hash:
        ctx["code_commit_hash"] = code_commit_hash
    return ctx
