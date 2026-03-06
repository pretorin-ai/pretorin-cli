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

> **Beta** — Pretorin is currently in closed beta. Framework/control browsing works for everyone. Platform write features (evidence, narratives, monitoring) require a beta code. [Sign up for early access](https://pretorin.com/early-access/).

Pretorin CLI gives developers and AI agents direct access to compliance data, implementation context, and evidence workflows.
mcp-name: io.github.pretorin-ai/pretorin

## Two Usage Modes

1. Pretorin-hosted model mode: run `pretorin agent run` and route model calls through Pretorin `/v1` endpoints.
2. Bring-your-own-agent mode: run `pretorin mcp-serve` and connect the MCP server to your existing AI tool (Claude Code, Codex CLI, Cursor, etc.).

## Quick Start

```bash
uv tool install pretorin
pretorin login
```

Run the walkthrough:

```bash
bash scripts/demo-walkthrough.sh
```

## Hosted Model Workflow (Recommended)

Use this flow when you want `pretorin agent run` to go through Pretorin-hosted model endpoints.

1. Authenticate with your Pretorin API key:

```bash
pretorin login
```

2. Optional: point model traffic to a custom/self-hosted Pretorin endpoint:

```bash
pretorin config set model_api_base_url https://platform.pretorin.com/v1
```

3. Verify runtime setup:

```bash
pretorin agent doctor
pretorin agent install
```

4. Run an agent task:

```bash
pretorin agent run "Assess AC-2 implementation gaps for my system"
```

Key behavior:
- Preferred setup is `pretorin login` with no shell-level `OPENAI_API_KEY` override.
- Model key precedence is: `OPENAI_API_KEY` -> `config.api_key` -> `config.openai_api_key`.
- If `OPENAI_API_KEY` is set in your shell, it overrides stored login credentials.

## Add to Your AI Tool

Use this flow when you already have an AI agent/tool and want Pretorin as an MCP capability provider.

### 1. Claude Code

```bash
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

Team setup via `.mcp.json`:

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

### 2. Codex CLI

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.pretorin]
command = "pretorin"
args = ["mcp-serve"]
```

For Claude Desktop, Cursor, and Windsurf setup, see [docs/MCP.md](docs/MCP.md).

## Core Commands

| Command | Purpose |
|---------|---------|
| `pretorin frameworks list` | List available frameworks |
| `pretorin frameworks control <framework> <control>` | Get control details and guidance |
| `pretorin context set` | Set active system/framework context |
| `pretorin evidence create` | Create local evidence file |
| `pretorin evidence push` | Push local evidence to Pretorin |
| `pretorin evidence search` | Search platform evidence |
| `pretorin evidence upsert <ctrl> <fw>` | Find-or-create evidence and link it |
| `pretorin narrative get <ctrl> <fw>` | Get current control narrative |
| `pretorin narrative push <ctrl> <fw> <sys> <file>` | Push a narrative file |
| `pretorin notes list <ctrl> <fw>` | List control notes |
| `pretorin notes add <ctrl> <fw> --content ...` | Add control note |
| `pretorin monitoring push` | Push a monitoring event |
| `pretorin agent run "<task>"` | Run Codex-powered compliance task |
| `pretorin review run --control-id <id> --path <dir>` | Review local code for control coverage |
| `pretorin mcp-serve` | Start MCP server |

## Artifact Authoring Rules

- Narrative and evidence markdown must be human-readable for auditors: no markdown headings, use lists/tables/code blocks/links.
- Markdown image embeds are temporarily disabled until platform-side file upload support is available.

## Configuration

Credentials are stored at `~/.pretorin/config.json`.

| Variable | Description |
|----------|-------------|
| `PRETORIN_API_KEY` | API key for platform access (overrides stored config) |
| `PRETORIN_PLATFORM_API_BASE_URL` | Platform REST API base URL (`/api/v1/public`) |
| `PRETORIN_API_BASE_URL` | Backward-compatible alias for `PRETORIN_PLATFORM_API_BASE_URL` |
| `PRETORIN_MODEL_API_BASE_URL` | Model API base URL used by agent/harness flows (default: `https://platform.pretorin.com/v1`) |
| `OPENAI_API_KEY` | Optional model key override for agent runtime |

## Documentation

- CLI reference: [docs/CLI.md](docs/CLI.md)
- MCP integration guide: [docs/MCP.md](docs/MCP.md)
- Contributing: [CONTRIBUTING.md](CONTRIBUTING.md)

## Development

```bash
git clone https://github.com/pretorin-ai/pretorin-cli.git
cd pretorin-cli
uv pip install -e ".[dev]"
pytest
ruff check src/pretorin
ruff format --check src/pretorin
```

## License

MIT License. See [LICENSE](LICENSE).
