# MCP Integration Overview

The Pretorin CLI includes a built-in [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that enables AI assistants to access compliance framework data directly during conversations.

## Why MCP?

The Model Context Protocol allows AI assistants to:

- **Access real-time data** — Query the latest compliance frameworks, controls, and requirements
- **Understand context** — Get detailed control guidance and related controls for better recommendations
- **Reduce hallucination** — Work with authoritative compliance data instead of training knowledge
- **Streamline workflows** — No need to copy-paste control requirements or switch between tools

## How It Works

The MCP server communicates via stdio (standard input/output) using JSON-RPC messages. When you start it with `pretorin mcp-serve`, your AI tool connects and gains access to 94 compliance tools.

```
┌──────────────┐     stdio      ┌──────────────┐     HTTPS     ┌──────────────┐
│   AI Agent   │◄──────────────►│   Pretorin   │◄─────────────►│   Pretorin   │
│ (Claude,     │   JSON-RPC    │   MCP Server  │              │   Platform   │
│  Cursor,     │               │               │              │              │
│  Codex)      │               │               │              │              │
└──────────────┘               └──────────────┘              └──────────────┘
```

## Scope

Scoped compliance execution tools on the MCP server run inside exactly one `system + framework` pair at a time. Set the active scope with `pretorin context set`, or pass both values explicitly. If a request spans multiple frameworks or systems, split it into separate runs.

Before running write-heavy MCP workflows from a shell or GUI wrapper, prefer validating the stored scope with:

```bash
pretorin context show --quiet --check
```

## Tool Categories

The 94 MCP tools are organized into categories:

| Category | Tools | Access |
|----------|-------|--------|
| Task Routing | 1 | Read-only, all users |
| Framework & Control Reference | 8 | Read-only, all users |
| Systems | 5 | Read-only |
| Evidence Management | 7 | Read/Write, requires beta |
| Implementation Context | 11 | Read/Write, requires beta |
| Compliance Updates | 3 | Write, requires beta |
| Workflow State & Analytics | 4 | Read-only |
| Family Operations | 4 | Read/Write, requires beta |
| Scope Workflow | 6 | Read/Write, requires beta |
| Policy Workflow | 7 | Read/Write, requires beta |
| Campaign Operations | 6 | Read/Write, requires beta |
| Vendor Management | 8 | Read/Write, requires beta |
| Inheritance & Responsibility | 6 | Read/Write, requires beta |
| STIG & CCI | 12 | Read-only / Write mix |
| Recipes & Workflows | 6 | Read-only |

See [Tool Reference](./tools.md) for the complete list.

## Quick Setup

```bash
# 1. Install
uv tool install pretorin

# 2. Authenticate
pretorin login

# 3. Add to your AI tool (example: Claude Code)
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

See [Setup Guides](./setup.md) for other AI tools.

## Example Conversations

### Getting Started with a Framework

> **You:** What compliance frameworks are available for government systems?
>
> **Claude:** *Uses pretorin_list_frameworks* — I can see several frameworks available including NIST 800-53 Rev 5, NIST 800-171, and FedRAMP at various impact levels...

### Understanding a Control

> **You:** I need to implement Account Management for our FedRAMP Moderate system. What does it require?
>
> **Claude:** *Uses pretorin_get_control and pretorin_get_control_references* — Account Management requires organizations to manage system accounts including identifying account types, establishing conditions for membership, and specifying authorized users...

### Control Family Overview

> **You:** Give me an overview of the Audit controls in NIST 800-53
>
> **Claude:** *Uses pretorin_list_controls with family filter* — The Audit and Accountability family contains controls for audit events, content, storage, review, and reporting...
