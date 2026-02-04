# Model Context Protocol (MCP) Integration

The Pretorin CLI includes a built-in MCP server that enables AI assistants like Claude to access compliance framework data directly during conversations.

## Why MCP?

The Model Context Protocol allows AI assistants to:

- **Access real-time data** - Query the latest compliance frameworks, controls, and requirements
- **Understand context** - Get detailed control guidance and related controls for better recommendations
- **Reduce hallucination** - Work with authoritative compliance data instead of training knowledge
- **Streamline workflows** - No need to copy-paste control requirements or switch between tools

## Quick Setup

### 1. Install Pretorin CLI

```bash
pip install pretorin
```

### 2. Authenticate

```bash
pretorin login
```

### 3. Configure Your AI Tool

<details open>
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

### 4. Restart Your AI Tool

Restart the application to load the new MCP server.

## Available Tools

The MCP server provides 7 tools for accessing compliance data:

| Tool | Description |
|------|-------------|
| `pretorin_list_frameworks` | List all available compliance frameworks |
| `pretorin_get_framework` | Get detailed metadata about a specific framework |
| `pretorin_list_control_families` | List control families for a framework |
| `pretorin_list_controls` | List controls, optionally filtered by family |
| `pretorin_get_control` | Get detailed control information including parameters |
| `pretorin_get_control_references` | Get control guidance, objectives, and related controls |
| `pretorin_get_document_requirements` | Get document requirements for a framework |

### Tool Reference

#### pretorin_list_frameworks

List all available compliance frameworks.

**Parameters:** None

**Returns:** List of frameworks with ID, title, version, tier, and control counts.

**Example prompt:** "What compliance frameworks are available?"

---

#### pretorin_get_framework

Get detailed metadata about a specific framework.

**Parameters:**
- `framework_id` (required): The framework ID (e.g., `nist-800-53-r5`, `fedramp-moderate`)

**Returns:** Framework details including description, version, OSCAL version, and dates.

**Example prompt:** "Tell me about the FedRAMP Moderate framework"

---

#### pretorin_list_control_families

List all control families for a specific framework.

**Parameters:**
- `framework_id` (required): The framework ID

**Returns:** List of control families with ID, title, class, and control count.

**Example prompt:** "What control families are in NIST 800-53?"

---

#### pretorin_list_controls

List controls for a framework, optionally filtered by family.

**Parameters:**
- `framework_id` (required): The framework ID
- `family_id` (optional): Filter by control family ID. Family IDs are slugs like `access-control` or `audit-and-accountability`, not short codes like `ac` or `au`. CMMC families include a level suffix (e.g., `access-control-level-2`). Use `pretorin frameworks families <id>` to discover valid family IDs.

**Returns:** List of controls with ID, title, and family.

**Example prompt:** "Show me all Access Control controls in NIST 800-53"

---

#### pretorin_get_control

Get detailed information about a specific control.

**Parameters:**
- `framework_id` (required): The framework ID
- `control_id` (required): The control ID. NIST/FedRAMP controls are zero-padded (e.g., `ac-01`, not `ac-1`). CMMC controls use dotted notation (e.g., `AC.L2-3.1.1`). Use `pretorin frameworks controls <id>` to discover valid control IDs.

**Returns:** Control details including parameters, parts, and enhancement count.

**Example prompt:** "Explain the Account Management control from NIST 800-53"

---

#### pretorin_get_control_references

Get reference information for a control including guidance and related controls.

**Parameters:**
- `framework_id` (required): The framework ID
- `control_id` (required): The control ID (zero-padded for NIST/FedRAMP, e.g., `ac-01`)

**Returns:** Statement, guidance, objectives, parameters, and related controls.

**Example prompt:** "What is the guidance for implementing Account Management?"

---

#### pretorin_get_document_requirements

Get document requirements for a framework.

**Parameters:**
- `framework_id` (required): The framework ID

**Returns:** List of explicit and implicit document requirements.

**Example prompt:** "What documents do I need for FedRAMP Moderate?"

## Resources

The MCP server also exposes resources for analysis guidance:

| Resource URI | Description |
|--------------|-------------|
| `analysis://schema` | JSON schema for compliance artifacts |
| `analysis://guide/{framework_id}` | Analysis guide for a specific framework |
| `analysis://control/{control_id}` | Analysis guidance for a specific control |

## Example Conversations

### Getting Started with a Framework

> **You:** What compliance frameworks are available for government systems?
>
> **Claude:** *Uses pretorin_list_frameworks* I can see several frameworks available including NIST 800-53 Rev 5, NIST 800-171, and FedRAMP at various impact levels...

### Understanding a Control

> **You:** I need to implement Account Management for our FedRAMP Moderate system. What does it require?
>
> **Claude:** *Uses pretorin_get_control and pretorin_get_control_references* Account Management requires organizations to manage system accounts including identifying account types, establishing conditions for membership, and specifying authorized users...

### Planning Documentation

> **You:** What policies and documents do I need to write for FedRAMP Moderate?
>
> **Claude:** *Uses pretorin_get_document_requirements* For FedRAMP Moderate, you'll need several key documents including System Security Plan (SSP), Incident Response Plan, Contingency Plan...

### Control Family Overview

> **You:** Give me an overview of the Audit controls in NIST 800-53
>
> **Claude:** *Uses pretorin_list_controls with family filter* The Audit and Accountability family contains controls for audit events, content, storage, review, and reporting...

## Troubleshooting

### "Not authenticated" Error

If you see authentication errors, ensure you've logged in:

```bash
pretorin login
pretorin whoami  # Verify authentication
```

### MCP Server Not Found

1. Verify pretorin is installed and in your PATH:
   ```bash
   which pretorin
   pretorin --version
   ```

2. Try using the full path in your config:
   ```json
   {
     "mcpServers": {
       "pretorin": {
         "command": "/path/to/pretorin",
         "args": ["mcp-serve"]
       }
     }
   }
   ```

3. For pipx installations, find the path:
   ```bash
   pipx list --include-injected
   ```

### Server Crashes or Hangs

Check the MCP server logs:

**macOS/Linux:**
```bash
pretorin mcp-serve 2>&1 | tee mcp-debug.log
```

Ensure your API key is valid:
```bash
pretorin whoami
```

### Framework or Control Not Found

- Verify the framework ID exists: `pretorin frameworks list`
- Verify the control ID exists: `pretorin frameworks controls <framework_id>`

## Using with Other MCP Clients

The Pretorin MCP server follows the standard Model Context Protocol and should work with any MCP-compatible client. The server communicates via stdio (standard input/output).

To test the server manually:

```bash
pretorin mcp-serve
```

The server accepts JSON-RPC messages on stdin and responds on stdout.

## Support

- Documentation: [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs)
- Issues: [github.com/pretorin-ai/pretorin-cli/issues](https://github.com/pretorin-ai/pretorin-cli/issues)
- Platform: [platform.pretorin.com](https://platform.pretorin.com)
