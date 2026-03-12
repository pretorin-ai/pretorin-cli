# Notes Commands

The `notes` command group manages control implementation notes. Notes are used to track gaps, manual follow-up items, and implementation context for specific controls.

## Create Local Note

```bash
pretorin notes create ac-02 fedramp-moderate \
  -c "Gap: Missing SSO evidence. Manual next step: collect IdP configuration screenshots."
```

Creates a local markdown file at `notes/<framework>/<control>/<slug>.md` with YAML frontmatter. No markdown validation is applied to notes.

Options:
- `--content / -c` — Note content (required)
- `--name / -n` — Custom name (defaults to content summary)

## Push Notes

```bash
pretorin notes push --dry-run
pretorin notes push
```

Batch-pushes all unsynced local notes to the platform. Notes are append-only on the platform. After a successful push, the local file's `platform_synced` frontmatter is set to `true`.

## List Local Notes

```bash
pretorin notes list --local
pretorin notes list --local --framework fedramp-moderate
```

Use the `--local` flag to list local note files instead of platform notes.

## List Platform Notes

```bash
pretorin notes list ac-02 fedramp-moderate --system "My System"
```

## Add a Note (Direct to Platform)

```bash
pretorin notes add ac-02 fedramp-moderate \
  --content "Gap: Missing SSO evidence. Manual next step: collect IdP configuration screenshots."
```

## Gap Note Format

When adding notes for unresolved gaps, use this structured format:

```text
Gap: <short title>
Observed: <what was verifiably found>
Missing: <what could not be verified>
Why missing: <access/system limitation>
Manual next step: <explicit user/platform action>
```

This format ensures consistency across CLI, MCP, and agent workflows when documenting compliance gaps.
