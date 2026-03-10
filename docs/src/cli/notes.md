# Notes Commands

The `notes` command group manages control implementation notes. Notes are used to track gaps, manual follow-up items, and implementation context for specific controls.

## List Notes

```bash
pretorin notes list ac-02 fedramp-moderate --system "My System"
```

## Add a Note

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
