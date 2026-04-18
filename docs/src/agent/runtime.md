# Agent Runtime Management

The agent runtime uses a managed Codex binary with isolated configuration.

## Check Runtime Health

```bash
pretorin agent doctor
```

Validates that the Codex runtime is properly installed and configured.

## Install Codex Binary

```bash
pretorin agent install
```

Downloads the pinned Codex binary to `~/.pretorin/bin/`. The version is pinned by the CLI to ensure compatibility.

## Check Version

```bash
pretorin agent version
```

Shows the pinned Codex version and whether it's currently installed.

## Manage MCP Servers

The agent can connect to additional MCP servers beyond Pretorin. This lets the agent access other tools (filesystem, databases, etc.) during compliance tasks.

### List Configured Servers

```bash
pretorin agent mcp-list
```

### Add a Server

```bash
# stdio transport
pretorin agent mcp-add <name> stdio <command> --arg <arg1> --arg <arg2>

# http transport
pretorin agent mcp-add <name> http <url>
```

Options:

| Option | Description |
|--------|-------------|
| `--arg/-a <arg>` | Additional args for stdio transport (repeatable) |
| `--scope <scope>` | Config scope: `project` (default, `.pretorin-mcp.json`) or `global` (`~/.pretorin/mcp.json`) |

Examples:

```bash
pretorin agent mcp-add github stdio uvx --arg mcp-server-github
pretorin agent mcp-add aws http https://mcp.example.com/aws
pretorin agent mcp-add tools stdio node --arg /path/to/server --scope global
```

### Remove a Server

```bash
pretorin agent mcp-remove <name>
```

## Runtime Architecture

The Codex runtime is fully isolated:

- **Binary location:** `~/.pretorin/bin/`
- **Configuration:** `~/.pretorin/codex/` (`CODEX_HOME`)
- **Version pinning:** The CLI pins a specific Codex version for compatibility
- **MCP injection:** Pretorin MCP server is automatically available to the agent

This isolation ensures the agent runtime never interferes with any user-installed Codex instances.
