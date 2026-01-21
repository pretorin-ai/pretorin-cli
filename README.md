# Pretorin CLI

CLI and MCP server for the Pretorin Compliance API.

## Installation

```bash
pip install pretorin
```

Or install from source:

```bash
git clone https://github.com/pretorin/pretorin-cli.git
cd pretorin-cli
pip install -e .
```

## Quick Start

### Authentication

Get your API key from [https://app.pretorin.com/settings/api](https://app.pretorin.com/settings/api), then:

```bash
pretorin login
```

Verify your authentication:

```bash
pretorin whoami
```

### Running Compliance Checks

Check a file for compliance issues:

```bash
pretorin check document.pdf
```

### Managing Reports

List your compliance reports:

```bash
pretorin reports list
```

Get details of a specific report:

```bash
pretorin reports get <report-id>
```

## CLI Commands

### Authentication

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display current user info |

### Configuration

| Command | Description |
|---------|-------------|
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |

### Compliance

| Command | Description |
|---------|-------------|
| `pretorin check <file>` | Run compliance check on a file |
| `pretorin reports list` | List compliance reports |
| `pretorin reports get <id>` | Get report details |
| `pretorin reports create -n <name> <files...>` | Create a new report |

### MCP Server

| Command | Description |
|---------|-------------|
| `pretorin mcp-serve` | Start the MCP server |

## MCP Server

The Pretorin CLI includes an MCP (Model Context Protocol) server for integration with AI assistants like Claude.

### Setup with Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

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

### Available Tools

The MCP server exposes the following tools:

- **pretorin_whoami** - Get current user information
- **pretorin_check_content** - Check text content for compliance issues
- **pretorin_check_file** - Check a file for compliance issues
- **pretorin_list_reports** - List compliance reports
- **pretorin_get_report** - Get details of a specific report

## Configuration

Credentials are stored in `~/.pretorin/config.json`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key (overrides stored config) |
| `PRETORIN_API_BASE_URL` | Custom API URL (for self-hosted) |

## Development

### Setup

```bash
git clone https://github.com/pretorin/pretorin-cli.git
cd pretorin-cli
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Type Checking

```bash
mypy src/pretorin
```

### Linting

```bash
ruff check src/pretorin
```

## License

MIT
