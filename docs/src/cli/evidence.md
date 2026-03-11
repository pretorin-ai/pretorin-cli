# Evidence Commands

The `evidence` command group manages local evidence files and syncs them to the Pretorin platform.

## Create Local Evidence

```bash
pretorin evidence create ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role-based access control in Azure AD"
```

Creates a markdown file under `evidence/<framework>/<control>/` with YAML frontmatter containing metadata (control ID, framework, name, type, status).

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

## Upsert Evidence

Find-or-create evidence and link it to a control:

```bash
pretorin evidence upsert ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role mapping in IdP" \
  --type configuration
```

This searches for an exact match on (name + description + type + control + framework) within the active system scope. If found, it reuses the existing item; otherwise, it creates a new one. It then ensures the evidence is linked to the specified control.

## Evidence Types

Valid evidence types:

| Type | Description |
|------|-------------|
| `policy_document` | Policy or procedure document (default) |
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

## Markdown Quality Requirements

Evidence descriptions must be auditor-ready markdown:

- **No markdown headings** (`#`, `##`, etc.)
- At least **one rich markdown element** (fenced code block, table, list, or link)
- **No markdown images** (temporarily disabled pending platform image upload support)

These requirements are validated before push/upsert operations.
