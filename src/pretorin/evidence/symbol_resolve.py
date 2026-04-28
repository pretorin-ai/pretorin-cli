"""Trace Python symbol references in captured snippets to their definitions.

When a snippet captured for evidence references a module-level constant
defined in another file (e.g., ``from app.config import
DELETION_GRACE_PERIOD_DAYS``), the auditor needs to see WHERE that
constant is defined and WHAT VALUE it holds in the production codebase.

This module:

1. Parses the snippet's AST to extract ``import`` / ``from ... import ...``
   statements. The import path is the precise hint for finding the
   definition file.
2. Regex-scans the snippet for bare UPPERCASE references that aren't on
   a builtin denylist (HTTP status codes, ``UTC``, ``TRUE`` / ``FALSE`` /
   ``NONE``).
3. For each detected name, searches the captured file's git repo for
   the definition:
   - If an AST import path was captured, attempt to resolve it to a
     file under the repo root.
   - Otherwise (or as fallback), grep for ``^\\s*NAME\\s*[:=]`` across
     the repo tree, preferring config-shaped paths (``config.py``,
     ``settings.py``, ``constants.py``, ...).
4. Reads ±2 lines around the assignment line via :func:`snapshot.read_code`.
5. Runs the snippet through :func:`pretorin.evidence.redact.redact` so
   any embedded credentials in a definition file (e.g., a hardcoded
   ``STRIPE_KEY = "sk_live_..."``) are blocked even though the
   resolution found the right line.

Soft-fail at every step: a malformed AST, missing file, or grep failure
never aborts the user's evidence write. Each unresolved symbol is
recorded with ``found=False`` so the auditor sees it was searched and
not located.

Out of scope (intentionally):

- Recursive resolution (``X = int(os.getenv("Y"))`` does NOT also resolve Y).
- Class-attribute / pydantic-settings / dataclass field lookups.
- Languages other than Python.
- Cross-repo references.
"""

from __future__ import annotations

import ast
import logging
import os
import re
import shutil
import subprocess
import textwrap
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from pretorin.evidence.redact import redact
from pretorin.evidence.snapshot import SnapshotError, read_code

logger = logging.getLogger(__name__)


# --- Detection --------------------------------------------------------------

# Bare UPPERCASE reference: at least one letter followed by 2+ letter/digit/underscore.
# Three-char minimum keeps loop-index style names like ``I`` / ``J`` out.
_UPPER_REF_RE = re.compile(r"\b(?P<name>[A-Z][A-Z0-9_]{2,})\b")

# Builtin / stdlib UPPERCASE names that have well-known meanings and don't
# benefit from being traced. ``HTTP_`` status codes are excluded by prefix.
_BUILTIN_DENYLIST: Final[frozenset[str]] = frozenset(
    {
        "TRUE",
        "FALSE",
        "NONE",
        "NULL",
        "UTC",
        "ASCII",
        "MAXSIZE",
        "MAXINT",
        "STDIN",
        "STDOUT",
        "STDERR",
        "ENV",
        "PATH",
        "TYPE_CHECKING",
        "TYPE_HINT",
    }
)
_HTTP_STATUS_RE = re.compile(r"^HTTP_[0-9]{3}(_[A-Z0-9_]+)?$")

_PYTHON_LANGS: Final[frozenset[str]] = frozenset({"python"})


@dataclass(frozen=True)
class Reference:
    """A detected symbol reference inside the captured snippet.

    ``import_path`` is the dotted module name from the import statement
    (e.g., ``"app.config"`` for ``from app.config import X``). It's used
    as the AST hint for resolution. ``None`` when the symbol was found
    only via the bare-UPPERCASE regex pass.

    ``level`` carries the relative-import level for ``from . import X``
    (1) or ``from .. import X`` (2) — used to walk up from the captured
    file's directory rather than from the repo root.
    """

    name: str
    import_path: str | None = None
    level: int = 0


@dataclass(frozen=True)
class Definition:
    """A symbol's definition site, after a successful repo search."""

    name: str
    file_path: str  # path relative to the search root
    line: int  # 1-indexed line of the assignment
    value: str  # right-hand side of the assignment, raw text
    snippet: str  # redacted ±2-line context around the assignment


@dataclass
class SymbolSummary:
    """Result of a full snippet → definitions resolution pass."""

    references: list[Reference] = field(default_factory=list)
    definitions: list[Definition] = field(default_factory=list)
    not_found: list[str] = field(default_factory=list)
    skipped_denylist: list[str] = field(default_factory=list)

    def any_found(self) -> bool:
        return bool(self.definitions)

    def short_form(self) -> str:
        """Footer-friendly summary string."""
        parts: list[str] = []
        if self.definitions:
            n = len(self.definitions)
            parts.append(f"{n} definition{'s' if n != 1 else ''} traced")
        if self.not_found:
            parts.append(f"{len(self.not_found)} not found")
        return ", ".join(parts)


# --- Detection: AST + regex --------------------------------------------------


def _is_denylisted(name: str) -> bool:
    if name in _BUILTIN_DENYLIST:
        return True
    if _HTTP_STATUS_RE.match(name):
        return True
    return False


def _try_parse(text: str) -> ast.Module | None:
    """Best-effort Python parse.

    The captured snippet is often a fragment indented inside a larger
    function. ``textwrap.dedent`` strips common leading whitespace so a
    function body can parse on its own. When the dedented text still
    fails (incomplete statement, unbalanced quotes), returns None and
    the caller falls back to the regex pass.
    """
    candidates = [text, textwrap.dedent(text)]
    for candidate in candidates:
        try:
            return ast.parse(candidate)
        except SyntaxError:
            continue
    return None


def _detect_imports_via_ast(tree: ast.Module) -> dict[str, Reference]:
    """Extract ``from x.y import NAME`` named imports from a parsed tree.

    Returns ``{symbol_name: Reference}``. Aliased imports map the
    *original* name (``from x import Y as Z`` keeps ``Y``) because the
    definition lookup uses the original module path.
    """
    imports: dict[str, Reference] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            level = node.level or 0
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.name
                if name.isupper() and len(name) >= 3 and not _is_denylisted(name):
                    imports[name] = Reference(name=name, import_path=module, level=level)
    return imports


def _detect_uppercase_refs_via_ast(tree: ast.Module) -> set[str]:
    """Walk AST ``Name`` nodes and collect UPPERCASE identifiers.

    Using the AST instead of a text regex is the difference between
    matching a real identifier (``DELETION_GRACE_PERIOD_DAYS`` used in
    code) and matching the same string accidentally embedded in a
    string literal (``os.getenv("DELETION_GRACE_PERIOD")``). The
    string-literal case must NOT be traced as a symbol reference.
    """
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            n = node.id
            if n.isupper() and len(n) >= 3 and not _is_denylisted(n):
                names.add(n)
        elif isinstance(node, ast.Attribute):
            # Catch ``Module.CONSTANT_NAME`` attribute access.
            if node.attr.isupper() and len(node.attr) >= 3 and not _is_denylisted(node.attr):
                names.add(node.attr)
    return names


def _detect_uppercase_refs_via_regex(text: str) -> set[str]:
    """Regex fallback when AST parsing fails on the snippet.

    Less precise (catches names inside string literals/comments) but at
    least captures *something* for unparseable fragments.
    """
    names: set[str] = set()
    for match in _UPPER_REF_RE.finditer(text):
        name = match.group("name")
        if not _is_denylisted(name):
            names.add(name)
    return names


def detect_references(text: str, language: str) -> list[Reference]:
    """Detect symbol references in ``text``.

    Currently Python-only. Returns an empty list for any other language
    so callers can pass through without special-casing.

    Order is deterministic: AST-imported names first (preserving the
    ``import_path`` hint for resolution), then bare UPPERCASE
    references that weren't already captured via imports.
    """
    if not text or language not in _PYTHON_LANGS:
        return []

    tree = _try_parse(text)
    if tree is not None:
        imports = _detect_imports_via_ast(tree)
        bare = _detect_uppercase_refs_via_ast(tree)
    else:
        imports = {}
        bare = _detect_uppercase_refs_via_regex(text)

    refs: list[Reference] = []
    seen: set[str] = set()
    for name, ref in imports.items():
        refs.append(ref)
        seen.add(name)
    for name in sorted(bare):
        if name not in seen:
            refs.append(Reference(name=name, import_path=None, level=0))
            seen.add(name)
    return refs


# --- Repo / file discovery --------------------------------------------------


_SKIP_DIRS: Final[frozenset[str]] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        "target",
        "vendor",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "site-packages",
    }
)

_CONFIG_FILENAMES: Final[tuple[str, ...]] = (
    "config.py",
    "settings.py",
    "constants.py",
    "conf.py",
    "defaults.py",
    "env.py",
    "configuration.py",
)

_MAX_FILES_SCANNED: Final[int] = 5000
_MAX_BYTES_PER_FILE: Final[int] = 1024 * 1024
_MAX_WALL_TIME_SECONDS: Final[float] = 30.0
_DEFINITION_CONTEXT_LINES: Final[int] = 2


def find_git_root(start: Path) -> Path | None:
    """Walk up from ``start`` to find a directory containing ``.git``.

    Returns None when no repo root is found before reaching the
    filesystem root. Stops at the OS root to avoid infinite loops.

    Uses ``Path.resolve(strict=False)`` so the existence check and
    canonicalization happen in one syscall — eliminates a TOCTOU race
    if the path vanishes between checks (LG3).
    """
    p = start.resolve(strict=False) if isinstance(start, Path) else Path(start).resolve(strict=False)
    if p.is_file():
        p = p.parent
    while True:
        if (p / ".git").exists():
            return p
        if p.parent == p:
            return None
        p = p.parent


def _resolve_import_path(
    import_path: str,
    level: int,
    code_file: Path,
    repo_root: Path,
) -> Path | None:
    """Try to resolve ``import_path`` (with optional relative ``level``)
    to a concrete ``.py`` file under ``repo_root``.

    Returns None if no candidate exists. This is a best-effort resolver,
    not a full Python import-system reimplementation.
    """
    parts = [p for p in import_path.split(".") if p]
    candidates: list[Path] = []

    if level > 0:
        # Relative import: walk up from the captured file's directory.
        # Bound by ``repo_root`` so a pathologically deep ``level``
        # can't make us probe paths above the repo (LG4).
        base = code_file.resolve(strict=False).parent
        repo_root_resolved = repo_root.resolve(strict=False)
        for _ in range(level - 1):
            if base == repo_root_resolved or repo_root_resolved not in base.parents:
                # Don't ascend past the repo root.
                return None
            base = base.parent
        if parts:
            target = base.joinpath(*parts)
        else:
            target = base
        # Reject any candidate that escapes the repo root.
        candidates.append(target.with_suffix(".py"))
        candidates.append(target / "__init__.py")
        candidates = [
            c
            for c in candidates
            if repo_root_resolved == _safe_resolve(c).parents[0] or repo_root_resolved in _safe_resolve(c).parents
        ]
    else:
        # Absolute import: try repo_root and any parent directory between
        # the captured file and repo_root (covers monorepos where the
        # package is rooted at a subdirectory like ``apps/auth/app/``).
        if not parts:
            return None
        target_rel = Path(*parts)
        bases: list[Path] = [repo_root]
        # Walk up from code_file toward repo_root, adding each parent
        # as a candidate base so ``app.config`` resolves to
        # ``apps/auth/app/config.py`` when captured from
        # ``apps/auth/app/routers/privacy.py``.
        try:
            cur = code_file.resolve().parent
            while cur != repo_root.resolve() and repo_root.resolve() in cur.parents:
                bases.append(cur)
                cur = cur.parent
        except (OSError, ValueError):
            pass
        for base in bases:
            candidates.append(base / target_rel.with_suffix(".py"))
            candidates.append(base / target_rel / "__init__.py")

    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


_DEFINITION_LINE_RE = re.compile(r"^[ \t]*(?P<name>[A-Z_][A-Z0-9_]*)[ \t]*[:=]")


def _scan_file_for_definition(
    path: Path,
    name: str,
) -> int | None:
    """Return the 1-indexed line number of the first matching definition,
    or None when not present.

    Reads the file with a hard byte cap to avoid pathological inputs.
    """
    try:
        size = path.stat().st_size
    except OSError:
        return None
    if size > _MAX_BYTES_PER_FILE:
        return None
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for lineno, line in enumerate(f, start=1):
                m = _DEFINITION_LINE_RE.match(line)
                if m and m.group("name") == name:
                    return lineno
    except OSError:
        return None
    return None


def _config_priority(path: Path) -> int:
    """Sort key: lower means higher priority for definition lookup."""
    name = path.name.lower()
    if name in _CONFIG_FILENAMES:
        return 0
    if "config" in name or "settings" in name or "constants" in name:
        return 1
    if "test" in name.lower() or "spec" in name.lower():
        return 9  # heavy deprioritize tests
    return 5


def _git_grep_definition(
    name: str,
    repo_root: Path,
    exclude: Path | None = None,
) -> tuple[Path, int] | None:
    """Use ``git grep -nE`` to find a file:line defining ``name``.

    Returns ``(path, line_number)`` for the highest-priority matching
    file or None. Files matching ``exclude`` (typically the captured
    file itself) are filtered. Combining the file find and line lookup
    in one ``-nE`` call avoids the redundant per-file rescan that
    ``-lE`` + ``_scan_file_for_definition`` required (O1).
    """
    if not shutil.which("git"):
        return None
    pattern = rf"^[ \t]*{re.escape(name)}[ \t]*[:=]"
    try:
        result = subprocess.run(
            ["git", "grep", "-nE", pattern],
            cwd=repo_root,
            timeout=10,
            capture_output=True,
            text=True,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode not in (0, 1):
        return None

    # Each output line is ``path:lineno:match-text``. Split only on the
    # first two colons so file paths containing ``:`` survive.
    matches: list[tuple[Path, int]] = []
    for raw in result.stdout.splitlines()[:_MAX_FILES_SCANNED]:
        if not raw.strip():
            continue
        parts = raw.split(":", 2)
        if len(parts) < 3:
            continue
        path_str, lineno_str, _ = parts
        try:
            lineno = int(lineno_str)
        except ValueError:
            continue
        path = repo_root / path_str
        if exclude is not None and _safe_resolve(path) == exclude:
            continue
        matches.append((path, lineno))
    if not matches:
        return None

    # Per-file: keep the FIRST match (lowest line number).
    by_file: dict[Path, int] = {}
    for path, lineno in matches:
        if path not in by_file:
            by_file[path] = lineno

    # Sort files by config priority and return the top.
    sorted_files = sorted(by_file.keys(), key=_config_priority)
    top = sorted_files[0]
    return (top, by_file[top])


def _walk_grep_definition(
    name: str,
    repo_root: Path,
    deadline: float,
    exclude: Path | None = None,
) -> tuple[Path, int] | None:
    """``os.walk``-based fallback when ``git grep`` is unavailable.

    Returns ``(path, line)`` directly so the caller doesn't re-scan.
    Honors the same skip-dir / file-cap / time-cap limits as the git
    path. Short-circuits on the first ``config.py``-class match (O3) —
    priority 0 is unbeatable, so further scanning is wasted work.
    """
    candidates: list[tuple[Path, int]] = []
    files_scanned = 0
    for root, dirs, files in os.walk(repo_root):
        if time.monotonic() > deadline:
            break
        # Prune skip dirs in-place so os.walk doesn't descend into them.
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        for f in files:
            if files_scanned >= _MAX_FILES_SCANNED or time.monotonic() > deadline:
                break
            if not f.endswith(".py"):
                continue
            files_scanned += 1
            path = Path(root) / f
            if exclude is not None and _safe_resolve(path) == exclude:
                continue
            line = _scan_file_for_definition(path, name)
            if line is not None:
                candidates.append((path, line))
                # Priority 0 = canonical config filename. Can't be
                # beaten by a later match, so stop scanning early.
                if _config_priority(path) == 0:
                    return (path, line)
        if files_scanned >= _MAX_FILES_SCANNED or time.monotonic() > deadline:
            break
    if not candidates:
        return None
    candidates.sort(key=lambda c: _config_priority(c[0]))
    return candidates[0]


def _safe_resolve(p: Path) -> Path:
    try:
        return p.resolve()
    except OSError:
        return p


def find_definition(
    name: str,
    code_file: Path,
    repo_root: Path,
    *,
    ast_hint: Reference | None = None,
    deadline: float | None = None,
) -> Definition | None:
    """Locate ``name``'s definition under ``repo_root`` and slice ±2 lines.

    Strategy:
    1. If ``ast_hint`` carries an import path, attempt to resolve it.
       When that file contains the name, use it.
    2. Otherwise (or when (1) misses), use ``git grep`` if available,
       falling back to ``os.walk``.
    3. Read ±2 lines around the assignment. Run the slice through
       :func:`redact` so credentials inside a definition file (e.g.,
       a hardcoded API key) don't leak into the captured evidence.

    Soft-fails to None on any error.
    """
    if deadline is None:
        deadline = time.monotonic() + _MAX_WALL_TIME_SECONDS

    target_file: Path | None = None
    target_line: int | None = None

    # Self-reference guard: never trace a symbol back to the file we're
    # already capturing. The original snippet is already shown; the
    # auditor doesn't need a duplicate fence.
    code_file_resolved = code_file.resolve() if code_file.exists() else code_file

    def _is_self(p: Path) -> bool:
        try:
            return p.resolve() == code_file_resolved
        except OSError:
            return False

    if ast_hint is not None and (ast_hint.import_path or ast_hint.level > 0):
        candidate = _resolve_import_path(
            ast_hint.import_path or "",
            ast_hint.level,
            code_file,
            repo_root,
        )
        if candidate is not None and not _is_self(candidate):
            line = _scan_file_for_definition(candidate, name)
            if line is not None:
                target_file = candidate
                target_line = line

    if target_file is None:
        # ``_git_grep_definition`` now returns (path, line) directly so
        # we don't pay the cost of re-scanning the file ourselves.
        grep_hit = _git_grep_definition(name, repo_root, exclude=code_file_resolved)
        if grep_hit is not None:
            target_file, target_line = grep_hit
        elif time.monotonic() < deadline:
            walk_hit = _walk_grep_definition(name, repo_root, deadline, exclude=code_file_resolved)
            if walk_hit is not None:
                target_file, target_line = walk_hit

    if target_file is None or target_line is None:
        return None

    # Read ±N lines for context. read_code wants a 1-indexed inclusive range.
    start = max(1, target_line - _DEFINITION_CONTEXT_LINES)
    end = target_line + _DEFINITION_CONTEXT_LINES
    try:
        snap = read_code(target_file, line_range=f"{start}-{end}")
    except SnapshotError:
        return None

    redacted_snippet, _ = redact(snap.text, redact_secrets=True)
    raw_value = _extract_value(redacted_snippet, name, target_line, start)

    try:
        rel_path = target_file.relative_to(repo_root)
    except ValueError:
        rel_path = target_file
    return Definition(
        name=name,
        file_path=str(rel_path),
        line=target_line,
        value=raw_value,
        snippet=redacted_snippet,
    )


def _extract_value(snippet: str, name: str, target_line: int, start_line: int) -> str:
    """Pull the right-hand side of the ``name = value`` assignment from a slice.

    The slice starts at ``start_line``; the assignment is at
    ``target_line``. Returns the raw RHS, stripped.

    Anchors on ``=`` only (with optional ``: type`` annotation between
    name and ``=``) so PEP-526 annotated assignments like
    ``DELETION_GRACE_PERIOD_DAYS: int = 30`` extract ``30`` rather than
    ``int = 30`` (B18).

    Trailing comments (``# ...``) are stripped only when preceded by
    whitespace. This keeps URL fragments like
    ``https://api.example.com/v1#section`` intact (B9).
    """
    lines = snippet.splitlines()
    idx = target_line - start_line
    if idx < 0 or idx >= len(lines):
        return ""
    line = lines[idx]
    m = re.match(
        rf"^[ \t]*{re.escape(name)}[ \t]*"
        r"(?::[^=\n]+)?"  # optional type annotation
        r"\s*=\s*"
        r"(?P<value>.*?)"
        r"\s*(?:[ \t]\#.*)?$",  # comment must be preceded by whitespace
        line,
    )
    if not m:
        return ""
    return m.group("value").strip()


# --- Public orchestration ---------------------------------------------------


def resolve_symbols(
    text: str,
    language: str,
    code_file: str | Path,
    repo_root: Path | None = None,
) -> SymbolSummary:
    """Detect references in ``text`` and resolve each to a definition.

    Args:
        text: The captured snippet body (already read; no I/O).
        language: Composer language tag (e.g. ``"python"``).
        code_file: Path of the captured file, used as the resolution
            anchor for relative imports and as the search root fallback
            when the file isn't in a git repo.
        repo_root: Optional explicit repo root. Defaults to the git
            repo containing ``code_file`` (or its parent dir if no git
            repo is detected).

    Soft-fails to an empty summary on any error.
    """
    summary = SymbolSummary()
    if language not in _PYTHON_LANGS:
        return summary

    try:
        refs = detect_references(text, language)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning("evidence.symbol_resolve.detect_failed", extra={"error": str(exc)})
        return summary
    summary.references = refs
    if not refs:
        return summary

    code_path = Path(code_file)
    root = repo_root
    if root is None:
        root = find_git_root(code_path) or (code_path.parent if code_path.parent != code_path else Path.cwd())

    deadline = time.monotonic() + _MAX_WALL_TIME_SECONDS
    # Track the index in the loop instead of calling refs.index(ref)
    # per iteration — that was O(N) per timeout-detection, which could
    # become quadratic in the worst case (O4).
    for i, ref in enumerate(refs):
        if time.monotonic() > deadline:
            for remaining in refs[i:]:
                if remaining.name not in summary.not_found:
                    summary.not_found.append(remaining.name)
            break
        try:
            defn = find_definition(
                ref.name,
                code_path,
                root,
                ast_hint=ref,
                deadline=deadline,
            )
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "evidence.symbol_resolve.find_failed",
                extra={"name": ref.name, "error": str(exc)},
            )
            defn = None
        if defn is None:
            summary.not_found.append(ref.name)
        else:
            summary.definitions.append(defn)

    return summary
