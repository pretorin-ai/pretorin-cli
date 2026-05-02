# Pretorin Developer & Agent Docs

> **Beta** — Pretorin is currently in closed beta. Framework and control browsing works for authenticated users. Platform write features (evidence, narratives, monitoring) require a beta code. [Sign up for early access](https://pretorin.com/early-access/).

Pretorin gives developers and AI agents direct access to compliance data, implementation context, and evidence workflows. The primary surfaces are the CLI, the MCP server, and skill-driven agent workflows. It supports 30+ compliance frameworks and profiles, including NIST 800-53, NIST 800-171, FedRAMP, and CMMC.

The CLI and MCP tooling in this repository are open source under Apache-2.0. Access to Pretorin-hosted platform services, APIs, and account-scoped data is authenticated and governed separately by the applicable platform terms.

## Start Here

Choose the path that matches how you work:

- **CLI-first** — Use the Pretorin CLI directly for framework browsing, evidence workflows, reviews, scans, and agent execution.
- **AI-agent-first** — Connect `pretorin mcp-serve` to Claude Code, Codex CLI, Cursor, or another MCP-compatible tool.
- **Hosted agent runtime** — Use `pretorin agent run` when you want Pretorin-managed model execution with built-in skills.

Start with [Installation](./getting-started/installation.md), [Authentication](./getting-started/authentication.md), and [Quick Start](./getting-started/quickstart.md) if this is your first time here.

## Core Paths

Pretorin is usually used in one of these modes:

1. **Bring-your-own-agent mode** — Run `pretorin mcp-serve` and connect the MCP server to your existing AI tool (Claude Code, Codex CLI, Cursor, Windsurf, etc.). Your agent gets compliance tools without changing your workflow. Pair with `pretorin skill install` to give your agent explicit guidance for using pretorin (see "Bundled skill" below).

2. **Pretorin-hosted agent mode** — Run `pretorin agent run` to use Pretorin's built-in agent runtime when you don't have your own local agent. Pretorin manages the AI runtime; you supply prompts.

3. **Direct CLI mode** — Use `pretorin` subcommands directly for browsing frameworks, managing context, authoring evidence, updating narratives, and running scans. No agent involved.

**Important architectural detail.** The vast majority of the CLI and the entire MCP server are thin wrappers over the platform API — *no LLM runs in pretorin in those paths*. When you use mode 1 (your own agent via MCP), your local agent does all the reasoning. Pretorin is the tool surface. The only place pretorin runs its own LLM is `pretorin agent run` (mode 2), provided as a fallback for users without a local agent.

### Bundled skill (`pretorin skill install`)

`pretorin skill install` copies a bundled skill into `~/.claude/skills/pretorin/` (or `~/.codex/skills/pretorin/`). The skill is markdown + scripts that tell your agent how to use pretorin's MCP tools effectively — which to call first, how to scope by system + framework, how to handle evidence and narrative writes. Highly recommended when using mode 1.

## What You Can Do

- **Browse compliance frameworks** — Query controls, families, and document requirements from authoritative sources
- **Manage implementation context** — Set an active system and framework, then track progress across controls
- **Create and manage evidence** — Generate local evidence files, push them to the platform, and link them to controls
- **Write implementation narratives** — Draft and push auditor-ready narratives for each control
- **Run AI-powered compliance tasks** — Use the built-in Codex agent with bundled skills (gap-analysis, narrative-generation, evidence-collection, security-review, stig-scan, cci-assessment)
- **Run compliance recipes** — Author or invoke recipe playbooks (markdown + scripts) that the calling agent executes for evidence capture, baseline scanning, and other procedures
- **Review code against controls** — Analyze your codebase for control coverage
- **Track monitoring events** — Record security scans, access reviews, configuration changes, and compliance checks
- **Generate compliance artifacts** — Produce structured JSON artifacts documenting control implementations
- **Browse STIGs and CCIs** — Look up STIG benchmarks, rules, and trace CCIs through the full control hierarchy
- **Manage vendors** — Track third-party vendors, link evidence to vendor assessments, and upload vendor documents
- **Complete policy and scope questionnaires** — Answer org-policy and scope questions through a guided workflow with AI-assisted generation and review

## Recommended Sections

- [Quick Start](./getting-started/quickstart.md) for first commands and setup
- [MCP Integration](./mcp/overview.md) for Claude, Codex, Cursor, and other agent tools
- [Agent Overview](./agent/overview.md) for Pretorin-hosted runtime usage
- [CLI Reference](./cli/command-reference.md) for command-level detail
- [Workflows](./workflows/narrative-evidence.md) for end-to-end compliance tasks
- [Authoring Recipes](./recipes/index.md) for writing or invoking compliance playbooks

## Architecture

Pretorin CLI is three things, with one shared API client at the bottom:

```
┌──────────────────────────────────────────────────────────────────────┐
│                            Developer                                  │
│                                                                       │
│   ┌──────────┐       ┌──────────────────┐      ┌──────────────────┐  │
│   │ Terminal │       │ Local AI Agent   │      │ pretorin agent   │  │
│   │ (direct  │       │ (Claude Code,    │      │ run              │  │
│   │  pretorin│       │  Codex CLI,      │      │ (Pretorin's own  │  │
│   │  cmds)   │       │  Cursor, ...)    │      │  CodexAgent — for│  │
│   │          │       │                  │      │  users w/o local │  │
│   │          │       │ + bundled        │      │  agent)          │  │
│   │          │       │   pretorin       │      │                  │  │
│   │          │       │   skill          │      │                  │  │
│   │          │       │   (optional)     │      │                  │  │
│   └────┬─────┘       └────────┬─────────┘      └────────┬─────────┘  │
│        │                      │                          │            │
│        │                      │ stdio                    │            │
│        │             ┌────────┴─────────┐                │            │
│        │             │  MCP Server      │                │            │
│        │             │  pretorin        │                │            │
│        │             │  mcp-serve       │                │            │
│        │             │                  │                │            │
│        │             │  Tool surface    │                │            │
│        │             │  (no LLM here)   │                │            │
│        │             └────────┬─────────┘                │            │
│        │                      │                          │            │
│        └──────────────┬───────┴──────────┬───────────────┘            │
│                       │                  │                            │
│              ┌────────┴──────────────────┴─────────┐                  │
│              │  Pretorin API Client                │                  │
│              │  (shared — only place that talks    │                  │
│              │   to the platform)                  │                  │
│              └────────────────┬────────────────────┘                  │
└───────────────────────────────┼───────────────────────────────────────┘
                                │
                       ┌────────┴─────────┐
                       │  Pretorin        │
                       │  Platform API    │
                       └──────────────────┘
```

Three things, one client:

1. **Direct CLI** — `pretorin <command>` runs synchronously, talks to the platform via the shared client. No LLM.
2. **MCP server** — `pretorin mcp-serve` exposes the same platform features as MCP tools. The local agent does all the reasoning; pretorin is the tool surface. **No LLM runs in pretorin in this path.**
3. **`pretorin agent run`** — Pretorin's own LLM, used when the user doesn't have a local agent. Calls the same platform-API tools as the MCP server, just over a Python in-process boundary.

The bundled skill (`pretorin skill install`) is content delivered to the local agent's skill directory; it's not a fourth path, it's a way to give path 2 better instructions.

## Links

- [GitHub Repository](https://github.com/pretorin-ai/pretorin-cli)
- [Platform](https://platform.pretorin.com)
- [PyPI Package](https://pypi.org/project/pretorin/)
- [Issue Tracker](https://github.com/pretorin-ai/pretorin-cli/issues)
- [API Documentation](https://platform.pretorin.com/api/docs)
