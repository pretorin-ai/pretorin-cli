# Pretorin CLI

> **Beta** — Pretorin is currently in closed beta. Framework and control browsing works for authenticated users. Platform write features (evidence, narratives, monitoring) require a beta code. [Sign up for early access](https://pretorin.com/early-access/).

Pretorin CLI gives developers and AI agents direct access to compliance data, implementation context, and evidence workflows. It supports NIST 800-53, NIST 800-171, FedRAMP, and CMMC frameworks with over 700 controls across 8 framework profiles.

The CLI and MCP tooling in this repository are open source under Apache-2.0. Access to Pretorin-hosted platform services, APIs, and account-scoped data is authenticated and governed separately by the applicable platform terms.

## Two Usage Modes

Pretorin works in two modes depending on your setup:

1. **Pretorin-hosted model mode** — Run `pretorin agent run` to route model calls through Pretorin's `/v1` endpoints. Pretorin manages the AI runtime.

2. **Bring-your-own-agent mode** — Run `pretorin mcp-serve` and connect the MCP server to your existing AI tool (Claude Code, Codex CLI, Cursor, Windsurf, etc.). Your agent gets compliance tools without changing your workflow.

## What You Can Do

- **Browse compliance frameworks** — Query controls, families, and document requirements from authoritative sources
- **Manage implementation context** — Set an active system and framework, then track progress across controls
- **Create and manage evidence** — Generate local evidence files, push them to the platform, and link them to controls
- **Write implementation narratives** — Draft and push auditor-ready narratives for each control
- **Run AI-powered compliance tasks** — Use the built-in Codex agent for gap analysis, narrative generation, evidence collection, and security review
- **Review code against controls** — Analyze your codebase for control coverage
- **Track monitoring events** — Record security scans, access reviews, configuration changes, and compliance checks
- **Generate compliance artifacts** — Produce structured JSON artifacts documenting control implementations

## Architecture

```
┌─────────────────────────────────────────────┐
│                 Developer                    │
│                                             │
│   ┌──────────┐        ┌──────────────────┐  │
│   │ CLI      │        │ AI Agent         │  │
│   │ pretorin │        │ (Claude, Codex,  │  │
│   │ commands │        │  Cursor, etc.)   │  │
│   └────┬─────┘        └────────┬─────────┘  │
│        │                       │             │
│        │              ┌────────┴─────────┐   │
│        │              │  MCP Server      │   │
│        │              │  pretorin        │   │
│        │              │  mcp-serve       │   │
│        │              └────────┬─────────┘   │
│        │                       │             │
│        └───────────┬───────────┘             │
│                    │                         │
│           ┌────────┴─────────┐               │
│           │  Pretorin API    │               │
│           │  Client          │               │
│           └────────┬─────────┘               │
└────────────────────┼─────────────────────────┘
                     │
            ┌────────┴─────────┐
            │  Pretorin        │
            │  Platform        │
            └──────────────────┘
```

## Links

- [GitHub Repository](https://github.com/pretorin-ai/pretorin-cli)
- [Platform](https://platform.pretorin.com)
- [PyPI Package](https://pypi.org/project/pretorin/)
- [Issue Tracker](https://github.com/pretorin-ai/pretorin-cli/issues)
- [API Documentation](https://platform.pretorin.com/api/docs)
