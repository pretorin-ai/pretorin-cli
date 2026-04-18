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
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-yellow.svg" alt="License: Apache-2.0"></a>
  <a href="https://github.com/pretorin-ai/pretorin-cli/actions"><img src="https://github.com/pretorin-ai/pretorin-cli/actions/workflows/test.yml/badge.svg" alt="Tests"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+"></a>
</p>

---

> **Beta** — Pretorin is currently in closed beta. Framework/control browsing works for authenticated users. Platform write features (evidence, narratives, monitoring) require a beta code. [Sign up for early access](https://pretorin.com/early-access/).

Pretorin CLI gives developers and AI agents direct access to compliance data, implementation context, and evidence workflows.

The CLI and MCP tooling in this repository are open source. Access to Pretorin-hosted platform services, APIs, and account-scoped data is authenticated and governed separately by the applicable platform terms.

`mcp-name: io.github.pretorin-ai/pretorin`

## Two Usage Modes

1. Pretorin-hosted model mode: run `pretorin agent run` and route model calls through Pretorin `/v1` endpoints.
2. Bring-your-own-agent mode: run `pretorin mcp-serve` and connect the MCP server to your existing AI tool (Claude Code, Codex CLI, Cursor, etc.).

## Quick Start

```bash
uv tool install pretorin
pretorin login
pretorin skill install
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
pretorin config set model_api_base_url https://platform.pretorin.com/api/v1/public/model
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

<img src="assets/Rome-bot_Basic-1.png" alt="Rome-bot" width="120" align="right">

### Install the Skill

The Pretorin skill teaches your AI agent how to use MCP tools effectively for compliance workflows. Install it for Claude Code and/or Codex CLI:

```bash
pretorin skill install                # both agents
pretorin skill install --agent claude # claude only
pretorin skill install --agent codex  # codex only
pretorin skill status                 # check what's installed
```

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

If you installed Pretorin with `uv tool install` or `pipx`, prefer pinning the absolute path from `command -v pretorin` to avoid PATH drift between shells and GUI apps.

For Claude Desktop, Cursor, and Windsurf setup, see [docs/MCP.md](docs/MCP.md).

## Core Commands

Platform-backed review and update workflows are single-scope: set one active `system + framework` first with `pretorin context set`, then run evidence, note, monitoring, narrative, or MCP-assisted compliance commands inside that scope. Multi-framework work must be split into separate runs. Evidence, narratives, and notes all support a local-first workflow: create locally, list, then push to the platform.

| Command | Purpose |
|---------|---------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Show current authenticated user |
| `pretorin frameworks list` | List available frameworks |
| `pretorin frameworks control <framework> <control>` | Get control details and guidance |
| `pretorin context set` | Set active system/framework context |
| `pretorin context show` | Inspect and validate the active context |
| `pretorin context clear` | Clear the active context |
| `pretorin control status` | Show control implementation status |
| `pretorin control context` | Get full control context for the active scope |
| `pretorin evidence create` | Create local evidence file |
| `pretorin evidence list` | List local evidence files |
| `pretorin evidence push` | Push local evidence to Pretorin |
| `pretorin evidence search` | Search platform evidence |
| `pretorin evidence link` | Link evidence to a control |
| `pretorin evidence upsert <ctrl> <fw>` | Find-or-create evidence and link it |
| `pretorin evidence delete` | Delete an evidence record |
| `pretorin narrative create` | Create local narrative file |
| `pretorin narrative list` | List local narrative files |
| `pretorin narrative push` | Push local narratives to Pretorin |
| `pretorin narrative get <ctrl> <fw>` | Get current control narrative |
| `pretorin narrative push-file <ctrl> <fw> <sys> <file>` | Push a single narrative file |
| `pretorin notes create` | Create local note file |
| `pretorin notes list --local` | List local note files |
| `pretorin notes push` | Push local notes to Pretorin |
| `pretorin notes list <ctrl> <fw>` | List platform control notes |
| `pretorin notes add <ctrl> <fw> --content ...` | Add control note directly |
| `pretorin notes resolve <note_id>` | Resolve (close) a control note |
| `pretorin monitoring push` | Push a monitoring event |
| `pretorin agent run "<task>"` | Run Codex-powered compliance task |
| `pretorin review run --control-id <id> --path <dir>` | Review local code for control coverage |
| `pretorin skill install` | Install Pretorin skill for AI agents |
| `pretorin skill status` | Check skill install status per agent |
| `pretorin mcp-serve` | Start MCP server |

### Campaign Workflows

Campaigns let you run bulk compliance operations across multiple controls, policies, or scope questions in a single coordinated run. Campaigns support an external-agent-first pattern with checkpoint persistence and lease-based concurrency.

| Command | Purpose |
|---------|---------|
| `pretorin campaign controls --mode initial --family AC` | Draft narratives/evidence for a control family |
| `pretorin campaign controls --mode notes-fix --family AC` | Fix controls flagged by platform notes |
| `pretorin campaign controls --mode review-fix --family AC` | Fix controls flagged by family review |
| `pretorin campaign policy --mode answer --all-incomplete` | Answer all incomplete policy questions |
| `pretorin campaign scope --mode answer` | Answer scope questions for a system/framework |
| `pretorin campaign status --checkpoint <path>` | Check campaign progress |

### Vendor Management & Inheritance

Manage vendor entities (CSPs, SaaS, managed services) and track control inheritance through vendor responsibility edges.

| Command | Purpose |
|---------|---------|
| `pretorin vendor list` | List all vendors |
| `pretorin vendor create <name> --type csp` | Create a vendor entity |
| `pretorin vendor get <id>` | Get vendor details |
| `pretorin vendor upload-doc <id> <file>` | Upload vendor evidence document |
| `pretorin vendor list-docs <id>` | List vendor documents |

### Policy & Scope Questionnaires

Stateful questionnaire workflows for organization policies and system scope. Answer questions interactively or in bulk via campaigns.

| Command | Purpose |
|---------|---------|
| `pretorin policy list` | List organization policies |
| `pretorin policy show <policy_id>` | Show policy detail and questions |
| `pretorin policy populate` | Auto-populate policy answers from context |
| `pretorin scope show` | Show scope questionnaire for active context |
| `pretorin scope populate` | Auto-populate scope answers from context |

### STIG & CCI Browsing

Browse STIG benchmarks, rules, and CCIs with full traceability from NIST 800-53 controls down to individual STIG check rules.

| Command | Purpose |
|---------|---------|
| `pretorin stig list` | List STIG benchmarks |
| `pretorin stig show <id>` | Show STIG benchmark detail |
| `pretorin stig rules <id>` | List rules for a benchmark |
| `pretorin stig applicable` | Show applicable STIGs for active system |
| `pretorin stig infer` | AI-infer applicable STIGs from system profile |
| `pretorin cci list` | List CCIs with optional control filter |
| `pretorin cci show <id>` | Show CCI detail with linked SRGs and rules |
| `pretorin cci chain <control_id>` | Full traceability: Control -> CCIs -> STIG rules |

### STIG Scanning

Run STIG compliance scans using available scanner tools (OpenSCAP, InSpec, AWS/Azure Cloud Scanners).

| Command | Purpose |
|---------|---------|
| `pretorin scan doctor` | Check installed scanner tools |
| `pretorin scan manifest` | Show test manifest for active system |
| `pretorin scan run` | Execute STIG compliance scans |
| `pretorin scan results` | View CCI-level test results |

Quick context checks:

```bash
pretorin context show --quiet
pretorin context show --quiet --check
```

`pretorin login` clears the stored active context when you switch API keys or platform endpoints, which helps prevent old localhost or deleted-system scope from leaking into a new environment.

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
| `PRETORIN_MODEL_API_BASE_URL` | Model API base URL used by agent/harness flows (default: `https://platform.pretorin.com/api/v1/public/model`) |
| `OPENAI_API_KEY` | Optional model key override for agent runtime |

## Documentation

Full documentation is built with [mdbook](https://rust-lang.github.io/mdBook/). To view it locally:

```bash
# Install mdbook (if you don't have it)
cargo install mdbook

# Serve the docs and open in your browser
cd docs && mdbook serve --open
```

This starts a local server at `http://localhost:3000` with live-reload.

To build static HTML without serving:

```bash
./scripts/build-docs.sh
# Output is in docs/book/ and includes llms.txt / llms-full.txt
```

### Quick links

- [CLI reference](docs/src/cli/command-reference.md)
- [MCP integration guide](docs/src/mcp/overview.md)
- [Bundled skill guide](pretorin-skill/SKILL.md)
- [Contributing](CONTRIBUTING.md)
- [Trademarks](TRADEMARKS.md)

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

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE).

The Apache-2.0 license applies to the source code in this repository. It does not grant rights to Pretorin trademarks, logos, or branding, and it does not change the separate terms that govern access to Pretorin-hosted platform services and data. See [TRADEMARKS.md](TRADEMARKS.md).
