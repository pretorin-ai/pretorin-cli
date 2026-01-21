# Pretorin CLI

CLI and MCP server for the Pretorin Compliance Platform API.

Access compliance frameworks, control families, and control details from NIST 800-53, NIST 800-171, FedRAMP, SOC 2, ISO 27001, and more.

## Installation

### Stable (PyPI)

```bash
pip install pretorin
```

We recommend using [pipx](https://pipx.pypa.io/) for isolated installation:

```bash
pipx install pretorin
```

### Latest (GitHub)

Install the latest development version directly from GitHub:

```bash
pip install git+https://github.com/pretorin/pretorin-cli.git
```

### Updating

Check for updates and upgrade:

```bash
pretorin update
```

## Quick Start

### Authentication

Get your API key from [https://platform.pretorin.com/settings/developer](https://platform.pretorin.com/settings/developer), then:

```bash
pretorin login
```

Verify your authentication:

```bash
pretorin whoami
```

### Browse Frameworks

List all available compliance frameworks:

```bash
pretorin frameworks list
```

Get details about a specific framework:

```bash
pretorin frameworks get nist-800-53-r5
```

### Browse Control Families

List control families for a framework:

```bash
pretorin frameworks families nist-800-53-r5
```

### Browse Controls

List all controls for a framework:

```bash
pretorin frameworks controls nist-800-53-r5
```

Filter by control family:

```bash
pretorin frameworks controls nist-800-53-r5 --family ac
```

Get details of a specific control:

```bash
pretorin frameworks control nist-800-53-r5 ac-1
```

Include guidance and references:

```bash
pretorin frameworks control nist-800-53-r5 ac-1 --references
```

### Document Requirements

Get document requirements for a framework:

```bash
pretorin frameworks documents fedramp-moderate
```

## CLI Commands

### Authentication

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display current authentication status |

### Configuration

| Command | Description |
|---------|-------------|
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |

### Frameworks

| Command | Description |
|---------|-------------|
| `pretorin frameworks list` | List all compliance frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks controls <id>` | List controls |
| `pretorin frameworks control <framework> <control>` | Get control details |
| `pretorin frameworks documents <id>` | Get document requirements |

### Utilities

| Command | Description |
|---------|-------------|
| `pretorin version` | Show CLI version |
| `pretorin update` | Update to latest version |
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

- **pretorin_list_frameworks** - List all compliance frameworks
- **pretorin_get_framework** - Get framework metadata
- **pretorin_list_control_families** - List control families for a framework
- **pretorin_list_controls** - List controls (with optional family filter)
- **pretorin_get_control** - Get detailed control information
- **pretorin_get_control_references** - Get control guidance and references
- **pretorin_get_document_requirements** - Get document requirements for a framework

## Configuration

Credentials are stored in `~/.pretorin/config.json`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key (overrides stored config) |
| `PRETORIN_API_BASE_URL` | Custom API URL (default: https://platform.pretorin.com/api/v1) |

## Supported Frameworks

The API provides access to various compliance frameworks including:

- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2
- FedRAMP (Low, Moderate, High)
- SOC 2
- ISO 27001
- And more...

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

Proprietary - Pretorin, Inc.
