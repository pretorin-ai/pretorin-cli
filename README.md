<p align="center">
  <img src="Logo_White+Orange.png" alt="Pretorin" width="400">
</p>

<p align="center">
  <strong>Making compliance the best part of your day.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/pretorin/"><img src="https://badge.fury.io/py/pretorin.svg" alt="PyPI version"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/pretorin-ai/pretorin-cli/actions"><img src="https://github.com/pretorin-ai/pretorin-cli/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-green" alt="MCP Compatible"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
</p>

---

CLI and MCP server for the Pretorin Compliance Platform API.

Access compliance frameworks, control families, and control details from NIST 800-53, NIST 800-171, FedRAMP, CMMC, and more.

**Documentation**: [https://platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs)

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
pip install git+https://github.com/pretorin-ai/pretorin-cli.git
```

### Updating

Check for updates and upgrade:

```bash
pretorin update
```

## Quick Start

Get your API key from [https://platform.pretorin.com/](https://platform.pretorin.com/), then authenticate:

```bash
pretorin login
```

Verify your authentication:

```bash
pretorin whoami
```

## MCP Integration

<img src="Rome-bot_Basic-1.png" alt="Rome-bot" width="120" align="right">

The Pretorin CLI includes an MCP (Model Context Protocol) server that enables AI assistants to access compliance framework data directly during conversations.

**Why MCP?**

- **Real-time data** — Query the latest compliance frameworks and controls
- **Reduce hallucination** — Work with authoritative compliance data instead of training knowledge
- **Streamline workflows** — No copy-pasting between tools

### Setup

Install and authenticate first:

```bash
pip install pretorin
pretorin login
```

Then add Pretorin to your AI tool of choice:

<details>
<summary><strong>Claude Desktop</strong></summary>

Add to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
**Linux**: `~/.config/Claude/claude_desktop_config.json`

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

</details>

<details>
<summary><strong>Claude Code</strong></summary>

Add a `.mcp.json` file to your project root:

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

Claude Code will detect the file automatically.

</details>

<details>
<summary><strong>Cursor</strong></summary>

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

</details>

<details>
<summary><strong>OpenAI Codex CLI</strong></summary>

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.pretorin]
command = "pretorin"
args = ["mcp-serve"]
```

</details>

<details>
<summary><strong>Windsurf</strong></summary>

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

</details>

### Available Tools

| Tool | Description |
|------|-------------|
| `pretorin_list_frameworks` | List all compliance frameworks |
| `pretorin_get_framework` | Get framework metadata |
| `pretorin_list_control_families` | List control families for a framework |
| `pretorin_list_controls` | List controls (with optional family filter) |
| `pretorin_get_control` | Get detailed control information |
| `pretorin_get_control_references` | Get control guidance and references |
| `pretorin_get_document_requirements` | Get document requirements for a framework |

### Resources

| Resource URI | Description |
|--------------|-------------|
| `analysis://schema` | Compliance artifact JSON schema |
| `analysis://guide/{framework_id}` | Framework analysis guide |
| `analysis://control/{control_id}` | Control analysis guidance |

### Example Prompts

Try asking your AI assistant:

- "What compliance frameworks are available for government systems?"
- "What are the Account Management requirements for FedRAMP Moderate?"
- "What documents do I need for NIST 800-171 compliance?"
- "Show me all Audit controls in NIST 800-53"

For comprehensive MCP documentation, see [docs/MCP.md](docs/MCP.md).

## CLI Reference

### Authentication

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display current authentication status |

### Frameworks

| Command | Description |
|---------|-------------|
| `pretorin frameworks list` | List all compliance frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks controls <id>` | List controls (use `--family` to filter) |
| `pretorin frameworks control <framework> <control>` | Get control details (use `--references` for guidance) |
| `pretorin frameworks documents <id>` | Get document requirements |

### Configuration

| Command | Description |
|---------|-------------|
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |

### Utilities

| Command | Description |
|---------|-------------|
| `pretorin version` | Show CLI version |
| `pretorin update` | Update to latest version |
| `pretorin mcp-serve` | Start the MCP server |

## Configuration

Credentials are stored in `~/.pretorin/config.json`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key (overrides stored config) |
| `PRETORIN_API_BASE_URL` | Custom API URL (default: https://platform.pretorin.com/api/v1) |

## Supported Frameworks

The initial public release includes these Government Core frameworks:

- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2
- FedRAMP (Low, Moderate, High)
- CMMC Level 1, 2, and 3

Additional frameworks are available on the platform. See [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs) for the full list.

## Development

### Setup

```bash
git clone https://github.com/pretorin-ai/pretorin-cli.git
cd pretorin-cli
pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=pretorin --cov-report=term-missing
```

### Docker Testing

```bash
# Run all tests
docker-compose run --rm test

# Run linter
docker-compose run --rm lint

# Run type checker
docker-compose run --rm typecheck

# Or use the convenience script
./scripts/docker-test.sh all
```

### Type Checking

```bash
mypy src/pretorin
```

### Linting

```bash
ruff check src/pretorin
ruff format --check src/pretorin
```

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.
