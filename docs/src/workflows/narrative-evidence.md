# Narrative & Evidence Workflow

This is the core workflow for updating control implementations on the platform. Follow this sequence for any control update.

## Workflow Steps

### 1. Resolve the Target

Identify the `system_id`, `control_id`, and `framework_id` for your update. Set the active context:

```bash
pretorin context set --system "My Application" --framework fedramp-moderate
```

### 2. Read Current State

Before making changes, understand what's already there:

```bash
# Get full control context (requirements + current implementation)
# Via MCP: pretorin_get_control_context

# Get current narrative
pretorin narrative get ac-02 fedramp-moderate

# Search existing evidence
pretorin evidence search --control-id ac-02 --framework-id fedramp-moderate

# List existing notes
pretorin notes list ac-02 fedramp-moderate
```

### 3. Collect Observable Facts

Search your codebase and connected systems for evidence. Only document what is directly observable — never assume or fabricate implementation details.

### 4. Draft Updates

Prepare three types of updates:

**Narrative** — How the control is implemented. Include TODO placeholders for unknowns:

```text
[[PRETORIN_TODO]]
missing_item: SSO configuration details
reason: Not observable from current workspace and connected MCP systems
required_manual_action: Export IdP SAML configuration
suggested_evidence_type: configuration
[[/PRETORIN_TODO]]
```

**Evidence** — Specific artifacts demonstrating implementation (config files, code, policies).

**Gap Notes** — Unresolved items requiring manual follow-up:

```text
Gap: Missing MFA enforcement evidence
Observed: TOTP library imported in auth module
Missing: MFA policy enforcement configuration
Why missing: IdP admin console not accessible via codebase
Manual next step: Screenshot MFA policy from Azure AD admin portal
```

### 5. Push Updates

```bash
# Push narrative
pretorin narrative push ac-02 fedramp-moderate "My Application" narrative-ac02.md

# Upsert evidence (finds or creates, then links)
pretorin evidence upsert ac-02 fedramp-moderate \
  --name "RBAC Configuration" \
  --description "Role mapping in IdP" \
  --type configuration

# Add gap notes
pretorin notes add ac-02 fedramp-moderate \
  --content "Gap: Missing MFA evidence..."
```

## Read-Only Draft Workflow

When you want AI drafts before any platform writes:

1. Resolve scope (system, control, framework)
2. Read current state (context, narrative, evidence, notes)
3. Generate drafts via `pretorin agent run --skill narrative-generation` or the MCP `pretorin_generate_control_artifacts` tool
4. Review the draft — clearly separate candidate narrative, evidence gaps, and manual follow-up actions
5. Only push to the platform after explicit approval

## Markdown Quality Rules

All narratives and evidence must pass markdown quality validation:

### Narratives
- No markdown headings (`#`, `##`, etc.)
- At least 2 rich markdown elements (code blocks, tables, lists, links)
- At least 1 structural element (code block, table, or list)
- No markdown images

### Evidence
- No markdown headings
- At least 1 rich markdown element
- No markdown images

## Evidence Deduplication

`pretorin evidence upsert` and the MCP `pretorin_create_evidence` tool use find-or-create logic by default (`dedupe: true`):

1. Search for an exact match on (name + description + type + control + framework) within the active system scope
2. If found, reuse the existing evidence item
3. If not found, create a new one
4. Ensure the evidence is linked to the specified control

The response indicates whether the evidence was `created` (new) or reused, along with the `match_basis`.
