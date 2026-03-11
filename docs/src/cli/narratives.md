# Narrative Commands

The `narrative` command group manages implementation narratives for controls. Narratives describe how a specific control is implemented within your system.

## Get Current Narrative

```bash
pretorin narrative get ac-02 fedramp-moderate --system "My System"
```

Returns the current narrative text, status, and AI confidence metadata when present.

## Push a Narrative File

```bash
pretorin narrative push ac-02 fedramp-moderate "My System" narrative-ac02.md
```

Reads a markdown or text file and submits it as the implementation narrative for the specified control.

## Markdown Quality Requirements

Narratives must be auditor-ready markdown:

- **No markdown headings** (`#`, `##`, etc.)
- At least **two rich markdown elements** (fenced code blocks, tables, lists, or links)
- At least **one structural element** (code block, table, or list)
- **No markdown images** (temporarily disabled pending platform image upload support)

These requirements are validated before push.

## Generating Narratives with AI

To generate narratives using the agent runtime:

```bash
pretorin agent run --skill narrative-generation "Generate narrative for AC-02"
```

Or use the MCP server's `pretorin_generate_control_artifacts` tool for read-only drafts through your AI agent.

See [Skills](../agent/skills.md) for more on agent-powered narrative generation.

## No-Hallucination Requirements

Generated narratives must only document observable facts. For missing information, use TODO placeholder blocks:

```text
[[PRETORIN_TODO]]
missing_item: <what is missing>
reason: Not observable from current workspace and connected MCP systems
required_manual_action: <what user must do on platform/integrations>
suggested_evidence_type: <policy_document|configuration|...>
[[/PRETORIN_TODO]]
```
