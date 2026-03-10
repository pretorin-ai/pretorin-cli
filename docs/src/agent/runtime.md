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
pretorin agent mcp-add <name> stdio <command> --arg <arg1> --arg <arg2>
```

Example:

```bash
pretorin agent mcp-add filesystem stdio node --arg /path/to/fs-server
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
