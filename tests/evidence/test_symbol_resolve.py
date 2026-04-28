"""Tests for pretorin.evidence.symbol_resolve.

Cover detection (AST imports + UPPERCASE refs + builtin denylist),
definition lookup (AST hint + git grep + os.walk fallback +
config-path priority + self-reference guard), and the public
``resolve_symbols`` orchestrator.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pretorin.evidence.symbol_resolve import (
    Definition,
    Reference,
    SymbolSummary,
    _config_priority,
    _is_denylisted,
    detect_references,
    find_definition,
    find_git_root,
    resolve_symbols,
)
from tests._synthetic_fixtures import STRIPE_LIVE_KEY

# --- Detection: AST imports + UPPERCASE refs --------------------------------


class TestDetectImports:
    def test_from_import_uppercase_captured(self):
        src = "from app.config import DELETION_GRACE_PERIOD_DAYS\n"
        refs = detect_references(src, "python")
        assert refs == [Reference(name="DELETION_GRACE_PERIOD_DAYS", import_path="app.config", level=0)]

    def test_from_import_aliased_keeps_original_name(self):
        """`from x import Y as Z` traces Y, not Z, because Y is what
        the definition file uses."""
        src = "from app.config import DELETION_GRACE_PERIOD_DAYS as GRACE\n"
        refs = detect_references(src, "python")
        names = [r.name for r in refs]
        assert "DELETION_GRACE_PERIOD_DAYS" in names
        # The alias GRACE is too short to match the UPPERCASE rule;
        # it would also be skipped from the bare-ref pass (only 5 chars,
        # but Name nodes are picked up regardless of length when imported).
        assert "GRACE" not in [r.name for r in refs if r.import_path is None]

    def test_relative_import_carries_level(self):
        src = "from .config import DELETION_GRACE_PERIOD_DAYS\n"
        refs = detect_references(src, "python")
        assert len(refs) == 1
        assert refs[0].level == 1

    def test_lowercase_import_skipped(self):
        """`from logging import getLogger` shouldn't be traced."""
        src = "from logging import getLogger\n"
        refs = detect_references(src, "python")
        assert refs == []

    def test_star_import_skipped(self):
        src = "from app.config import *\n"
        refs = detect_references(src, "python")
        assert refs == []


class TestDetectBareUpperRefs:
    def test_simple_module_constant_used(self):
        src = "from app.config import DELETION_GRACE_PERIOD_DAYS\ndelta = timedelta(days=DELETION_GRACE_PERIOD_DAYS)\n"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        assert "DELETION_GRACE_PERIOD_DAYS" in names

    def test_string_literal_uppercase_not_traced(self):
        """The user's reported regression: `os.getenv("DELETION_GRACE_PERIOD")`
        contains an uppercase string literal that must NOT be traced as
        a code reference. AST Name nodes give us this for free."""
        src = 'import os\nGRACE = os.getenv("DELETION_GRACE_PERIOD", "300")\n'
        refs = detect_references(src, "python")
        # GRACE is too short to match (2 chars after first letter is OK
        # since regex requires 3+ chars total: `[A-Z][A-Z0-9_]{2,}` so
        # 5 chars 'GRACE' matches). But it IS a real Name node.
        assert any(r.name == "GRACE" for r in refs)
        # The string literal must NOT be detected.
        assert not any(r.name == "DELETION_GRACE_PERIOD" for r in refs)

    def test_attribute_access_uppercase_captured(self):
        """`config.MAX_RETRIES` matches via Attribute node walk."""
        src = "import config\nx = config.MAX_RETRIES\n"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        assert "MAX_RETRIES" in names

    def test_short_uppercase_skipped(self):
        """Short names like ``X``, ``OK`` aren't traced (3-char minimum)."""
        src = "X = 1\nOK = True\nFOO = 2\n"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        assert "X" not in names
        assert "OK" not in names
        assert "FOO" in names

    def test_unparseable_fragment_falls_back_to_regex(self):
        """An indented fragment that fails ast.parse() still yields
        UPPERCASE refs via the regex fallback."""
        src = "    x = SOME_CONSTANT + ANOTHER_VAR\n  unbalanced'string"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        # Regex fallback picks both up; AST would have failed.
        assert "SOME_CONSTANT" in names or "ANOTHER_VAR" in names

    def test_dedented_function_body_parses(self):
        """A captured function body usually has 4-space indentation.
        textwrap.dedent + AST should parse it."""
        src = "    user.x = MY_CONSTANT\n    return MY_CONSTANT * 2\n"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        assert "MY_CONSTANT" in names


class TestDenylist:
    @pytest.mark.parametrize("name", ["TRUE", "FALSE", "NONE", "NULL", "UTC", "ASCII", "STDIN", "STDOUT", "STDERR"])
    def test_builtin_excluded(self, name):
        assert _is_denylisted(name)

    @pytest.mark.parametrize("name", ["HTTP_200_OK", "HTTP_404_NOT_FOUND", "HTTP_409_CONFLICT", "HTTP_500"])
    def test_http_status_excluded(self, name):
        assert _is_denylisted(name)

    def test_legitimate_constant_not_denylisted(self):
        assert not _is_denylisted("DELETION_GRACE_PERIOD_DAYS")
        assert not _is_denylisted("MAX_RETRIES")

    def test_http_status_in_snippet_not_traced(self):
        """The screenshot's `HTTP_409_CONFLICT` is a fastapi status code,
        not a config constant. Tracing it would be noise."""
        src = "raise HTTPException(status_code=status.HTTP_409_CONFLICT)\n"
        refs = detect_references(src, "python")
        names = {r.name for r in refs}
        assert "HTTP_409_CONFLICT" not in names


class TestNonPython:
    def test_yaml_returns_empty(self):
        src = "key: value\n"
        assert detect_references(src, "yaml") == []

    def test_javascript_returns_empty(self):
        src = "const X = 'value';"
        assert detect_references(src, "javascript") == []

    def test_empty_text(self):
        assert detect_references("", "python") == []


# --- Repo discovery ---------------------------------------------------------


class TestFindGitRoot:
    def test_returns_repo_root(self, tmp_path: Path):
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        nested = repo / "a" / "b" / "c"
        nested.mkdir(parents=True)
        assert find_git_root(nested) == repo

    def test_returns_none_when_not_in_repo(self, tmp_path: Path):
        (tmp_path / "x").mkdir()
        assert find_git_root(tmp_path / "x") is None

    def test_handles_file_path_input(self, tmp_path: Path):
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        f = repo / "a.py"
        f.write_text("# stub\n")
        assert find_git_root(f) == repo


# --- find_definition (AST hint + grep) --------------------------------------


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Minimal repo: app/config.py defines a constant, app/main.py uses it."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    app = repo / "app"
    app.mkdir()
    (app / "__init__.py").write_text("")
    (app / "config.py").write_text(
        'DELETION_GRACE_PERIOD_DAYS = 30\nMAX_RETRIES = 5\nAPI_BASE_URL = "https://api.example.com"\n'
    )
    (app / "main.py").write_text("from app.config import DELETION_GRACE_PERIOD_DAYS\nx = DELETION_GRACE_PERIOD_DAYS\n")
    # Initialize a git repo so git grep works.
    try:
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "init"],
            cwd=repo,
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return repo


class TestFindDefinition:
    def test_finds_via_ast_hint(self, fake_repo: Path):
        defn = find_definition(
            "DELETION_GRACE_PERIOD_DAYS",
            fake_repo / "app" / "main.py",
            fake_repo,
            ast_hint=Reference(name="DELETION_GRACE_PERIOD_DAYS", import_path="app.config"),
        )
        assert defn is not None
        assert defn.file_path == "app/config.py"
        assert defn.line == 1
        assert defn.value == "30"

    def test_finds_via_grep_when_no_hint(self, fake_repo: Path):
        defn = find_definition(
            "MAX_RETRIES",
            fake_repo / "app" / "main.py",
            fake_repo,
            ast_hint=None,
        )
        assert defn is not None
        assert defn.file_path == "app/config.py"
        assert defn.value == "5"

    def test_self_reference_skipped(self, fake_repo: Path):
        """A symbol defined in the same file we're capturing should NOT
        be returned as a definition match. The auditor already sees the
        original snippet."""
        # main.py defines `x = DELETION_GRACE_PERIOD_DAYS` but NOT
        # ``DELETION_GRACE_PERIOD_DAYS`` itself. config.py is the real
        # definition. Make a self-defining file:
        self_def = fake_repo / "app" / "self_def.py"
        self_def.write_text("MY_LOCAL_CONST = 42\nx = MY_LOCAL_CONST\n")
        defn = find_definition(
            "MY_LOCAL_CONST",
            self_def,
            fake_repo,
            ast_hint=None,
        )
        # Symbol exists nowhere else, so the only match was the self-file.
        # The guard means we get None back.
        assert defn is None

    def test_redacts_secret_in_definition_slice(self, fake_repo: Path):
        """A definition like `STRIPE_KEY = "sk_live_xxx"` must be tier-2
        redacted in the embedded snippet. Uses the synthetic fixture
        from `tests._synthetic_fixtures` so GitHub's secret-scanning
        push protection doesn't flag the test source."""
        secret_def = fake_repo / "app" / "secrets.py"
        secret_def.write_text(f'# config\nSTRIPE_KEY = "{STRIPE_LIVE_KEY}"\nOTHER = 1\n')
        # Re-add so git grep sees it.
        try:
            subprocess.run(["git", "add", "."], cwd=fake_repo, check=True, capture_output=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        defn = find_definition(
            "STRIPE_KEY",
            fake_repo / "app" / "main.py",
            fake_repo,
            ast_hint=None,
        )
        assert defn is not None
        # Secret value in the slice is redacted.
        assert STRIPE_LIVE_KEY not in defn.snippet
        assert "[REDACTED:stripe_key]" in defn.snippet

    def test_returns_none_when_symbol_missing(self, fake_repo: Path):
        defn = find_definition(
            "NONEXISTENT_SYMBOL",
            fake_repo / "app" / "main.py",
            fake_repo,
            ast_hint=None,
        )
        assert defn is None


class TestExtractValue:
    """The RHS extractor handles the common Python assignment shapes."""

    def test_plain_assignment(self):
        from pretorin.evidence.symbol_resolve import _extract_value

        assert _extract_value("X = 30\n", "X", 1, 1) == "30"

    def test_annotated_assignment_extracts_rhs_only(self):
        """B18: PEP-526 ``X: int = 30`` must extract '30', not 'int = 30'."""
        from pretorin.evidence.symbol_resolve import _extract_value

        assert _extract_value("DELETION_GRACE_PERIOD_DAYS: int = 30\n", "DELETION_GRACE_PERIOD_DAYS", 1, 1) == "30"

    def test_annotated_complex_type(self):
        from pretorin.evidence.symbol_resolve import _extract_value

        # Final[dict[str, int]] is a real-world annotation form.
        assert _extract_value("X: Final[dict[str, int]] = {}\n", "X", 1, 1) == "{}"

    def test_url_fragment_preserved_in_string_value(self):
        """B9: # is only a comment when preceded by whitespace.
        URLs with #fragment must not lose the fragment."""
        from pretorin.evidence.symbol_resolve import _extract_value

        out = _extract_value("API_URL = 'https://api.example.com/v1#section'\n", "API_URL", 1, 1)
        assert "#section" in out

    def test_trailing_comment_still_stripped(self):
        from pretorin.evidence.symbol_resolve import _extract_value

        # Whitespace-then-# IS stripped, as before.
        assert _extract_value("X = 30  # the answer\n", "X", 1, 1) == "30"

    def test_no_match_when_name_not_present(self):
        from pretorin.evidence.symbol_resolve import _extract_value

        assert _extract_value("Y = 30\n", "X", 1, 1) == ""


class TestConfigPathPriority:
    """Files matching common config naming should sort before other matches."""

    def test_config_py_is_top_priority(self, tmp_path: Path):
        assert _config_priority(tmp_path / "config.py") < _config_priority(tmp_path / "main.py")

    def test_settings_py_is_top_priority(self, tmp_path: Path):
        assert _config_priority(tmp_path / "settings.py") == 0

    def test_test_files_are_deprioritized(self, tmp_path: Path):
        assert _config_priority(tmp_path / "test_thing.py") > _config_priority(tmp_path / "main.py")


# --- resolve_symbols (orchestrator) -----------------------------------------


class TestRelativeImportBound:
    """LG4: relative imports with deep ``level`` must not probe paths
    above the repo root."""

    def test_excessive_level_returns_none(self, tmp_path: Path):
        from pretorin.evidence.symbol_resolve import _resolve_import_path

        repo = tmp_path / "repo"
        sub = repo / "a" / "b"
        sub.mkdir(parents=True)
        captured = sub / "main.py"
        captured.write_text("# stub\n")
        # level=10 against a 2-deep file would otherwise walk past repo root.
        out = _resolve_import_path("config", level=10, code_file=captured, repo_root=repo)
        assert out is None


class TestGitGrepReturnsLine:
    """O1: ``git grep -nE`` returns (path, line) directly so the caller
    doesn't need to re-scan the matching file."""

    def test_returns_tuple(self, fake_repo: Path):
        from pretorin.evidence.symbol_resolve import _git_grep_definition

        hit = _git_grep_definition("MAX_RETRIES", fake_repo)
        # Either the function returns a tuple (path, line), or returns
        # None (e.g., git not installed in test env). The shape, when
        # present, is what matters.
        if hit is not None:
            path, line = hit
            assert path.name == "config.py"
            assert isinstance(line, int)
            assert line >= 1


class TestResolveSymbolsEndToEnd:
    def test_traces_imported_constant(self, fake_repo: Path):
        snippet = (
            "from app.config import DELETION_GRACE_PERIOD_DAYS\ndelta = timedelta(days=DELETION_GRACE_PERIOD_DAYS)\n"
        )
        out = resolve_symbols(snippet, "python", fake_repo / "app" / "main.py", repo_root=fake_repo)
        names = [d.name for d in out.definitions]
        assert "DELETION_GRACE_PERIOD_DAYS" in names
        # Source location preserved.
        defn = next(d for d in out.definitions if d.name == "DELETION_GRACE_PERIOD_DAYS")
        assert defn.file_path == "app/config.py"
        assert defn.value == "30"

    def test_python_only(self, tmp_path: Path):
        out = resolve_symbols("key: value", "yaml", tmp_path / "x.yaml")
        assert out.definitions == []
        assert out.references == []
        assert out.not_found == []

    def test_not_found_recorded(self, fake_repo: Path):
        snippet = "x = NEVER_DEFINED_ANYWHERE_NOT_REAL\n"
        out = resolve_symbols(snippet, "python", fake_repo / "app" / "main.py", repo_root=fake_repo)
        assert "NEVER_DEFINED_ANYWHERE_NOT_REAL" in out.not_found

    def test_short_form_summary(self, fake_repo: Path):
        snippet = (
            "from app.config import DELETION_GRACE_PERIOD_DAYS, MAX_RETRIES\n"
            "x = DELETION_GRACE_PERIOD_DAYS + MAX_RETRIES + UNKNOWN_X\n"
        )
        out = resolve_symbols(snippet, "python", fake_repo / "app" / "main.py", repo_root=fake_repo)
        text = out.short_form()
        assert "definitions traced" in text


class TestSymbolSummary:
    def test_empty_summary_short_form(self):
        assert SymbolSummary().short_form() == ""

    def test_singular_definition(self):
        s = SymbolSummary()
        s.definitions.append(Definition(name="X", file_path="a.py", line=1, value="1", snippet="X = 1"))
        assert s.short_form() == "1 definition traced"

    def test_plural(self):
        s = SymbolSummary()
        for i in range(3):
            s.definitions.append(Definition(name=f"X{i}", file_path="a.py", line=i + 1, value="0", snippet="x"))
        assert "3 definitions traced" in s.short_form()

    def test_not_found_reported(self):
        s = SymbolSummary()
        s.not_found = ["A", "B"]
        assert "2 not found" in s.short_form()
