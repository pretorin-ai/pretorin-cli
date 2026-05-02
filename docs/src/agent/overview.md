# Agent Overview

The `agent` command group runs autonomous compliance tasks using the Codex agent runtime. This is the **Pretorin-hosted model mode** — Pretorin manages the AI runtime and routes model calls through its `/v1` endpoints.

If you already use another AI agent (Claude Code, Cursor, etc.), use the **MCP mode** instead (`pretorin mcp-serve`) and connect Pretorin tools to your existing agent.

## Running a Compliance Task

```bash
# Free-form task
pretorin agent run "Assess AC-02 implementation gaps for my system"

# Use a predefined skill
pretorin agent run --skill gap-analysis "Analyze my system compliance gaps"
```

## Options

| Option | Description |
|--------|-------------|
| `--skill/-s <name>` | Use a predefined skill template |
| `--model/-m <model>` | Model override |
| `--base-url <url>` | Custom model API endpoint |
| `--working-dir/-w <path>` | Working directory for code analysis |
| `--no-stream` | Disable streaming output |
| `--legacy` | Use legacy OpenAI Agents SDK (deprecated) |
| `--max-turns <n>` | Maximum agent turns (legacy mode only, default 15) |
| `--no-mcp` | Disable external MCP servers (legacy mode only) |

## Hosted Model Setup

Use this setup when you want `pretorin agent run` to call Pretorin-hosted model endpoints.

```bash
# 1. Login with your Pretorin API key
pretorin login

# 2. Optional: override the default model proxy endpoint
#    (default: https://platform.pretorin.com/api/v1/public/model)
pretorin config set model_api_base_url https://your-proxy.example.com/v1

# 3. Validate runtime
pretorin agent doctor
pretorin agent install

# 4. Run a task
pretorin agent run "Assess AC-02 implementation gaps for my system"
```

## Model Key Precedence

The Codex agent resolves API keys in this order:

1. `config.api_key` (from `pretorin login`) — used as bearer key for the platform model proxy
2. `OPENAI_API_KEY` environment variable
3. `config.openai_api_key`

When `--base-url` is explicitly provided (non-platform endpoint), the order changes to prefer `OPENAI_API_KEY` first, then falls back to config keys.

## Custom Model Endpoints

The agent supports any OpenAI-spec LLM endpoint, including:

- Azure OpenAI
- vLLM
- LiteLLM
- Ollama

Configure via `--base-url` flag or the `model_api_base_url` config key.

## How It Works

The agent runtime uses the Codex SDK with a pinned binary in `~/.pretorin/bin/` and an isolated `CODEX_HOME` at `~/.pretorin/codex/`. The agent:

1. Downloads and pins a specific Codex binary version
2. Runs in an isolated `CODEX_HOME` environment (never touches `~/.codex/`)
3. Automatically injects the Pretorin MCP server for compliance tool access
4. Streams events and output in real-time (unless `--no-stream` is passed)

See [Agent Runtime Management](./runtime.md) for the full set of `pretorin agent` lifecycle commands.
