"""Tests for pretorin.evidence.env_resolve.

Covers detection per supported language, two-tier safety
(name-denylist + value-redact), default handling, deduplication, and
the rendered Markdown block.
"""

from __future__ import annotations

import pytest

from pretorin.evidence.env_resolve import (
    EnvRef,
    EnvSummary,
    ResolvedRef,
    detect_env_refs,
    detect_inline_defs,
    format_block,
    resolve_from_text,
    resolve_refs,
)
from tests._synthetic_fixtures import AWS_AKIA, GITHUB_PAT, STRIPE_LIVE_KEY


class TestDetectPython:
    def test_os_getenv_simple(self):
        refs = detect_env_refs('x = os.getenv("DELETION_GRACE_PERIOD")', "python")
        assert refs == [EnvRef(name="DELETION_GRACE_PERIOD", default=None)]

    def test_os_getenv_with_default(self):
        refs = detect_env_refs('x = os.getenv("PORT", "8080")', "python")
        assert refs == [EnvRef(name="PORT", default="8080")]

    def test_os_environ_subscript(self):
        refs = detect_env_refs('x = os.environ["API_HOST"]', "python")
        assert refs == [EnvRef(name="API_HOST", default=None)]

    def test_os_environ_get(self):
        refs = detect_env_refs('x = os.environ.get("LOG_LEVEL")', "python")
        assert refs == [EnvRef(name="LOG_LEVEL", default=None)]

    def test_os_environ_get_with_default(self):
        refs = detect_env_refs('x = os.environ.get("LOG_LEVEL", "info")', "python")
        assert refs == [EnvRef(name="LOG_LEVEL", default="info")]

    def test_dynamic_key_skipped(self):
        """Non-literal keys are out of scope — no crash, no false match."""
        src = "name = 'X'\nx = os.getenv(name)\n"
        assert detect_env_refs(src, "python") == []

    def test_single_quotes_supported(self):
        refs = detect_env_refs("x = os.getenv('PORT', '8080')", "python")
        assert refs == [EnvRef(name="PORT", default="8080")]

    def test_no_python_in_shell_language(self):
        """Don't cross-detect Python patterns when the file is a shell script."""
        src = 'x = os.getenv("FOO")'
        assert detect_env_refs(src, "bash") == []


class TestPythonAstSkipsStringLiterals:
    """FG2: env_resolve must use AST for Python so string-literal /
    docstring content doesn't false-match as code references."""

    def test_docstring_does_not_false_match(self):
        src = '"""\n    Use os.getenv("FAKE_FROM_DOCSTRING") to read it at runtime.\n"""\nx = os.getenv("REAL_REF")\n'
        refs = detect_env_refs(src, "python")
        names = {r.name for r in refs}
        assert "REAL_REF" in names
        assert "FAKE_FROM_DOCSTRING" not in names

    def test_string_literal_does_not_false_match(self):
        src = 'msg = "use os.getenv(\\"FAKE_VAR\\") at startup"\nreal = os.getenv("REAL_VAR")\n'
        refs = detect_env_refs(src, "python")
        names = {r.name for r in refs}
        assert "REAL_VAR" in names
        assert "FAKE_VAR" not in names

    def test_comment_does_not_false_match(self):
        src = '# os.getenv("COMMENTED_VAR") would be wrong\nx = os.getenv("REAL_VAR")\n'
        refs = detect_env_refs(src, "python")
        names = {r.name for r in refs}
        assert "REAL_VAR" in names
        assert "COMMENTED_VAR" not in names

    def test_dynamic_first_arg_skipped(self):
        """``os.getenv(name)`` (variable arg) is silently skipped, same
        as the regex behavior."""
        src = "name = 'X'\nx = os.getenv(name)\n"
        refs = detect_env_refs(src, "python")
        assert refs == []

    def test_unparseable_fragment_falls_back_to_regex(self):
        """Indented function-body fragments still detect via regex
        when AST parsing fails on every dedent variant."""
        src = '   x = os.getenv("FRAG_VAR")\n  if True:'
        refs = detect_env_refs(src, "python")
        # Either AST handles it or regex does — but the var is detected.
        names = {r.name for r in refs}
        assert "FRAG_VAR" in names


class TestYamlInlineDefUrlFragment:
    """B2: YAML inline def must preserve URL fragments (#section)."""

    def test_yaml_url_fragment_preserved(self):
        defs = detect_inline_defs("URL: https://api.example.com/v1#section\n", "yaml")
        assert defs.get("URL") == "https://api.example.com/v1#section"

    def test_yaml_comment_still_stripped_when_whitespace_prefixed(self):
        defs = detect_inline_defs("PORT: 8080  # the port\n", "yaml")
        assert defs.get("PORT") == "8080"

    def test_yaml_url_with_no_fragment(self):
        """Sanity: clean URL still works."""
        defs = detect_inline_defs("API: https://api.example.com/v1\n", "yaml")
        assert defs.get("API") == "https://api.example.com/v1"


class TestDetectJS:
    @pytest.mark.parametrize("lang", ["javascript", "typescript", "jsx", "tsx"])
    def test_dotted_form(self, lang):
        refs = detect_env_refs("const x = process.env.LOG_LEVEL;", lang)
        assert refs == [EnvRef(name="LOG_LEVEL", default=None)]

    @pytest.mark.parametrize("lang", ["javascript", "typescript"])
    def test_bracket_form(self, lang):
        refs = detect_env_refs('const x = process.env["API_HOST"];', lang)
        assert refs == [EnvRef(name="API_HOST", default=None)]


class TestDetectShell:
    def test_brace_form(self):
        refs = detect_env_refs('echo "${PORT}"', "bash")
        assert refs == [EnvRef(name="PORT", default=None)]

    def test_brace_with_colon_default(self):
        refs = detect_env_refs('echo "${PORT:-8080}"', "bash")
        assert refs == [EnvRef(name="PORT", default="8080")]

    def test_brace_with_dash_default(self):
        refs = detect_env_refs('echo "${PORT-8080}"', "bash")
        assert refs == [EnvRef(name="PORT", default="8080")]

    def test_bare_form(self):
        refs = detect_env_refs("export PATH=$HOME/bin", "bash")
        names = sorted(r.name for r in refs)
        assert names == ["HOME"]

    def test_positionals_and_specials_excluded(self):
        """$0, $1, $?, $@, $$ are not env vars — exclude them."""
        src = "echo $0 $1 $@ $? $$ $HOME"
        refs = detect_env_refs(src, "bash")
        assert [r.name for r in refs] == ["HOME"]

    def test_brace_takes_precedence_over_bare(self):
        """${X:-default} should produce ONE ref (X with default), not also X bare."""
        refs = detect_env_refs("echo ${PORT:-8080}", "bash")
        assert refs == [EnvRef(name="PORT", default="8080")]

    def test_lowercase_bare_form_excluded(self):
        """Bare $var (lowercase) is not a conventional env-var reference;
        excluded so YAML JSON-schema artifacts (`$ref`, `$schema`) don't
        false-match. The brace form keeps lowercase support."""
        assert detect_env_refs("echo $foo", "bash") == []
        # Brace form with lowercase still matches.
        assert detect_env_refs("echo ${foo}", "bash") == [EnvRef(name="foo", default=None)]


class TestDetectYamlAndDockerfile:
    """CI workflows / k8s manifests / docker-compose / Dockerfile commonly
    embed shell-style ``$VAR`` interpolation. Treat YAML and Dockerfile
    as shell-family for detection purposes."""

    def test_github_actions_run_block_shell_refs(self):
        """The user's reported case: --target "$TARGET" inside a `run: |` block."""
        src = """
        - name: Run Shannon Lite
          env:
            TARGET: ${{ secrets.PENTEST_STAGING_URL }}
            AUTH: ${{ secrets.PENTEST_AUTH_TOKEN }}
            SHANNON_BUDGET_USD: "200"
          run: |
            shannon scan \\
              --target "$TARGET" \\
              --auth-header "Authorization: Bearer $AUTH" \\
              --budget-usd "$SHANNON_BUDGET_USD"
        """
        refs = detect_env_refs(src, "yaml")
        names = {r.name for r in refs}
        # The shell-style references in the run: block are detected.
        assert "TARGET" in names
        assert "AUTH" in names
        assert "SHANNON_BUDGET_USD" in names

    def test_github_actions_template_syntax_not_matched(self):
        """${{ secrets.X }} is GitHub Actions template syntax — double braces.
        It must NOT match the shell ${X} pattern."""
        src = "TARGET: ${{ secrets.PENTEST_STAGING_URL }}"
        refs = detect_env_refs(src, "yaml")
        # No `secrets`, no `PENTEST_STAGING_URL` resolved as an env var.
        names = {r.name for r in refs}
        assert "secrets" not in names
        assert "PENTEST_STAGING_URL" not in names

    def test_json_schema_yaml_does_not_false_match(self):
        """OpenAPI / JSON-schema YAML uses $ref and $schema keys.
        The uppercase-first rule keeps these out of the resolved block."""
        src = """
        components:
          schemas:
            User:
              $ref: "#/definitions/User"
              $schema: "http://json-schema.org/draft-07/schema#"
        """
        refs = detect_env_refs(src, "yaml")
        names = {r.name for r in refs}
        assert "ref" not in names
        assert "schema" not in names

    def test_dockerfile_arg_and_env(self):
        src = """
        ARG NODE_VERSION=18
        FROM node:${NODE_VERSION}
        ENV APP_PORT=8080
        RUN echo "Listening on $APP_PORT"
        """
        refs = detect_env_refs(src, "dockerfile")
        names = {r.name for r in refs}
        assert "NODE_VERSION" in names
        assert "APP_PORT" in names

    def test_yaml_brace_with_default(self):
        src = 'command: ["sh", "-c", "exec /app/bin --port ${APP_PORT:-8080}"]'
        refs = detect_env_refs(src, "yaml")
        assert EnvRef(name="APP_PORT", default="8080") in refs


class TestKubernetesParenSyntax:
    """Kubernetes uses $(VAR_NAME) for env interpolation in
    container.command / args / env. Different from shell command
    substitution because the names are uppercase env-var conventional."""

    def test_k8s_paren_ref_detected(self):
        src = 'command: ["/app", "--port", "$(PORT)", "--log", "$(LOG_LEVEL)"]'
        refs = detect_env_refs(src, "yaml")
        names = {r.name for r in refs}
        assert "PORT" in names
        assert "LOG_LEVEL" in names

    def test_shell_command_substitution_not_matched(self):
        """$(date) / $(pwd) are bash command substitution, lowercase.
        The uppercase rule keeps these out of the resolved block."""
        src = 'echo "build at $(date) by $(whoami) in $(pwd)"'
        refs = detect_env_refs(src, "bash")
        assert refs == []


class TestInlineDefinitions:
    """Inline definitions in the snippet take priority over the agent's
    process env. The snippet defines what production evaluates to; the
    agent's env is incidental."""

    def test_yaml_env_block_extracted(self):
        src = """
        env:
          SHANNON_BUDGET_USD: "200"
          TARGET: ${{ secrets.PENTEST_STAGING_URL }}
          AUTH: ${{ secrets.PENTEST_AUTH_TOKEN }}
        """
        defs = detect_inline_defs(src, "yaml")
        assert defs["SHANNON_BUDGET_USD"] == "200"
        assert defs["TARGET"] == "${{ secrets.PENTEST_STAGING_URL }}"
        assert defs["AUTH"] == "${{ secrets.PENTEST_AUTH_TOKEN }}"

    def test_dockerfile_arg_and_env_extracted(self):
        src = 'ARG NODE_VERSION=18\nENV APP_PORT="8080"\nENV REGION us-east-1\n'
        defs = detect_inline_defs(src, "dockerfile")
        assert defs["NODE_VERSION"] == "18"
        assert defs["APP_PORT"] == "8080"
        assert defs["REGION"] == "us-east-1"

    def test_shell_export_extracted(self):
        src = 'export DATABASE_URL="postgres://localhost:5432/app"\nexport LOG_LEVEL=debug\n'
        defs = detect_inline_defs(src, "bash")
        assert defs["DATABASE_URL"] == "postgres://localhost:5432/app"
        assert defs["LOG_LEVEL"] == "debug"

    def test_k8s_env_list_extracted(self):
        src = """
        env:
        - name: PORT
          value: "8080"
        - name: LOG_LEVEL
          value: "info"
        """
        defs = detect_inline_defs(src, "yaml")
        assert defs["PORT"] == "8080"
        assert defs["LOG_LEVEL"] == "info"

    def test_lowercase_yaml_keys_excluded(self):
        """`name: foo`, `kind: Deployment` are k8s structural fields,
        not env-var definitions. The uppercase rule keeps them out."""
        src = """
        apiVersion: apps/v1
        kind: Deployment
        metadata:
          name: api
        """
        defs = detect_inline_defs(src, "yaml")
        assert defs == {}

    def test_first_occurrence_wins_on_duplicate(self):
        src = "ARG NODE_VERSION=18\nARG NODE_VERSION=20\n"
        defs = detect_inline_defs(src, "dockerfile")
        assert defs["NODE_VERSION"] == "18"

    def test_python_returns_empty(self):
        """Python module assignments (`KEY = "value"`) are not env
        var definitions. Only the os.getenv default-arg form counts,
        and that's handled by the reference detector."""
        src = 'KEY = "value"\nOPENAI_API_KEY = "sk_xxx"\n'
        defs = detect_inline_defs(src, "python")
        assert defs == {}

    def test_javascript_returns_empty(self):
        src = 'const KEY = "value"; const X = process.env.X;'
        defs = detect_inline_defs(src, "javascript")
        assert defs == {}


class TestResolutionPriorityOrder:
    """Inline def beats process env beats source default."""

    def test_inline_def_beats_process_env(self):
        refs = [EnvRef(name="LOG_LEVEL", default=None)]
        out = resolve_refs(
            refs,
            env={"LOG_LEVEL": "debug"},
            inline_defs={"LOG_LEVEL": "info"},
        )
        assert out.refs[0].value == "info"
        assert out.refs[0].from_inline is True
        assert out.refs[0].used_default is False

    def test_process_env_beats_source_default(self):
        refs = [EnvRef(name="LOG_LEVEL", default="info")]
        out = resolve_refs(
            refs,
            env={"LOG_LEVEL": "debug"},
            inline_defs={},
        )
        assert out.refs[0].value == "debug"
        assert out.refs[0].used_default is False

    def test_source_default_when_neither_inline_nor_env(self):
        refs = [EnvRef(name="LOG_LEVEL", default="info")]
        out = resolve_refs(refs, env={}, inline_defs={})
        assert out.refs[0].value == "info"
        assert out.refs[0].used_default is True
        assert out.refs[0].from_inline is False

    def test_inline_def_for_unset_env_with_no_default(self):
        """The user's primary case: snippet defines SHANNON_BUDGET_USD
        and references $SHANNON_BUDGET_USD. Resolves to the inline value
        even though the agent's env has nothing set."""
        refs = [EnvRef(name="SHANNON_BUDGET_USD", default=None)]
        out = resolve_refs(
            refs,
            env={},
            inline_defs={"SHANNON_BUDGET_USD": "200"},
        )
        assert out.resolved == 1
        assert out.refs[0].value == "200"
        assert out.refs[0].from_inline is True

    def test_inline_def_runs_through_tier1(self):
        """Inline def with a secret-shaped name still tier-1 redacts."""
        refs = [EnvRef(name="OPENAI_API_KEY", default=None)]
        out = resolve_refs(
            refs,
            env={},
            inline_defs={"OPENAI_API_KEY": "sk_live_xxx_inline"},
        )
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "secret-name"

    def test_inline_def_runs_through_tier2(self):
        """Inline def with a credential-bearing URL value still tier-2 redacts."""
        refs = [EnvRef(name="DATABASE_URL", default=None)]
        out = resolve_refs(
            refs,
            env={},
            inline_defs={"DATABASE_URL": "postgres://user:hunter2@db.example.com/app"},
        )
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "cred_url"


class TestEndToEndUserScenario:
    """The user's reported workflow capture from the screenshot."""

    def test_github_actions_workflow_renders_inline_values(self, monkeypatch):
        """Reproduces the user's GH workflow. SHANNON_BUDGET_USD is "200"
        in the env: block; auditor must see "200" not "<unset>" even
        though the agent's local shell has nothing set."""
        # Make sure the local env doesn't have any of these set.
        for var in ("TARGET", "AUTH", "SHANNON_BUDGET_USD", "OPENAI_API_KEY"):
            monkeypatch.delenv(var, raising=False)
        src = """
        - name: Run Shannon Lite
          env:
            OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
            SHANNON_BUDGET_USD: "200"
            TARGET: ${{ secrets.PENTEST_STAGING_URL }}
            AUTH: ${{ secrets.PENTEST_AUTH_TOKEN }}
          run: |
            shannon scan \\
              --target "$TARGET" \\
              --auth-header "Authorization: Bearer $AUTH" \\
              --budget-usd "$SHANNON_BUDGET_USD"
        """
        out = resolve_from_text(src, "yaml")
        by_name = {r.name: r for r in out.refs}
        # The three referenced vars all appear with values from the env block.
        assert by_name["SHANNON_BUDGET_USD"].value == "200"
        assert by_name["TARGET"].value == "${{ secrets.PENTEST_STAGING_URL }}"
        # AUTH name matches denylist → tier-1 redact even though defined inline.
        assert by_name["AUTH"].redacted_kind == "secret-name"


class TestDetectEdgeCases:
    def test_empty_text(self):
        assert detect_env_refs("", "python") == []

    def test_unknown_language(self):
        """Unrecognized language tags get an empty list — safer than guessing."""
        assert detect_env_refs('os.getenv("X")', "rust") == []
        assert detect_env_refs('os.getenv("X")', "text") == []

    def test_dedupe_preserves_first_seen_order(self):
        src = 'a = os.getenv("BETA")\nb = os.getenv("ALPHA")\nc = os.getenv("BETA")\nd = os.getenv("ALPHA")\n'
        refs = detect_env_refs(src, "python")
        assert [r.name for r in refs] == ["BETA", "ALPHA"]

    def test_dedupe_upgrades_default_on_later_match(self):
        """First call had no default; later call supplied one. Keep the default."""
        src = 'a = os.getenv("PORT")\nb = os.getenv("PORT", "8080")\n'
        refs = detect_env_refs(src, "python")
        assert refs == [EnvRef(name="PORT", default="8080")]


class TestResolveRefsHappyPath:
    def test_safe_name_value_present(self):
        refs = [EnvRef(name="DELETION_GRACE_PERIOD", default=None)]
        out = resolve_refs(refs, env={"DELETION_GRACE_PERIOD": "3600"})
        assert out.resolved == 1
        assert out.redacted == 0
        assert out.unset == 0
        assert out.refs[0] == ResolvedRef(
            name="DELETION_GRACE_PERIOD",
            value="3600",
            redacted_kind=None,
            used_default=False,
            is_unset=False,
        )

    def test_default_env_falls_back_to_os_environ(self, monkeypatch: pytest.MonkeyPatch):
        """When env=None, the resolver reads os.environ live."""
        monkeypatch.setenv("PRETORIN_TEST_SENTINEL", "ok")
        refs = [EnvRef(name="PRETORIN_TEST_SENTINEL", default=None)]
        out = resolve_refs(refs)
        assert out.refs[0].value == "ok"

    def test_unset_no_default(self):
        refs = [EnvRef(name="MISSING_VAR", default=None)]
        out = resolve_refs(refs, env={})
        assert out.unset == 1
        assert out.refs[0].is_unset is True
        assert out.refs[0].value is None
        assert out.refs[0].redacted_kind is None

    def test_unset_with_source_default(self):
        refs = [EnvRef(name="LOG_LEVEL", default="info")]
        out = resolve_refs(refs, env={})
        assert out.resolved == 1
        assert out.refs[0].used_default is True
        assert out.refs[0].value == "info"
        assert out.refs[0].is_unset is False


class TestResolveRefsTier1NameDenylist:
    @pytest.mark.parametrize(
        "name",
        [
            "OPENAI_API_KEY",
            "STRIPE_SECRET",
            "GITHUB_TOKEN",
            "DB_PASSWORD",
            "DB_PASSWD",
            "USER_PWD",
            "AWS_CREDENTIALS",
            "PRIVATE_KEY",
            "AUTH_HEADER",
            "SESSION_ID",
            "SESSION_COOKIE",
            "HMAC_SALT",
            "SIGNATURE_KEY",
            "TLS_CERT",
            "BEARER_HEADER",
        ],
    )
    def test_each_denylist_token_blocks_value(self, name):
        refs = [EnvRef(name=name, default=None)]
        out = resolve_refs(refs, env={name: "real-value-that-must-not-leak"})
        assert out.redacted == 1
        assert out.refs[0].value is None
        assert out.refs[0].redacted_kind == "secret-name"

    def test_case_insensitive_name_match(self):
        refs = [EnvRef(name="openai_api_key", default=None)]
        out = resolve_refs(refs, env={"openai_api_key": "sk_live_xxxxx"})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "secret-name"


class TestResolveRefsTier2ValueRedact:
    """The name passes tier 1, but the VALUE looks secret. Block it anyway."""

    def test_aws_key_in_innocent_named_var(self):
        refs = [EnvRef(name="STARTUP_NOTE", default=None)]
        out = resolve_refs(refs, env={"STARTUP_NOTE": f"here is {AWS_AKIA}"})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "aws_access_key"

    def test_github_token_in_innocent_var(self):
        refs = [EnvRef(name="ANNOUNCEMENT", default=None)]
        out = resolve_refs(refs, env={"ANNOUNCEMENT": GITHUB_PAT})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "github_token"

    def test_postgres_url_with_creds(self):
        refs = [EnvRef(name="DATABASE_URL", default=None)]
        out = resolve_refs(refs, env={"DATABASE_URL": "postgres://user:hunter2@host:5432/db"})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "cred_url"

    def test_redis_url_with_password_only(self):
        refs = [EnvRef(name="REDIS_URL", default=None)]
        out = resolve_refs(refs, env={"REDIS_URL": "redis://:hunter2@host:6379/0"})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "cred_url"

    def test_https_url_without_creds_passes_through(self):
        """A clean URL is not credential-bearing; show it."""
        refs = [EnvRef(name="API_BASE_URL", default=None)]
        out = resolve_refs(refs, env={"API_BASE_URL": "https://api.example.com/v1"})
        assert out.resolved == 1
        assert out.refs[0].value == "https://api.example.com/v1"

    def test_default_value_also_runs_tier2(self):
        """If the source default literal is itself a secret, redact it."""
        refs = [EnvRef(name="STARTUP_NOTE", default=AWS_AKIA)]
        out = resolve_refs(refs, env={})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "aws_access_key"

    def test_stripe_key_in_innocent_var(self):
        refs = [EnvRef(name="ANNOUNCEMENT", default=None)]
        out = resolve_refs(refs, env={"ANNOUNCEMENT": STRIPE_LIVE_KEY})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "stripe_key"


class TestEnvSummary:
    def test_empty_summary_is_falsy(self):
        s = EnvSummary()
        assert s.any() is False
        assert s.short_form() == ""

    def test_short_form_resolved_only(self):
        s = EnvSummary(resolved=2)
        assert s.short_form() == "2 env vars resolved"

    def test_short_form_singular(self):
        s = EnvSummary(resolved=1)
        assert s.short_form() == "1 env var resolved"

    def test_short_form_combined(self):
        s = EnvSummary(resolved=2, redacted=1, unset=1)
        assert "2 env vars resolved" in s.short_form()
        assert "1 env redacted" in s.short_form()
        assert "1 env unset" in s.short_form()


class TestFormatBlock:
    def test_empty_returns_none(self):
        assert format_block(EnvSummary()) is None

    def test_safe_value_rendered(self):
        s = EnvSummary(resolved=1)
        s.refs.append(
            ResolvedRef(
                name="DELETION_GRACE_PERIOD",
                value="3600",
                redacted_kind=None,
                used_default=False,
                is_unset=False,
            )
        )
        out = format_block(s)
        assert out is not None
        assert "**Resolved values at capture time:**" in out
        assert "`DELETION_GRACE_PERIOD` = `3600`" in out

    def test_default_marked(self):
        s = EnvSummary(resolved=1)
        s.refs.append(
            ResolvedRef(
                name="LOG_LEVEL",
                value="info",
                redacted_kind=None,
                used_default=True,
                is_unset=False,
            )
        )
        out = format_block(s)
        assert "`LOG_LEVEL` = `info` (default; env unset)" in out

    def test_redacted_value_rendered(self):
        s = EnvSummary(redacted=1)
        s.refs.append(
            ResolvedRef(
                name="OPENAI_API_KEY",
                value=None,
                redacted_kind="secret-name",
                used_default=False,
                is_unset=False,
            )
        )
        out = format_block(s)
        assert "`OPENAI_API_KEY` = `[REDACTED:secret-name]`" in out

    def test_unset_rendered(self):
        s = EnvSummary(unset=1)
        s.refs.append(
            ResolvedRef(
                name="OPTIONAL_VAR",
                value=None,
                redacted_kind=None,
                used_default=False,
                is_unset=True,
            )
        )
        out = format_block(s)
        assert "`OPTIONAL_VAR` = `<unset>`" in out

    def test_value_truncated_above_200_chars(self):
        long_val = "x" * 500
        s = EnvSummary(resolved=1)
        s.refs.append(ResolvedRef(name="BIG", value=long_val, redacted_kind=None, used_default=False, is_unset=False))
        out = format_block(s)
        # Display capped: 199 chars + ellipsis.
        assert "x" * 500 not in out
        assert "…" in out

    def test_overflow_caps_rendered_list(self):
        s = EnvSummary()
        for i in range(60):
            s.refs.append(
                ResolvedRef(
                    name=f"VAR_{i}",
                    value=str(i),
                    redacted_kind=None,
                    used_default=False,
                    is_unset=False,
                )
            )
            s.resolved += 1
        out = format_block(s)
        assert "*… and 10 more*" in out
        assert "VAR_49" in out
        assert "VAR_50" not in out


class TestResolveFromText:
    """End-to-end detect → resolve in one call."""

    def test_python_safe_var(self):
        src = 'period = os.getenv("DELETION_GRACE_PERIOD", "300")'
        out = resolve_from_text(src, "python", env={"DELETION_GRACE_PERIOD": "3600"})
        assert out.resolved == 1
        assert out.refs[0].value == "3600"

    def test_python_secret_var_blocked_by_name(self):
        src = 'client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])'
        out = resolve_from_text(src, "python", env={"OPENAI_API_KEY": "sk_live_xxxx"})
        assert out.redacted == 1
        assert out.refs[0].redacted_kind == "secret-name"

    def test_no_refs_returns_empty_summary(self):
        out = resolve_from_text("x = 1 + 2", "python", env={})
        assert out.any() is False
        assert format_block(out) is None

    def test_unknown_language_safe_no_op(self):
        src = 'os.getenv("X")'
        out = resolve_from_text(src, "rust", env={"X": "value"})
        assert out.any() is False
