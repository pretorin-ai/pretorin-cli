"""Resolve env-var references in captured code snippets to runtime values.

When a snippet captured for evidence references an environment variable
(``os.getenv("DELETION_GRACE_PERIOD")``, ``process.env.LOG_LEVEL``,
``${PORT:-8080}``), the auditor reading the description benefits from
seeing what that variable actually evaluates to at capture time, not
just the symbolic reference. This module detects those references and
resolves them against the calling process's ``os.environ``.

Two-tier safety:

- **Tier 1 (name denylist):** if the variable name looks secret-shaped
  (case-insensitive substring match against ``KEY``, ``SECRET``,
  ``TOKEN``, ``PASSWORD``, ``CREDENTIAL``, ``PRIVATE``, ``AUTH``,
  ``SESSION``, ``COOKIE``, ``SALT``, ``SIGNATURE``, ``CERT``,
  ``BEARER``), the value is hidden.
- **Tier 2 (value redact):** even if the name passes tier 1, the
  resolved value is run through :mod:`pretorin.evidence.redact`. Any
  match — AWS / GitHub / Stripe / JWT / PEM / password assignment /
  ``proto://user:pass@host`` URL — hides the value. Both gates must
  pass for the value to appear.

Tier 2 runs *independently* of the snippet-redaction ``--no-redact``
flag, so an operator confirming "this snippet is clean" can't
accidentally leak credential URLs out of env values.

Out of scope:

- Loading ``.env`` files (resolution is against the live process env only).
- Languages beyond Python / JS-TS / shell.
- The campaign-apply path: the agent runtime's env is not the user's
  local env, so :func:`pretorin.workflows.evidence_validation.enrich_evidence_recommendations`
  is intentionally left untouched.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import textwrap
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Final

from pretorin.evidence.redact import redact

logger = logging.getLogger(__name__)


# --- Detection ---------------------------------------------------------------

# Python: os.getenv("X"[, "default"]), os.environ.get("X"[, "default"])
_PY_GETENV_RE = re.compile(
    r"""(?x)
    \bos\.(?:getenv|environ\.get)\(
        \s*['"](?P<name>[A-Za-z_][A-Za-z0-9_]*)['"]
        (?:\s*,\s*['"](?P<default>[^'"]*)['"])?
        \s*\)
    """
)
# Python: os.environ["X"]
_PY_ENVIRON_SUBSCRIPT_RE = re.compile(
    r"""(?x)
    \bos\.environ\[
        \s*['"](?P<name>[A-Za-z_][A-Za-z0-9_]*)['"]\s*
    \]
    """
)
# JS/TS: process.env.X
_JS_DOTTED_RE = re.compile(r"\bprocess\.env\.(?P<name>[A-Za-z_][A-Za-z0-9_]*)")
# JS/TS: process.env["X"]
_JS_BRACKET_RE = re.compile(
    r"""(?x)
    \bprocess\.env\[
        \s*['"](?P<name>[A-Za-z_][A-Za-z0-9_]*)['"]\s*
    \]
    """
)
# Shell: ${X}, ${X:-default}, ${X-default}
_SHELL_BRACE_RE = re.compile(
    r"""(?x)
    \$\{
        (?P<name>[A-Za-z_][A-Za-z0-9_]*)
        (?::?-(?P<default>[^}]*))?
    \}
    """
)
# Shell: $X — bare form, no default. Restricted to uppercase-first names
# (the env-var convention) so JSON-schema-style YAML keys like ``$ref`` /
# ``$schema`` don't false-match. Positionals ($0, $1) and specials
# ($?, $@, $$) are excluded by the [A-Z_] requirement.
_SHELL_BARE_RE = re.compile(r"\$(?P<name>[A-Z_][A-Z0-9_]*)\b")
# Kubernetes manifest env interpolation: $(VAR_NAME). Used in container
# ``command``/``args``/``env``. Same uppercase-first rule keeps shell
# command substitution like ``$(date)`` / ``$(pwd)`` out.
_SHELL_PAREN_RE = re.compile(r"\$\((?P<name>[A-Z_][A-Z0-9_]*)\)")

_PYTHON_LANGS: Final[frozenset[str]] = frozenset({"python"})
_JS_LANGS: Final[frozenset[str]] = frozenset({"javascript", "jsx", "typescript", "tsx"})
# YAML is in the shell family because CI workflows / k8s manifests /
# docker-compose files commonly embed shell-style ``$VAR`` interpolation
# inside ``run:`` / ``command:`` blocks. Dockerfile uses the same
# ``${VAR}`` / ``$VAR`` interpolation in ARG / ENV / RUN lines.
_SHELL_LANGS: Final[frozenset[str]] = frozenset({"bash", "fish", "shell", "yaml", "dockerfile"})


# --- Inline definition detection --------------------------------------------
#
# A reference like ``$SHANNON_BUDGET_USD`` inside a captured YAML often has
# its value defined elsewhere in the same snippet (``env:`` block, k8s
# ``- name: X / value: Y`` pair, Dockerfile ``ARG``/``ENV``, shell
# ``export X=Y`` or bare ``X=Y``). Detecting those inline assignments lets
# us resolve the snippet's actual evaluation rather than depending on the
# agent's local ``os.environ``, which is unrelated to what the snippet
# does in production.
#
# Uppercase-first names only — same rationale as the shell bare-form ref
# detector. Lowercase YAML keys like ``name:`` / ``kind:`` are skipped.

# Dockerfile: ``ARG X=Y`` / ``ARG X`` / ``ENV X=Y`` / ``ENV X Y``
_DEF_DOCKERFILE_RE = re.compile(
    r"""(?xm)
    ^[ \t]*(?:ARG|ENV)[ \t]+
    (?P<name>[A-Z_][A-Z0-9_]*)
    (?:[ \t]*=[ \t]*|[ \t]+)
    (?P<value>"[^"\n]*"|'[^'\n]*'|\S+)
    """
)
# Shell: ``export X=Y`` or bare ``X=Y`` at start of line.
_DEF_SHELL_RE = re.compile(
    r"""(?xm)
    ^[ \t]*(?:export[ \t]+)?
    (?P<name>[A-Z_][A-Z0-9_]*)
    =
    (?P<value>"[^"\n]*"|'[^'\n]*'|\S+)
    """
)
# YAML mapping entry: ``KEY: value`` / ``KEY: "value"``. The value group
# stops at end-of-line and strips trailing comments — but a comment is
# only recognized when preceded by whitespace, so URL fragments
# (``https://api.example.com/v1#section``) survive intact (B2).
# Block scalars (``KEY: |``) are intentionally not handled — multi-line
# values aren't auditor-friendly inside a one-liner resolved block anyway.
_DEF_YAML_RE = re.compile(
    r"""(?xm)
    ^[ \t]*
    (?P<name>[A-Z_][A-Z0-9_]*)
    [ \t]*:[ \t]*
    (?P<value>"[^"\n]*"|'[^'\n]*'|\S[^\n]*?)
    [ \t]*(?:[ \t]\#.*)?$
    """
)
# Kubernetes container env list:
#   - name: PORT
#     value: "8080"
# Spans two lines, so DOTALL/MULTILINE both matter.
_DEF_K8S_ENV_RE = re.compile(
    r"""(?xms)
    -[ \t]*name:[ \t]*
    (?P<name>[A-Z_][A-Z0-9_]*)
    \s+
    value:[ \t]*
    (?P<value>"[^"\n]*"|'[^'\n]*'|[^\n]+?)
    [ \t]*$
    """
)

# Per-language patterns. A single name may have multiple defs across
# patterns (e.g. ``ENV X=1`` later overridden by ``X=2`` in a RUN). The
# detector keeps the FIRST match — matching how a reader scans top-to-bottom.
_INLINE_DEFS_BY_LANG: Final[dict[str, tuple[re.Pattern[str], ...]]] = {
    "yaml": (_DEF_YAML_RE, _DEF_K8S_ENV_RE),
    "dockerfile": (_DEF_DOCKERFILE_RE, _DEF_SHELL_RE),
    "bash": (_DEF_SHELL_RE,),
    "fish": (_DEF_SHELL_RE,),
    "shell": (_DEF_SHELL_RE,),
}


def _unquote(raw: str) -> str:
    """Strip matching outer quotes from a captured YAML/shell value literal."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        return raw[1:-1]
    return raw


def detect_inline_defs(text: str, language: str) -> dict[str, str]:
    """Extract ``NAME -> value`` pairs from inline definitions in ``text``.

    Returns the first occurrence of each name. Empty dict for languages
    that don't have a definition syntax we recognize (Python / JS / TS:
    those use ``os.getenv("X", "default")`` and ``process.env.X`` — the
    second-arg ``default`` is already captured by the reference detector).
    """
    if not text:
        return {}
    patterns = _INLINE_DEFS_BY_LANG.get(language)
    if patterns is None:
        return {}

    defs: dict[str, str] = {}
    for pat in patterns:
        for match in pat.finditer(text):
            name = match.group("name")
            if name in defs:
                continue
            defs[name] = _unquote(match.group("value"))
    return defs


# --- Safety policy -----------------------------------------------------------

# Case-insensitive substring tokens. Any name containing one of these is
# tier-1 hidden. Tight enough to keep DELETION_GRACE_PERIOD / LOG_LEVEL /
# DATABASE_HOST visible, broad enough to catch the obvious shapes.
_NAME_DENYLIST: Final[tuple[str, ...]] = (
    "KEY",
    "SECRET",
    "TOKEN",
    "PASSWORD",
    "PASSWD",
    "PWD",
    "CREDENTIAL",
    "PRIVATE",
    "AUTH",
    "SESSION",
    "COOKIE",
    "SALT",
    "SIGNATURE",
    "CERT",
    "BEARER",
)

# Per-value display cap. Above this, structured config dumps stop being
# auditor signal and start eating into the description budget.
_MAX_VALUE_DISPLAY: Final[int] = 200

# Hard cap on resolved entries rendered in the block. Detection still
# scans the full snippet; only rendering is capped.
_MAX_RENDERED: Final[int] = 50


# --- Data classes ------------------------------------------------------------


@dataclass(frozen=True)
class EnvRef:
    """A single detected env-var reference in a snippet."""

    name: str
    default: str | None  # literal default from the source, if any


@dataclass(frozen=True)
class ResolvedRef:
    """A reference after lookup + safety check.

    Exactly one of (value present) or (redacted_kind set) is true,
    except for the ``unset`` case where both are None.

    ``from_inline`` is True when the value came from an inline
    definition in the same snippet (e.g. a YAML ``env:`` block, a
    Dockerfile ``ARG``/``ENV`` line, or a shell ``export``). The
    auditor can spot the source by reading the snippet itself, so the
    rendered block does not annotate it specially.
    """

    name: str
    value: str | None
    redacted_kind: str | None
    used_default: bool
    is_unset: bool
    from_inline: bool = False


@dataclass
class EnvSummary:
    """Per-capture counts used by the markdown footer."""

    resolved: int = 0
    redacted: int = 0
    unset: int = 0
    refs: list[ResolvedRef] = field(default_factory=list)

    def any(self) -> bool:
        return (self.resolved + self.redacted + self.unset) > 0

    def short_form(self) -> str:
        """Footer-friendly summary string. Empty when nothing happened."""
        if not self.any():
            return ""
        parts: list[str] = []
        if self.resolved:
            parts.append(f"{self.resolved} env var{'s' if self.resolved != 1 else ''} resolved")
        if self.redacted:
            parts.append(f"{self.redacted} env redacted")
        if self.unset:
            parts.append(f"{self.unset} env unset")
        return ", ".join(parts)


# --- Public API --------------------------------------------------------------


def _detect_py_env_refs_via_ast(text: str) -> list[EnvRef] | None:
    """AST-based detection for Python ``os.getenv`` / ``os.environ`` refs.

    Returns a list when AST parsing succeeded, or ``None`` when the
    snippet failed to parse (caller falls back to regex). Using AST
    instead of text regex means string literals (``log("use os.getenv('X')")``)
    and docstrings don't false-match as code references (FG2).

    Recognized shapes:

    - ``os.getenv("X"[, "default"])``
    - ``os.environ.get("X"[, "default"])``
    - ``os.environ["X"]``

    Any non-literal first arg (``os.getenv(name)`` with ``name`` a
    variable) is silently skipped — same as the regex behavior.
    """
    candidates = [text, textwrap.dedent(text)]
    tree: ast.Module | None = None
    for candidate in candidates:
        try:
            tree = ast.parse(candidate)
            break
        except SyntaxError:
            continue
    if tree is None:
        return None

    seen: dict[str, EnvRef] = {}

    def _str_literal(node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def _add(name: str, default: str | None) -> None:
        existing = seen.get(name)
        if existing is None:
            seen[name] = EnvRef(name=name, default=default)
        elif existing.default is None and default is not None:
            seen[name] = EnvRef(name=name, default=default)

    for node in ast.walk(tree):
        # os.getenv("X"[, "default"])
        # os.environ.get("X"[, "default"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            attr = node.func
            is_getenv = attr.attr == "getenv" and isinstance(attr.value, ast.Name) and attr.value.id == "os"
            is_environ_get = (
                attr.attr == "get"
                and isinstance(attr.value, ast.Attribute)
                and attr.value.attr == "environ"
                and isinstance(attr.value.value, ast.Name)
                and attr.value.value.id == "os"
            )
            if (is_getenv or is_environ_get) and node.args:
                name = _str_literal(node.args[0])
                if name is None:
                    continue
                default = _str_literal(node.args[1]) if len(node.args) >= 2 else None
                _add(name, default)
        # os.environ["X"]
        elif isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
            attr = node.value
            if attr.attr == "environ" and isinstance(attr.value, ast.Name) and attr.value.id == "os":
                # Python 3.9+: slice is the expression directly.
                key_node = node.slice
                name = _str_literal(key_node)
                if name is not None:
                    _add(name, None)

    return list(seen.values())


def detect_env_refs(text: str, language: str) -> list[EnvRef]:
    """Return env-var references found in ``text`` for the given language.

    Order is first-seen and duplicates are removed: if ``OPENAI_API_KEY``
    appears 5 times, the result has one entry. Default literal is taken
    from the first occurrence that supplies one.

    For Python, AST-based detection is used so string literals and
    docstrings don't false-match (FG2). Regex fallback runs when AST
    parsing fails on a snippet fragment.

    A best-effort function: any regex failure raises an exception that
    callers should treat as a soft failure (capture continues, just
    without resolution).
    """
    if not text:
        return []

    if language in _PYTHON_LANGS:
        ast_refs = _detect_py_env_refs_via_ast(text)
        if ast_refs is not None:
            return ast_refs
        # AST failed (incomplete fragment); fall back to regex pass.
        patterns = [_PY_GETENV_RE, _PY_ENVIRON_SUBSCRIPT_RE]
    elif language in _JS_LANGS:
        patterns = [_JS_DOTTED_RE, _JS_BRACKET_RE]
    elif language in _SHELL_LANGS:
        # Order matters: ${...} and $(...) must run before $X so the
        # bare-form regex doesn't grab the leading ``$`` of a brace or
        # paren expression.
        patterns = [_SHELL_BRACE_RE, _SHELL_PAREN_RE, _SHELL_BARE_RE]
    else:
        return []

    seen: dict[str, EnvRef] = {}
    for pat in patterns:
        for match in pat.finditer(text):
            name = match.group("name")
            default = match.groupdict().get("default")
            existing = seen.get(name)
            if existing is None:
                seen[name] = EnvRef(name=name, default=default)
            elif existing.default is None and default is not None:
                # Upgrade the dedup'd entry with a default if a later
                # occurrence supplies one.
                seen[name] = EnvRef(name=name, default=default)
    return list(seen.values())


def _name_is_secret(name: str) -> str | None:
    """Return the matching denylist token, or None if the name is safe."""
    upper = name.upper()
    for token in _NAME_DENYLIST:
        if token in upper:
            return token
    return None


def _value_is_secret(value: str) -> str | None:
    """Run the value through redact(); return the kind that matched, or None.

    Reuses the snippet redactor as the tier-2 gate so the secret-shape
    catalogue stays in one place.
    """
    redacted, summary = redact(value, redact_secrets=True)
    if summary.any():
        # Most-frequent kind wins; ties broken by sort for determinism.
        kind, _ = max(summary.counts.items(), key=lambda kv: (kv[1], kv[0]))
        return kind
    return None


def resolve_refs(
    refs: Iterable[EnvRef],
    env: Mapping[str, str] | None = None,
    inline_defs: Mapping[str, str] | None = None,
) -> EnvSummary:
    """Resolve each detected reference against the available value sources.

    Resolution priority (highest first):

    1. **Inline definition** — a same-snippet assignment like a YAML
       ``env:`` mapping, a Dockerfile ``ARG``/``ENV``, or a shell
       ``export``. This is the source of truth for what the snippet
       evaluates to in production; the agent's local ``os.environ`` is
       incidental.
    2. **Process env** — ``os.environ`` at capture time.
    3. **Source default literal** — the second arg of
       ``os.getenv("X", "default")`` (Python only).
    4. **<unset>** — none of the above produced a value.

    Tier-1 (name denylist) and tier-2 (value redact) gates run AFTER
    the value source is chosen. Both must pass for the value to appear.

    Each ref produces one :class:`ResolvedRef` in the returned summary,
    in input order. The summary's counters reflect how many were
    resolved-clean vs. redacted vs. unset.
    """
    if env is None:
        env = os.environ
    if inline_defs is None:
        inline_defs = {}

    summary = EnvSummary()
    for ref in refs:
        denylist_hit = _name_is_secret(ref.name)
        if denylist_hit is not None:
            # Track where the value WOULD have come from so the source
            # column in the rendered table stays accurate even though
            # the value itself is hidden.
            from_inline_when_redacted = ref.name in inline_defs
            summary.refs.append(
                ResolvedRef(
                    name=ref.name,
                    value=None,
                    redacted_kind="secret-name",
                    used_default=False,
                    is_unset=False,
                    from_inline=from_inline_when_redacted,
                )
            )
            summary.redacted += 1
            continue

        # Pick value source by priority: inline def > process env > source default.
        value: str | None = None
        from_inline = False
        used_default = False
        if ref.name in inline_defs:
            value = inline_defs[ref.name]
            from_inline = True
        elif (env_value := env.get(ref.name)) is not None:
            value = env_value
        elif ref.default is not None:
            value = ref.default
            used_default = True

        if value is None:
            summary.refs.append(
                ResolvedRef(
                    name=ref.name,
                    value=None,
                    redacted_kind=None,
                    used_default=False,
                    is_unset=True,
                )
            )
            summary.unset += 1
            continue

        value_kind = _value_is_secret(value)
        if value_kind is not None:
            summary.refs.append(
                ResolvedRef(
                    name=ref.name,
                    value=None,
                    redacted_kind=value_kind,
                    used_default=used_default,
                    is_unset=False,
                    from_inline=from_inline,
                )
            )
            summary.redacted += 1
            continue

        summary.refs.append(
            ResolvedRef(
                name=ref.name,
                value=value,
                redacted_kind=None,
                used_default=used_default,
                is_unset=False,
                from_inline=from_inline,
            )
        )
        summary.resolved += 1

    return summary


def resolve_from_text(
    text: str,
    language: str,
    env: Mapping[str, str] | None = None,
) -> EnvSummary:
    """Convenience: detect refs + inline defs and resolve in one call.

    Soft-fails on regex error so a malformed snippet never aborts the
    user's evidence write.
    """
    try:
        refs = detect_env_refs(text, language)
        inline_defs = detect_inline_defs(text, language)
    except (re.error, ValueError) as exc:  # pragma: no cover — defensive
        logger.warning("evidence.env_resolve.detect_failed", extra={"error": str(exc)})
        return EnvSummary()
    try:
        return resolve_refs(refs, env=env, inline_defs=inline_defs)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("evidence.env_resolve.resolve_failed", extra={"error": str(exc)})
        return EnvSummary()


def _truncate(value: str, limit: int = _MAX_VALUE_DISPLAY) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "…"


def format_block(summary: EnvSummary) -> str | None:
    """Render the 'Resolved values at capture time' markdown block.

    Returns ``None`` when there's nothing to show, so callers can omit
    the block (and the surrounding blank line) entirely.

    Each line is one of:

        - `NAME` = `value`
        - `NAME` = `default` (default; env unset)
        - `NAME` = `[REDACTED:<kind>]`
        - `NAME` = `<unset>`
    """
    if not summary.any():
        return None

    rendered: list[str] = ["**Resolved values at capture time:**"]
    refs = summary.refs[:_MAX_RENDERED]
    overflow = len(summary.refs) - len(refs)

    for ref in refs:
        if ref.redacted_kind is not None:
            line = f"- `{ref.name}` = `[REDACTED:{ref.redacted_kind}]`"
        elif ref.is_unset:
            line = f"- `{ref.name}` = `<unset>`"
        elif ref.used_default and ref.value is not None:
            line = f"- `{ref.name}` = `{_truncate(ref.value)}` (default; env unset)"
        elif ref.value is not None:
            line = f"- `{ref.name}` = `{_truncate(ref.value)}`"
        else:  # pragma: no cover — defensive; redacted_kind covers None values
            line = f"- `{ref.name}` = `<unset>`"
        rendered.append(line)

    if overflow > 0:
        rendered.append(f"- *… and {overflow} more*")

    return "\n".join(rendered)
