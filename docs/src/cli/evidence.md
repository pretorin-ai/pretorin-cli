# Evidence Commands

The `evidence` command group manages local evidence files and syncs them to the Pretorin platform.

## Create Local Evidence

```bash
pretorin evidence create ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role-based access control in Azure AD" \
  --type configuration
```

Creates a markdown file under `evidence/<framework>/<control>/` with YAML frontmatter containing metadata (control ID, framework, name, type, status).

`--type / -t` is **required** — the CLI no longer defaults to `policy_document`. See [Evidence Types](#evidence-types) below for the 13 canonical values.

## List Local Evidence

```bash
# List all local evidence
pretorin evidence list

# Filter by framework
pretorin evidence list --framework fedramp-moderate
```

## Push Evidence to Platform

```bash
pretorin evidence push
```

Pushes local evidence files to the platform using find-or-create upsert logic. Exact matches are reused and reported separately.

Requires an active single scope from `pretorin context set`, unless both `--system` and `--framework` are provided explicitly.

## Search Platform Evidence

```bash
# Search by control
pretorin evidence search --control-id ac-02 --framework-id fedramp-moderate

# Search by system
pretorin evidence search --system "My Application" --framework-id fedramp-moderate --limit 100
```

## Upload Evidence File

Upload a file directly as evidence:

```bash
pretorin evidence upload screenshot.png ac-02 fedramp-moderate \
  --name "MFA Screenshot" --type screenshot

pretorin evidence upload config.yaml ac-06 fedramp-moderate \
  --name "Auth Config" --type configuration --description "IdP auth config"
```

Creates an evidence record with the uploaded file and links it to the specified control. The file's SHA-256 checksum is computed locally and verified server-side for integrity.

| Option | Description |
|--------|-------------|
| `--name` / `-n` | Evidence name (required) |
| `--type` / `-t` | Evidence type (default: `other`) |
| `--description` / `-d` | Evidence description |
| `--system` / `-s` | System name or ID (uses active context if omitted) |

## Upsert Evidence

Find-or-create evidence and link it to a control:

```bash
pretorin evidence upsert ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role mapping in IdP" \
  --type configuration
```

This searches for an exact match on (name + description + type + control + framework) within the active system scope. If found, it reuses the existing item; otherwise, it creates a new one. It then ensures the evidence is linked to the specified control.

### Code Context Options

When upserting evidence, you can attach source code context:

| Option | Description |
|--------|-------------|
| `--code-file` | Path to source file |
| `--code-lines` | Line range (e.g., `10-25`) |
| `--code-repo` | Git repository URL |
| `--code-commit` | Git commit hash |

If `--code-repo` or `--code-commit` are not provided, the CLI auto-populates them from the attested source verification snapshot when available.

### Capturing Source and Log Content (mandatory when `--code-file` / `--log-file` is set)

In 0.17.0+, passing `--code-file` or `--log-file` to `evidence upsert` or `evidence create` always reads the file, redacts API keys and password assignments, and embeds the result as a fenced code block in the pushed `description`. There is no path-only mode. Each captured description ends with an italic provenance footer (file path, line range, commit, capture timestamp) so auditors always see where the snippet came from.

```bash
pretorin evidence upsert ac-02 fedramp-moderate \
  --name "MFA verification function" \
  --type code_snippet \
  --description "TOTP-based MFA verification used by the login flow." \
  --code-file app/auth.py \
  --code-lines 12-14 \
  --code-commit a1b2c3d
```

Pushed description (rendered):

````markdown
TOTP-based MFA verification used by the login flow.

```python
def verify_mfa(user, code):
    totp = pyotp.TOTP(user.mfa_secret)
    return totp.verify(code)
```

---
*Captured from `app/auth.py` lines 12-14 · commit `a1b2c3d` · 2026-04-27T18:32:11Z · 1 secret redacted*
````

Log capture is symmetric:

```bash
pretorin evidence upsert au-02 fedramp-moderate \
  --name "Authentication audit trail sample" \
  --type log_file \
  --description "Excerpt from auth service production logs." \
  --log-file /var/log/pretorin/auth.log \
  --log-tail 50
```

| Option | Description |
|--------|-------------|
| `--log-file` | Path to a log file (companion to `--code-file`). |
| `--log-tail N` | Capture the last N lines of `--log-file`. |
| `--log-since RFC3339` | Capture `--log-file` lines on or after the given timestamp. |
| `--redact-pii / --no-redact-pii` | Reserved flag; PII redaction is no longer part of the active scope. Pass-through for back-compat. |
| `--no-redact` | Disable secret redaction. Requires interactive confirmation. Refused in non-TTY (CI) environments. |
| `--no-resolve-env` | Disable inline env-var value resolution (see below). On by default. |
| `--no-trace-defs` | Disable cross-file definition tracing (see below). On by default. |

The redactor scope is intentionally narrow:

- **API keys:** AWS access / secret keys, GitHub tokens, Slack tokens, Stripe keys (live + test), Google API keys, JWTs, PEM private key blocks.
- **Credential URLs:** `postgres://user:pass@host`, `redis://:pass@host`, `https://user:pass@host`, and similar `proto://userinfo@authority` patterns.
- **Passwords:** assignments matching `password`, `passwd`, `pwd`, `secret`, `api[_-]?key`, `access[_-]?token`, or `auth[_-]?token` followed by `:` or `=` and a quoted value ≥ 4 chars.

Vendor plugins (detect-secrets) and entropy heuristics were removed because they false-positived on every multi-character YAML / Python / Helm identifier and made captured snippets unreadable.

> **Hard rule:** every evidence record that references a code/log/config file carries embedded captured content. The same rule is enforced at the workflow boundary, so MCP tools, agent tools, and campaign apply paths cannot create an evidence record with `code_file_path` set but no markdown snippet attached.

### Inline env-var value resolution (0.17.0+)

When `--code-file` capture detects env-var references in the snippet, the CLI resolves them against the current process env and renders a **Resolved values at capture time** block under the snippet. Auditors see what the code actually evaluates to, not just the symbolic reference.

```bash
DELETION_GRACE_PERIOD=3600 OPENAI_API_KEY=sk_live_xxxx \
pretorin evidence create ac-02 fedramp-moderate \
  --type configuration \
  --description "Deletion grace period and OpenAI client config." \
  --code-file app/config.py
```

Pushed description (rendered):

````markdown
Deletion grace period and OpenAI client config.

```python
GRACE = os.getenv("DELETION_GRACE_PERIOD", "300")
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
LEVEL = os.getenv("LOG_LEVEL", "info")
```

**Resolved values at capture time:**
- `DELETION_GRACE_PERIOD` = `3600`
- `OPENAI_API_KEY` = `[REDACTED:secret-name]`
- `LOG_LEVEL` = `info` (default; env unset)

---
*Captured from `app/config.py` · 2026-04-28T18:00:00Z · 1 env redacted · 2 env vars resolved*
````

**Two-tier safety:**

1. **Name denylist (tier 1).** Names containing a secret-shaped substring — case-insensitive: `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, `PASSWD`, `PWD`, `CREDENTIAL`, `PRIVATE`, `AUTH`, `SESSION`, `COOKIE`, `SALT`, `SIGNATURE`, `CERT`, `BEARER` — render as `[REDACTED:secret-name]`. The name itself stays visible so the auditor knows what was referenced; only the value is hidden.
2. **Value redact (tier 2).** Even when the name passes tier 1, the resolved value is run through the same secret-redactor as the snippet. AWS / GitHub / Stripe / JWT / PEM / password assignments / `proto://user:pass@host` URLs all hide the value. Tier 2 runs **independently** of `--no-redact` so a confirmed snippet override never leaks credentials out of resolved env values.

**Detection languages:**

- **Python:** `os.getenv("X")`, `os.getenv("X", "default")`, `os.environ["X"]`, `os.environ.get("X")`, `os.environ.get("X", "default")`.
- **JavaScript / TypeScript:** `process.env.X`, `process.env["X"]`.
- **Shell-family** (bash, fish, **YAML**, **Dockerfile**): `$VAR`, `${VAR}`, `${VAR:-default}`, `${VAR-default}`. Kubernetes manifest interpolation `$(VAR)` is also detected in YAML. YAML detection covers the common case of CI workflows / docker-compose / k8s manifests embedding shell-style interpolation in `run:` / `command:` / `args:` blocks. Dockerfile covers `ARG` / `ENV` / `RUN` interpolation.
- **GitHub Actions template syntax** `${{ ... }}` is **not** an env-var reference — it's resolved by the GitHub runner against its secrets vault, which the local CLI can't access. Correctly skipped.
- **JSON-Schema YAML** (`$ref`, `$schema`) does **not** false-match: the bare `$var` form and `$(var)` form both require an uppercase first character, matching the conventional env-var naming rule. Use `${var}` (with braces) when you need a lowercase env var.

Other languages produce no resolved-values block (silent no-op — no detection, no false positives).

**Inline definitions take priority over the agent's process env.** When the snippet defines a variable in the same file (a YAML `env:` mapping, a Dockerfile `ARG`/`ENV`, a k8s `- name: X / value: Y` pair, or a shell `export X=Y`), that inline value is what the resolved block displays — not whatever happens to be set in the operator's shell. The snippet *itself* is the source of truth for what production evaluates to; the agent's env is incidental.

Resolution priority (highest to lowest):
1. **Inline definition** in the same snippet (e.g. `SHANNON_BUDGET_USD: "200"` in a YAML `env:` block).
2. **Process env** at capture time.
3. **Source default** literal (`os.getenv("X", "default")` second arg, Python only).
4. `<unset>` if none of the above produced a value.

Tier-1 (name denylist) and tier-2 (value redact) gates always run on whichever value wins, so an inline-defined credential URL in `DATABASE_URL: postgres://user:pass@host` is still `[REDACTED:cred_url]`.

**Source defaults**: when an env var is unset and the source supplies a default literal (e.g. `os.getenv("LOG_LEVEL", "info")`), the resolved block shows the default with `(default; env unset)` so the auditor can distinguish a runtime value from a fallback.

**`--no-resolve-env`** disables resolution entirely for the capture. Use this when the auditor only needs the symbolic source code, or when running on a machine whose env is not representative of production.

### Cross-file definition tracing (0.17.0+)

When the captured Python snippet references a module-level constant defined in another file (a typical compliance pattern: `from app.config import DELETION_GRACE_PERIOD_DAYS`), the CLI traces the symbol back to the definition file and embeds the relevant lines as a second fenced code block under the original snippet.

```bash
pretorin evidence create dch-10 soc2 \
  --type code_snippet \
  --description "Account deletion grace period." \
  --code-file apps/auth/app/routers/privacy.py \
  --code-lines 10-20
```

Pushed description (rendered):

````markdown
Account deletion grace period.

```python
user.deletion_scheduled_at = now + timedelta(days=DELETION_GRACE_PERIOD_DAYS)
```

```python
# apps/auth/app/config.py:18
DELETION_GRACE_PERIOD_DAYS = 30
```

| Variable | Value | Source |
|---|---|---|
| `DELETION_GRACE_PERIOD_DAYS` | `30` | `apps/auth/app/config.py:18` |

---
*Captured from `apps/auth/app/routers/privacy.py` lines 10-20 · ... · 1 definition traced*
````

**Detection** uses Python's AST so string literals (e.g. the env-var name inside `os.getenv("DELETION_GRACE_PERIOD")`) don't false-match as code references — only real `Name` and `Attribute` nodes count. Imports caught by `ast.ImportFrom` carry a precise import-path hint; bare UPPERCASE references (3+ chars) without an explicit import are also caught.

**Lookup** prefers AST-resolved import paths (`from app.config import X` → `app/config.py`), falls back to `git grep -lE "^[ \t]*X[ \t]*[:=]"` across the repo, and ranks results so files named `config.py` / `settings.py` / `constants.py` win over generic matches. The search root is the git repo containing `--code-file` (or its parent dir if no git root is found). Tests are deprioritized.

**Safety**: each definition slice runs through the same redactor as the original snippet, so a `STRIPE_KEY = "sk_live_..."` constant gets `[REDACTED:stripe_key]` even though the resolution found the right line.

**Bounds**: 5000 files / 1MB per file / 30 seconds wall-time. Anything beyond that is reported as `<not found>` in the table.

**Unified variable table**: every captured description ends with one markdown table merging all detected references — env vars and cross-file constants together. Source column distinguishes:

- `inline` — defined in the captured file itself (YAML `env:` mapping, Dockerfile `ARG`, k8s `- name:/value:` pair, shell `export`)
- `env` — read from the calling process's `os.environ`
- `default` — Python `os.getenv("X", "default")` second-arg fallback
- `<file>:<line>` — cross-file definition traced
- `—` — value is unset and no fallback applies, OR symbol's definition wasn't found anywhere

**`--no-trace-defs`** disables tracing per-capture. Use it when capturing files outside any git repo, or when scan time matters and you only need the original snippet.

**Out of scope** (for both env resolution and cross-file tracing): recursive resolution (`X = int(os.getenv("Y"))` doesn't also resolve Y); class-attribute / pydantic-settings field lookups; the campaign-apply path (the agent runtime's filesystem isn't the user's local repo); cross-repo references.

**Out of scope:** `.env` autoload (resolution reads the live process env only); resolution on the campaign-apply path (the agent runtime's env is not the user's local env, so it stays untouched); resolution in `--log-file` capture (logs are runtime output already, not symbolic references).

## Link Evidence to a Control

Link an existing platform evidence item to a control:

```bash
pretorin evidence link ev-abc123 ac-02
pretorin evidence link ev-abc123 ac-02 --framework-id fedramp-moderate --system "My System"
```

Options:
- `--framework-id / -f` — Framework ID (uses active context if omitted)
- `--system / -s` — System name or ID (uses active context if omitted)

## Delete Evidence

```bash
# Delete with confirmation prompt
pretorin evidence delete ev-abc123

# Skip confirmation (for automation)
pretorin evidence delete ev-abc123 --yes

# Explicit system scope
pretorin evidence delete ev-abc123 --system "My Application" --framework-id fedramp-moderate --yes
```

Permanently deletes an evidence item from the platform. This is system-scoped and requires `WRITE` access. Associated evidence embeddings are removed as part of the delete lifecycle.

| Option | Description |
|--------|-------------|
| `--system` / `-s` | System name or ID (uses active context if omitted) |
| `--framework-id` / `-f` | Framework ID (uses active context if omitted) |
| `--yes` / `-y` | Skip confirmation prompt |

## Evidence Types

Valid evidence types:

| Type | Description |
|------|-------------|
| `policy_document` | Policy or procedure document |
| `screenshot` | Screenshot evidence |
| `screen_recording` | Screen recording |
| `log_file` | Log file extract |
| `configuration` | Configuration file or setting |
| `test_result` | Test output or report |
| `certificate` | Certificate or attestation document |
| `attestation` | Signed attestation |
| `code_snippet` | Code excerpt |
| `repository_link` | Link to source repository |
| `scan_result` | Security scan output |
| `interview_notes` | Interview or assessment notes |
| `other` | Other evidence type |

### AI-Drift Normalization

Non-CLI write paths (MCP handlers, agent tools, `upsert_evidence` workflow, campaign apply) run a client-side normalizer before submitting evidence to the platform. It maps known AI-drift aliases to canonical types (e.g. `audit_log` → `log_file`, plural `test_results` → `test_result`, `screenshoot` → `screenshot`) and uses `difflib` fuzzy matching for novel typos before falling back to `other`. The CLI itself does **not** run the normalizer; users get a hard error listing all 13 canonical types and can self-correct.

## Markdown Quality Requirements

Evidence descriptions must be auditor-ready markdown:

- **No markdown headings** (`#`, `##`, etc.)
- At least **one rich markdown element** (fenced code block, table, list, or link)
- **No markdown images** (temporarily disabled pending platform image upload support)

These requirements are validated before push/upsert operations.
