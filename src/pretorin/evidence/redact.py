"""Redact super-sensitive secrets from text captured for evidence.

Ported from PR #92 (issue #88, post-rework 2026-04-27) as part of the
recipe-implementation WS3 work. The redactor scope is intentionally tight:
API keys and password-shaped values, nothing else. Vendor plugins from
upstream tools (detect-secrets) and the entropy heuristic were both noisy on
real-world code/config — they flagged ordinary identifiers like
``resources``, ``cpu``, ``minReplicas`` as secrets and made the captured
snippets unreadable. The current pack is a hand-curated list of named
high-confidence patterns.

Each match is replaced with a stable placeholder ``[REDACTED:<kind>]``.
:class:`RedactionResult` carries per-kind counts; ``to_audit_summary()``
converts to the platform-facing ``RedactionSummary`` audit-metadata model
(see ``pretorin.client.models.RedactionSummary``). The two models are
deliberately separate: this one tracks redaction internals, the other is
the wire-format the platform stores.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Final

from pretorin.client.models import RedactionSummary

logger = logging.getLogger(__name__)

_BACKEND_LOGGED = False


def _log_backend_once(backend: str) -> None:
    global _BACKEND_LOGGED
    if not _BACKEND_LOGGED:
        logger.info("Evidence redactor backend: %s", backend)
        _BACKEND_LOGGED = True


# --- Internal regex pack -----------------------------------------------------

_AWS_SECRET_RE = re.compile(r"(?i)aws(?:.{0,20})?(?:secret|key)(?:.{0,20})?[=:]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?")
_PEM_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----"
    r"[\s\S]+?"
    r"-----END (?:RSA |EC |DSA |OPENSSH |ENCRYPTED |PGP )?PRIVATE KEY-----"
)
# Credential-bearing URLs: ``proto://user:pass@host`` (postgres, redis,
# mongodb, http(s), amqp, ldap, ssh, etc.). Empty username is allowed
# (``redis://:pass@host``); password must be at least one char. The userinfo
# segment cannot contain ``/`` or whitespace, which prevents false positives
# on paths/queries that happen to contain ``@``.
_CRED_URL_RE = re.compile(r"\b[a-zA-Z][a-zA-Z0-9+.-]*://[^/\s:@]*:[^/\s@]+@")
# password / secret / api_key style assignments. Triggers on any of those
# keyword names followed by `:` or `=` and a quoted value of length 4+.
# Captures the QUOTED VALUE only so the keyword stays readable in the
# redacted output (``password = "[REDACTED:password]"`` is more useful than
# ``[REDACTED:password]``).
_PASSWORD_ASSIGNMENT_RE = re.compile(
    r"""(?ix)                                  # ignore case + verbose
    \b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)\b
    \s*[:=]\s*
    ['"]([^'"\s]{4,})['"]
    """
)

_SECRET_PATTERNS: Final[list[tuple[str, re.Pattern[str]]]] = [
    ("aws_access_key", re.compile(r"\b((?:AKIA|ASIA)[0-9A-Z]{16})\b")),
    ("aws_secret_key", _AWS_SECRET_RE),
    ("github_token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{36,255})\b")),
    ("slack_token", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("stripe_key", re.compile(r"\b(sk_(?:live|test)_[A-Za-z0-9]{24,})\b")),
    ("google_api_key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")),
    ("jwt", re.compile(r"\b(eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,})\b")),
    ("pem_private_key", _PEM_RE),
    ("cred_url", _CRED_URL_RE),
]


@dataclass
class RedactionResult:
    """Per-kind redaction counts captured during a single redact() call.

    Distinct from ``pretorin.client.models.RedactionSummary``: this dataclass
    tracks redaction internals (one entry per matched pattern kind), while
    ``RedactionSummary`` is the platform-facing audit-metadata wire format.
    Convert with ``to_audit_summary()`` when stamping evidence.
    """

    counts: Counter[str] = field(default_factory=Counter)

    def any(self) -> bool:
        return sum(self.counts.values()) > 0

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    def short_form(self) -> str:
        """Footer-friendly summary string. Empty when nothing redacted."""
        if not self.any():
            return ""
        n = self.total
        return f"{n} secret{'s' if n != 1 else ''} redacted"

    def to_audit_summary(self) -> RedactionSummary:
        """Convert to the platform-facing audit-metadata RedactionSummary model.

        Maps every redaction kind onto the schema'd ``secrets`` count (this
        redactor is scoped to secret-shaped patterns only — no PII tracking).
        Per-kind detail goes into the ``details`` dict so callers that want
        granularity can preserve it without changing the top-level shape.
        """
        return RedactionSummary(
            secrets=self.total,
            pii=0,
            custom=0,
            details=dict(self.counts) if self.counts else None,
        )


def _redact_internal(text: str) -> tuple[str, RedactionResult]:
    result = RedactionResult()

    def _make_replacer(kind: str) -> Callable[[re.Match[str]], str]:
        def _replace(_match: re.Match[str]) -> str:
            result.counts[kind] += 1
            return f"[REDACTED:{kind}]"

        return _replace

    for kind, pat in _SECRET_PATTERNS:
        text = pat.sub(_make_replacer(kind), text)

    # password / secret / api_key keyword detector — captures only the quoted
    # value so the keyword stays readable for the auditor.
    def _password_replace(match: re.Match[str]) -> str:
        result.counts["password"] += 1
        prefix = match.group(0)[: match.start(1) - match.start()]
        suffix = match.group(0)[match.end(1) - match.start() :]
        return f"{prefix}[REDACTED:password]{suffix}"

    text = _PASSWORD_ASSIGNMENT_RE.sub(_password_replace, text)
    return text, result


# --- Public API --------------------------------------------------------------


def redact(text: str, *, redact_secrets: bool = True) -> tuple[str, RedactionResult]:
    """Redact API keys and password-shaped values from ``text``.

    Args:
        text: Source text to scan.
        redact_secrets: When False, return the input unchanged with an empty
            summary. The CLI exposes this via ``--no-redact`` and requires
            interactive confirmation before disabling.
    """
    if not redact_secrets:
        _log_backend_once("disabled")
        return text, RedactionResult()

    _log_backend_once("internal_named_pack")
    return _redact_internal(text)


__all__ = ["RedactionResult", "redact"]
