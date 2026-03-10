# Model Context Protocol (MCP) Integration

The Pretorin CLI includes a built-in MCP server that enables AI assistants like Claude, Codex, Cursor, and Windsurf to access compliance framework data directly during conversations.

Scoped compliance execution tools on the MCP server run inside exactly one `system + framework` pair at a time. Set the active scope with `pretorin context set`, or pass both values explicitly. If a request spans multiple framework levels or systems, split it into separate runs.

## Why MCP?

The Model Context Protocol allows AI assistants to:

- **Access real-time data** - Query the latest compliance frameworks, controls, and requirements
- **Understand context** - Get detailed control guidance and related controls for better recommendations
- **Reduce hallucination** - Work with authoritative compliance data instead of training knowledge
- **Streamline workflows** - No need to copy-paste control requirements or switch between tools

## Quick Setup

### 1. Install Pretorin CLI

```bash
uv tool install pretorin
```

Alternative installs:

```bash
pip install pretorin
pipx install pretorin
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

**Quick setup** — run a single command:

```bash
claude mcp add --transport stdio pretorin -- pretorin mcp-serve
```

This registers the server for your current project. To make it available across all your projects, add `--scope user`.

**Team setup** — add a `.mcp.json` file to your project root so every team member gets the server automatically:

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

If you installed Pretorin with `uv tool install` or `pipx`, prefer pinning the absolute path from `command -v pretorin` to avoid PATH drift between shells and GUI apps.

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

The MCP server provides 23 tools for accessing and managing compliance data.
The current tool surface is:

| Tool | Description |
|------|-------------|
| `pretorin_list_frameworks` | List all available compliance frameworks |
| `pretorin_get_framework` | Get detailed metadata about a specific framework |
| `pretorin_list_control_families` | List control families for a framework |
| `pretorin_list_controls` | List controls, optionally filtered by family |
| `pretorin_get_control` | Get detailed control information including parameters |
| `pretorin_get_control_references` | Get control guidance, objectives, and related controls |
| `pretorin_get_document_requirements` | Get document requirements for a framework |
| `pretorin_list_systems` | List systems in the current organization |
| `pretorin_get_system` | Get system metadata, attached frameworks, and impact level |
| `pretorin_get_compliance_status` | Get implementation progress for a system |
| `pretorin_get_control_context` | Get rich control context: AI guidance, statement, objectives, and implementation details |
| `pretorin_get_scope` | Get scope narrative, exclusions, and scope Q&A |
| `pretorin_get_narrative` | Get the current narrative for a control |
| `pretorin_get_control_implementation` | Get implementation status, narrative, evidence count, and notes |
| `pretorin_get_control_notes` | Read notes for a control implementation |
| `pretorin_search_evidence` | Search current evidence items |
| `pretorin_create_evidence` | Upsert evidence (find-or-create by default) |
| `pretorin_link_evidence` | Link an existing evidence item to a control |
| `pretorin_update_narrative` | Push a narrative text update for a control implementation |
| `pretorin_add_control_note` | Add a control note with manual follow-up guidance |
| `pretorin_update_control_status` | Update a control implementation status |
| `pretorin_push_monitoring_event` | Create a monitoring event for a system |
| `pretorin_generate_control_artifacts` | Generate read-only AI narrative and evidence-gap drafts |

`pretorin_generate_control_artifacts` is read-only. Use `pretorin_update_narrative`, `pretorin_create_evidence`, and `pretorin_add_control_note` to persist approved changes.

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

---

#### pretorin_list_systems

List systems in the current organization.

**Parameters:** None

**Returns:** System IDs, names, and summary metadata.

**Example prompt:** "List my systems"

---

#### pretorin_get_system

Get metadata about a specific system.

**Parameters:**
- `system_id` (required): The system ID or name

**Returns:** System metadata including security impact level and attached frameworks.

**Example prompt:** "Show me the details for my production system"

---

#### pretorin_get_compliance_status

Get framework progress and implementation posture for a system.

**Parameters:**
- `system_id` (required): The system ID or name

**Returns:** Framework status summaries and progress metrics.

**Example prompt:** "How far along is my FedRAMP Moderate system?"

---

#### pretorin_get_control_context

Get rich context for a control including AI guidance, control statement, assessment objectives, scope status, and current implementation details.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID (zero-padded for NIST/FedRAMP, e.g., `ac-01`)
- `framework_id` (required): The framework ID

**Returns:** Combined control metadata and implementation details: AI guidance, statement, objectives, scope status, narrative, user context.

**Example prompt:** "What's the full context for AC-02 in my FedRAMP Moderate system?"

---

#### pretorin_get_narrative

Get the current narrative record for a control.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID

**Returns:** Narrative text, status, and AI confidence metadata when present.

**Example prompt:** "Show me the current narrative for AC-02 in my system"

---

#### pretorin_get_scope

Get system scope and policy information including excluded controls and Q&A responses.

**Parameters:**
- `system_id` (required): The system ID

**Returns:** Scope narrative, list of excluded controls, Q&A responses, and scope status.

**Example prompt:** "Which controls are excluded from scope for my system?"

---

#### pretorin_get_control_implementation

Get implementation details for a control in a system.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID

**Returns:** Current status, narrative, evidence count, and implementation notes metadata.

**Example prompt:** "Show me implementation details for AC-02 in my system"

---

#### pretorin_update_narrative

Push a narrative text update for a control implementation on the platform.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID
- `narrative` (required): The narrative text to set
- `is_ai_generated` (optional): Whether the narrative was AI-generated (default: false)

Validation rules:
- No markdown headings (`#`, `##`, etc.)
- At least two rich markdown elements (fenced code blocks, tables, lists, links)
- At least one structural element (`code block`, `table`, or `list`)
- Markdown images are currently disallowed

**Returns:** Confirmation of the update.

**Example prompt:** "Update the narrative for AC-02 with the implementation details I just described"

---

#### pretorin_create_evidence

Upsert evidence on the platform (find-or-create by default). If `dedupe` is true, exact matching evidence in the active system/framework scope is reused; otherwise a new record is created. The tool then ensures control linking inside that same scope.

**Parameters:**
- `system_id` (required): The system ID
- `name` (required): Evidence name
- `description` (required): Evidence description
- `evidence_type` (optional): Evidence type (default: `policy_document`)
- `control_id` (optional): Associated control
- `framework_id` (optional): Associated framework
- `dedupe` (optional): Reuse exact matches before create (default: `true`)

Validation rules:
- No markdown headings (`#`, `##`, etc.)
- At least one rich markdown element (fenced code blocks, tables, lists, or links)
- Markdown images are currently disallowed

**Returns:** Upsert result with:
- `evidence_id`
- `created` (true if new, false if reused)
- `linked` (whether control/system link succeeded)
- `match_basis` (`exact_name_desc_type_control_framework` or `none`)

---

#### pretorin_link_evidence

Link an existing evidence item to a control.

**Parameters:**
- `system_id` (required): The system ID
- `evidence_id` (required): The evidence item ID
- `control_id` (required): The control ID
- `framework_id` (optional): Framework context for the link

**Returns:** Link confirmation for the requested control association.

**Example prompt:** "Link evidence item ev_123 to AC-02"

---

#### pretorin_get_control_notes

Get notes for a control implementation in a system.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (optional): Framework context

**Returns:** Note list with `total` count.

---

#### pretorin_add_control_note

Add a note for unresolved gaps or manual follow-up actions.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID
- `content` (required): Note body

**Returns:** The created note record.

**Example prompt:** "Add a note that SSO evidence must be collected manually"

---

#### pretorin_update_control_status

Update the implementation status for a control.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `status` (required): New status value
- `framework_id` (optional): Framework context

**Returns:** Status update confirmation.

**Example prompt:** "Mark AC-02 as in_progress for my system"

---

#### pretorin_push_monitoring_event

Create a monitoring event for a system.

**Parameters:**
- `system_id` (required): The system ID
- `title` (required): Event title
- `severity` (optional): Severity (`critical`, `high`, `medium`, `low`, `info`)
- `event_type` (optional): Event type (`security_scan`, `configuration_change`, `access_review`, `compliance_check`)
- `control_id` (optional): Associated control ID
- `description` (optional): Detailed event description

**Returns:** The created monitoring event.

**Example prompt:** "Record a quarterly access review event for my production system"

---

#### pretorin_generate_control_artifacts

Generate read-only AI drafts for a control narrative and evidence-gap assessment.

**Parameters:**
- `system_id` (required): The system ID
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID
- `working_directory` (optional): Local workspace path for code-aware drafting
- `model` (optional): Model override

**Returns:** Draft narrative text plus evidence-gap analysis without writing anything to the platform.

**Example prompt:** "Draft narrative and evidence gaps for AC-02 using this repo as context"

## Resources

The MCP server also exposes resources for analysis guidance:

| Resource URI | Description |
|--------------|-------------|
| `analysis://schema` | JSON schema for compliance artifacts |
| `analysis://guide/{framework_id}` | Analysis guide for a specific framework |
| `analysis://control/{framework_id}/{control_id}` | Analysis guidance for a specific control within one framework scope |

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

3. For `uv tool` or `pipx` installations, find the path:
   ```bash
   command -v pretorin
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
