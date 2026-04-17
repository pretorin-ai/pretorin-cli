# Model Context Protocol (MCP) Integration

The Pretorin CLI includes a built-in MCP server that enables AI assistants like Claude, Codex, Cursor, and Windsurf to access compliance framework data directly during conversations.

Scoped compliance execution tools on the MCP server run inside exactly one `system + framework` pair at a time. Set the active scope with `pretorin context set`, or pass both values explicitly. If a request spans multiple framework levels or systems, split it into separate runs.

Before running write-heavy MCP workflows from a shell or GUI wrapper, prefer validating the stored scope with:

```bash
pretorin context show --quiet --check
```

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

The MCP server provides 80+ tools organized by category.

### Framework & Control Reference

| Tool | Description |
|------|-------------|
| `pretorin_list_frameworks` | List all available compliance frameworks |
| `pretorin_get_framework` | Get detailed metadata about a specific framework |
| `pretorin_list_control_families` | List control families for a framework |
| `pretorin_list_controls` | List controls, optionally filtered by family |
| `pretorin_get_control` | Get detailed control information including parameters |
| `pretorin_get_controls_batch` | Get detailed control data for many controls in one request |
| `pretorin_get_control_references` | Get control guidance, objectives, and related controls |
| `pretorin_get_document_requirements` | Get document requirements for a framework |

### Systems

| Tool | Description |
|------|-------------|
| `pretorin_list_systems` | List systems in the current organization |
| `pretorin_get_system` | Get system metadata, attached frameworks, and impact level |
| `pretorin_get_compliance_status` | Get implementation progress for a system |

### Evidence Management

| Tool | Description |
|------|-------------|
| `pretorin_search_evidence` | Search current evidence items |
| `pretorin_create_evidence` | Upsert evidence (find-or-create by default) |
| `pretorin_create_evidence_batch` | Create and link multiple evidence items in one scoped request |
| `pretorin_link_evidence` | Link an existing evidence item to a control |

### Implementation Context

| Tool | Description |
|------|-------------|
| `pretorin_get_control_context` | Get rich control context: AI guidance, statement, objectives, and implementation details |
| `pretorin_get_scope` | Get scope narrative, exclusions, and scope Q&A |
| `pretorin_get_narrative` | Get the current narrative for a control |
| `pretorin_get_control_implementation` | Get implementation status, narrative, evidence count, and notes |
| `pretorin_get_control_notes` | Read notes for a control implementation |
| `pretorin_update_narrative` | Push a narrative text update for a control implementation |
| `pretorin_add_control_note` | Add a control note with manual follow-up guidance |
| `pretorin_resolve_control_note` | Resolve, unresolve, or update an existing control note |
| `pretorin_update_control_status` | Update a control implementation status |
| `pretorin_generate_control_artifacts` | Generate read-only AI narrative and evidence-gap drafts |

### Monitoring

| Tool | Description |
|------|-------------|
| `pretorin_push_monitoring_event` | Create a monitoring event for a system |

### Workflow State & Analytics

| Tool | Description |
|------|-------------|
| `pretorin_get_workflow_state` | Get lifecycle state for a system+framework (scope, policies, controls, evidence) |
| `pretorin_get_analytics_summary` | Lightweight system progress snapshot |
| `pretorin_get_family_analytics` | Per-family breakdown: narrative coverage, evidence, status distribution |
| `pretorin_get_policy_analytics` | Per-policy breakdown: answer completion, review status |

### Family Operations

| Tool | Description |
|------|-------------|
| `pretorin_get_pending_families` | Identify families that need work (pending vs total counts) |
| `pretorin_get_family_bundle` | Get all controls in a family with status, narrative, evidence, notes |
| `pretorin_trigger_family_review` | Trigger AI review of all controls in a family |
| `pretorin_get_family_review_results` | Poll family review results with findings |

### Scope Workflow

| Tool | Description |
|------|-------------|
| `pretorin_get_pending_scope_questions` | Get only unanswered scope questions |
| `pretorin_get_scope_question_detail` | Get guidance, tips, and examples for a scope question |
| `pretorin_answer_scope_question` | Answer one scope question |
| `pretorin_patch_scope_qa` | Batch update scope questionnaire answers |
| `pretorin_trigger_scope_generation` | Trigger AI scope document generation |
| `pretorin_trigger_scope_review` | Trigger AI scope review |
| `pretorin_get_scope_review_results` | Poll scope review results |

### Policy Workflow

| Tool | Description |
|------|-------------|
| `pretorin_list_org_policies` | List organization policies |
| `pretorin_get_org_policy_questionnaire` | Get policy questionnaire state |
| `pretorin_get_pending_policy_questions` | Get only unanswered policy questions |
| `pretorin_get_policy_question_detail` | Get guidance for a policy question |
| `pretorin_answer_policy_question` | Answer one policy question |
| `pretorin_patch_org_policy_qa` | Batch update policy questionnaire answers |
| `pretorin_get_policy_workflow_state` | Per-policy completion and review status |
| `pretorin_trigger_policy_generation` | Trigger AI policy document generation |
| `pretorin_trigger_policy_review` | Trigger AI policy review |
| `pretorin_get_policy_review_results` | Poll policy review results |

### Campaign Operations

| Tool | Description |
|------|-------------|
| `pretorin_prepare_campaign` | Prepare a campaign run with platform state snapshot |
| `pretorin_claim_campaign_items` | Claim items for drafting with TTL-based leases |
| `pretorin_get_campaign_item_context` | Get full item context and drafting instructions |
| `pretorin_submit_campaign_proposal` | Submit a proposal without applying to platform |
| `pretorin_apply_campaign` | Push accepted proposals to the platform |
| `pretorin_get_campaign_status` | Get structured campaign status snapshot |

### Vendor Management

| Tool | Description |
|------|-------------|
| `pretorin_list_vendors` | List all vendor entities |
| `pretorin_create_vendor` | Create a vendor (CSP, SaaS, managed service, internal) |
| `pretorin_get_vendor` | Get vendor details |
| `pretorin_update_vendor` | Update vendor fields |
| `pretorin_delete_vendor` | Delete a vendor entity |
| `pretorin_upload_vendor_document` | Upload vendor evidence documents |
| `pretorin_list_vendor_documents` | List documents linked to a vendor |
| `pretorin_link_evidence_to_vendor` | Link evidence to a vendor with attestation type |

### Inheritance & Responsibility

| Tool | Description |
|------|-------------|
| `pretorin_set_control_responsibility` | Mark control as inherited/shared from a provider |
| `pretorin_get_control_responsibility` | Check if control is inherited and from where |
| `pretorin_remove_control_responsibility` | Convert inherited control to system-specific |
| `pretorin_generate_inheritance_narrative` | AI-generate inheritance narrative from vendor docs |
| `pretorin_get_stale_edges` | Identify controls with stale inheritance |
| `pretorin_sync_stale_edges` | Bulk update inherited controls from source narratives |

### STIG & CCI

| Tool | Description |
|------|-------------|
| `pretorin_list_stigs` | List STIG benchmarks with filters |
| `pretorin_get_stig` | Get STIG benchmark detail |
| `pretorin_list_stig_rules` | List rules with severity/CCI filters |
| `pretorin_get_stig_rule` | Full rule detail: check text, fix text, CCIs |
| `pretorin_list_ccis` | List CCIs with optional control filter |
| `pretorin_get_cci` | CCI detail with linked SRGs and rules |
| `pretorin_get_cci_chain` | Full traceability: Control -> CCIs -> SRGs -> STIG rules |
| `pretorin_get_cci_status` | CCI-level compliance rollup for a system |
| `pretorin_get_stig_applicability` | Which STIGs apply to a system |
| `pretorin_infer_stigs` | AI-infer applicable STIGs from system profile |
| `pretorin_get_test_manifest` | Fetch test manifest for a system |
| `pretorin_submit_test_results` | Upload STIG scan results |

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

#### pretorin_get_controls_batch

Get detailed control data for many controls in a single framework-scoped request.

**Parameters:**
- `framework_id` (required): The framework ID
- `control_ids` (optional): A list of canonical control IDs to retrieve. Omit it to return all controls in the framework.

**Returns:** Full control detail records for the requested controls.

**Example prompt:** "Fetch the full details for AC-02, IA-02, and SC-07 in FedRAMP Moderate"

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
- `system_id` (required): The system ID or name
- `control_id` (required): The control ID (zero-padded for NIST/FedRAMP, e.g., `ac-01`)
- `framework_id` (required): The framework ID

**Returns:** Combined control metadata and implementation details: AI guidance, statement, objectives, scope status, narrative, user context.

**Example prompt:** "What's the full context for AC-02 in my FedRAMP Moderate system?"

---

#### pretorin_get_narrative

Get the current narrative record for a control.

**Parameters:**
- `system_id` (required): The system ID or name
- `control_id` (required): The control ID
- `framework_id` (required): The framework ID

**Returns:** Narrative text, status, and AI confidence metadata when present.

**Example prompt:** "Show me the current narrative for AC-02 in my system"

---

#### pretorin_get_scope

Get system scope and policy information including excluded controls and Q&A responses.

**Parameters:**
- `system_id` (required): The system ID or name
- `framework_id` (required): The framework ID

**Returns:** Scope narrative, list of excluded controls, Q&A responses, and scope status.

**Example prompt:** "Which controls are excluded from scope for my system?"

---

#### pretorin_patch_scope_qa

Apply partial scope questionnaire updates for a system/framework.

**Parameters:**
- `system_id` (required): The system ID or name
- `framework_id` (required): The framework ID
- `updates` (required): A non-empty list of `{question_id, answer}` objects

**Returns:** The updated scope questionnaire state including saved answers.

**Example prompt:** "Set my scope answer for sd-1 to say the system handles CUI in production"

---

#### pretorin_list_org_policies

List organization policies available for questionnaire work.

**Parameters:** None

**Returns:** Policy summaries with IDs, names, template IDs, and questionnaire status.

**Example prompt:** "What organization policies can I work on?"

---

#### pretorin_get_org_policy_questionnaire

Get the canonical questionnaire state for one organization policy.

**Parameters:**
- `policy_id` (required): The organization policy ID

**Returns:** Policy metadata, saved answers, and template/question structure when available.

**Example prompt:** "Show me the questionnaire for policy pol-123"

---

#### pretorin_patch_org_policy_qa

Apply partial organization policy questionnaire updates.

**Parameters:**
- `policy_id` (required): The organization policy ID
- `updates` (required): A non-empty list of `{question_id, answer}` objects

**Returns:** The updated policy questionnaire state.

**Example prompt:** "Update the Access Control policy questionnaire to say MFA is required for all users"

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

#### pretorin_create_evidence_batch

Create and link multiple evidence items within one active system/framework scope.

**Parameters:**
- `system_id` (required): The system ID
- `framework_id` (required): The framework ID
- `items` (required): Array of evidence payloads with `name`, `description`, and `control_id`; may also include `evidence_type` and `relevance_notes`

**Returns:** Batch creation summary with per-item status and evidence IDs.

**Example prompt:** "Create three evidence records for AC-02, AC-03, and IA-02 from these notes"

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

#### pretorin_resolve_control_note

Resolve, unresolve, or update an existing control note. Use this to clear blocking notes so control status can advance.

**Parameters:**
- `system_id` (optional): Defaults to active scope
- `control_id` (required): The control ID
- `note_id` (required): ID of the note to resolve or update
- `framework_id` (optional): Defaults to active scope
- `is_resolved` (optional, default `true`): Set `false` to reopen
- `content` (optional): Updated note content
- `is_pinned` (optional): Whether the note is pinned

**Returns:** The updated note record.

**Example prompt:** "Resolve the blocking note on AC-02 now that SSO evidence has been uploaded"

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

4. If the MCP client can connect but scoped write tools behave strangely, validate the stored CLI context:
   ```bash
   pretorin context show --quiet --check
   ```

   This catches deleted systems, detached frameworks, and other stale local scope before you debug the MCP client itself.

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
