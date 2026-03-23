# MCP Setup Guides

## Prerequisites

Install and authenticate the Pretorin CLI:

```bash
uv tool install pretorin
pretorin login
```

## Claude Code

**Quick setup** — run a single command:

```bash
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

This registers the server for your current project. To make it available across all your projects, add `--scope user`.

**Team setup** — add a `.mcp.json` file to your project root so every team member gets the server automatically:

```json
{
  "mcpServers": {
    "pretorin": {
      "type": "stdio",
      "command": "pretorin",
      "args": ["mcp-serve"]
    }
  }
}
```

Claude Code detects the file automatically.

## Claude Desktop

Add to your Claude Desktop configuration file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pretorin": {
      "command": "pretorin",
      "args": ["mcp-serve"]
    }
  }
}
```

Restart Claude Desktop after saving.

## Cursor

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "pretorin": {
      "command": "pretorin",
      "args": ["mcp-serve"]
    }
  }
}
```

Restart Cursor after saving.

## OpenAI Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.pretorin]
command = "pretorin"
args = ["mcp-serve"]
```

If you installed Pretorin with `uv tool install` or `pipx`, prefer pinning the absolute path from `command -v pretorin` to avoid PATH drift between shells and GUI apps.

## Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "pretorin": {
      "command": "pretorin",
      "args": ["mcp-serve"]
    }
  }
}
```

Restart Windsurf after saving.

## Other MCP Clients

The Pretorin MCP server follows the standard Model Context Protocol and works with any MCP-compatible client. The server communicates via stdio.

To test the server manually:

```bash
pretorin mcp-serve
```

The server accepts JSON-RPC messages on stdin and responds on stdout.

## PATH Considerations

If your AI tool can't find the `pretorin` command, use the full path:

```bash
# Find the full path
command -v pretorin
```

Then use that path in your configuration:

```json
{
  "mcpServers": {
    "pretorin": {
      "command": "/home/user/.local/bin/pretorin",
      "args": ["mcp-serve"]
    }
  }
}
```

This is especially important for `uv tool` and `pipx` installations where the binary may not be on the PATH available to GUI applications.

Before debugging scoped MCP write failures, validate the active CLI scope:

```bash
pretorin context show --quiet --check
```
