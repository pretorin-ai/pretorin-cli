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

The redactor scope is intentionally narrow:

- **API keys:** AWS access / secret keys, GitHub tokens, Slack tokens, Stripe keys (live + test), Google API keys, JWTs, PEM private key blocks.
- **Passwords:** assignments matching `password`, `passwd`, `pwd`, `secret`, `api[_-]?key`, `access[_-]?token`, or `auth[_-]?token` followed by `:` or `=` and a quoted value ≥ 4 chars.

Vendor plugins (detect-secrets) and entropy heuristics were removed because they false-positived on every multi-character YAML / Python / Helm identifier and made captured snippets unreadable.

> **Hard rule:** every evidence record that references a code/log/config file carries embedded captured content. The same rule is enforced at the workflow boundary, so MCP tools, agent tools, and campaign apply paths cannot create an evidence record with `code_file_path` set but no markdown snippet attached.

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
