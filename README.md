<p align="center">
  <img src="assets/Logo_White+Orange.png" alt="Pretorin" width="400">
</p>

<p align="center">
  <strong>Compliance tools for developers. Integrate with AI agents or your CI pipeline.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/pretorin/"><img src="https://img.shields.io/pypi/v/pretorin" alt="PyPI version"></a>
  <a href="https://registry.modelcontextprotocol.io/"><img src="https://img.shields.io/badge/MCP_Registry-Listed-green" alt="MCP Registry"></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-green" alt="MCP Compatible"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <a href="https://github.com/pretorin-ai/pretorin-cli/actions"><img src="https://github.com/pretorin-ai/pretorin-cli/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
</p>

---

Pretorin brings compliance into your development workflow. Use the **MCP server** to give AI agents direct access to authoritative control data, not hallucinated requirements. Use the **CLI** to query frameworks, controls, and document requirements from your terminal or CI pipeline. Both connect to the same API with enriched data for NIST 800-53, NIST 800-171, FedRAMP, CMMC, and more.

## Quick Start

Get your API key from [platform.pretorin.com](https://platform.pretorin.com/), then:

```bash
uv tool install pretorin
pretorin login
```

That's it. Now add Pretorin to your AI tool below.

## Add to Your AI Tool

<img src="assets/Rome-bot_Basic-1.png" alt="Rome-bot" width="120" align="right">

### Claude Code

```bash
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

This registers the server for your current project. To make it available across all your projects, add `--scope user`.

**Team setup** - add a `.mcp.json` file to your project root so every team member gets the server automatically:

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

### Claude Desktop

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

### Cursor

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

### Windsurf

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

### Harness CLI

If your harness uses the Codex-compatible config format, add to `~/.codex/config.toml`:

```toml
[mcp_servers.pretorin]
command = "pretorin"
args = ["mcp-serve"]
```

Prefer using Pretorin's neutral wrapper command so you can swap harness backends later:

```bash
# Initialize harness policy defaults (Pretorin provider mode)
pretorin harness init --provider-url https://your-pretorin-instance.example/v1

# Validate local setup
pretorin harness doctor

# Run a compliance task through your configured harness backend
pretorin harness run "Assess AC-2 implementation gaps"
```

## Available Tools

| Tool | Description |
|------|-------------|
| `pretorin_list_frameworks` | List all compliance frameworks with tier and category info |
| `pretorin_get_framework` | Get framework metadata including AI context (purpose, target audience, regulatory context, scope, key concepts) |
| `pretorin_list_control_families` | List control families with AI context (domain summary, risk context, implementation priority) |
| `pretorin_list_controls` | List controls with optional family filter |
| `pretorin_get_control` | Get detailed control info including AI guidance (summary, intent, evidence expectations, implementation considerations, common failures) |
| `pretorin_get_control_references` | Get control statement, guidance, objectives, parameters, and related controls |
| `pretorin_get_document_requirements` | Get explicit and implicit document requirements for a framework |
| `pretorin_get_control_context` | Get rich control context: AI guidance, statement, objectives, and implementation details for a system |
| `pretorin_get_scope` | Get system scope/policy information including excluded controls |
| `pretorin_update_narrative` | Push a narrative text update for a control implementation |

## Resources

| Resource URI | Description |
|--------------|-------------|
| `analysis://schema` | Compliance artifact JSON schema |
| `analysis://guide/{framework_id}` | Framework analysis guide |
| `analysis://control/{control_id}` | Control analysis guidance |

## Example Prompts

Try asking your AI assistant:

- "What compliance frameworks are available for government systems?"
- "What are the Account Management requirements for FedRAMP Moderate?"
- "What documents do I need for NIST 800-171 compliance?"
- "Show me all Audit controls in NIST 800-53"

For comprehensive MCP documentation, see [docs/MCP.md](docs/MCP.md).

## Supported Frameworks

The initial public release includes these Government Core frameworks:

- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2
- FedRAMP (Low, Moderate, High)
- CMMC Level 1, 2, and 3

Additional frameworks are available on the platform. See [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs) for the full list.

## CLI Reference

Pretorin also includes a full CLI for working with compliance data directly in the terminal. For comprehensive documentation with real terminal output examples, see [docs/CLI.md](docs/CLI.md).

### Quick Examples

```bash
# List all frameworks
pretorin frameworks list

# Get framework details
pretorin frameworks get fedramp-moderate

# List control families (IDs are slugs like "access-control", not "ac")
pretorin frameworks families nist-800-53-r5

# List controls filtered by family
pretorin frameworks controls nist-800-53-r5 --family access-control --limit 10

# Get control details (IDs are zero-padded: "ac-01", not "ac-1")
pretorin frameworks control nist-800-53-r5 ac-02

# Get full control details with statement, guidance, and related controls
pretorin frameworks control nist-800-53-r5 ac-02 --references
```

### All Commands

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display current authentication status |
| `pretorin frameworks list` | List all compliance frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks controls <id>` | List controls (`--family`, `--limit`) |
| `pretorin frameworks control <framework> <control>` | Get control details (`--references`) |
| `pretorin frameworks documents <id>` | Get document requirements |
| `pretorin context list` | List available systems and frameworks with progress |
| `pretorin context set` | Set active system/framework context (`--system`, `--framework`) |
| `pretorin context show` | Display current active context |
| `pretorin context clear` | Clear active system/framework context |
| `pretorin review run` | Review code against a control (`--control-id`, `--framework-id`, `--path`) |
| `pretorin review status` | Check implementation status (`--control-id`) |
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |
| `pretorin harness init` | Initialize harness config with Pretorin policy defaults |
| `pretorin harness doctor` | Validate harness/provider/MCP policy setup |
| `pretorin harness run "<task>"` | Run a compliance task through the configured harness backend |
| `pretorin version` | Show CLI version |
| `pretorin update` | Update to latest version |
| `pretorin mcp-serve` | Start the MCP server |

## Installation

### Stable (PyPI)

We recommend using [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io/) for isolated installation:

```bash
uv tool install pretorin
```

```bash
pipx install pretorin
```

Or with pip:

```bash
pip install pretorin
```

### Latest (GitHub)

Install the latest development version directly from GitHub:

```bash
uv tool install git+https://github.com/pretorin-ai/pretorin-cli.git
```

### Updating

```bash
pretorin update
```

## Configuration

Credentials are stored in `~/.pretorin/config.json`.

### Environment Variables

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key (overrides stored config) |
| `PRETORIN_PLATFORM_API_BASE_URL` | Platform REST API URL for framework/system/evidence/narrative endpoints (default: https://platform.pretorin.com/api/v1/public) |
| `PRETORIN_API_BASE_URL` | Backward-compatible alias for `PRETORIN_PLATFORM_API_BASE_URL` |
| `PRETORIN_MODEL_API_BASE_URL` | Model provider URL used by `pretorin harness init` (default: https://platform.pretorin.com/v1) |

## Development

### Setup

```bash
git clone https://github.com/pretorin-ai/pretorin-cli.git
cd pretorin-cli
uv pip install -e ".[dev]"
```

Or with pip:

```bash
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

## MCP Registry

This server is listed on the official [MCP Registry](https://registry.modelcontextprotocol.io/).

<!-- mcp-name: io.github.pretorin-ai/pretorin -->

## License

MIT License - see [LICENSE](LICENSE) for details.
