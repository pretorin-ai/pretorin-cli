# Quick Start

After [installing](./installation.md) and [authenticating](./authentication.md), here are some common first steps.

## Browse Frameworks

List all available compliance frameworks:

```bash
pretorin frameworks list
```

Get details on a specific control:

```bash
pretorin frameworks control nist-800-53-r5 ac-02
```

## Set Up Context

Set your active system and framework for platform operations:

```bash
# Interactive selection
pretorin context set

# Or explicit
pretorin context set --system "My Application" --framework fedramp-moderate
```

## Create Evidence

Create a local evidence file:

```bash
pretorin evidence create ac-02 fedramp-moderate \
  --description "Role-based access control in Azure AD" \
  --type configuration \
  --name "RBAC Configuration"
```

Push evidence to the platform:

```bash
pretorin evidence push
```

## Run an Agent Task

Use the Codex agent for compliance analysis:

```bash
pretorin agent run "Assess AC-02 implementation gaps for my system"
```

Or use a predefined skill:

```bash
pretorin agent run --skill gap-analysis "Analyze my system compliance gaps"
```

## Connect Your AI Tool

If you use Claude Code, Codex CLI, or another MCP-compatible AI tool:

```bash
# Install the skill (teaches your agent how to use Pretorin tools)
pretorin skill install

# Add the MCP server (Claude Code example)
claude mcp add --transport stdio pretorin -- pretorin mcp-serve

# Then ask your AI agent about compliance
# "What controls are in the Access Control family for FedRAMP Moderate?"
```

Check install status with `pretorin skill status`. See the [MCP Setup Guides](../mcp/setup.md) for other tools.

## Run a Recipe

Recipes are markdown-plus-scripts playbooks that the calling agent invokes through MCP for evidence capture, baseline scanning, and other procedures:

```bash
# List available recipes (built-in + user + project)
pretorin recipe list

# Show one recipe's manifest and prose body
pretorin recipe show inspec-baseline

# Scaffold a new recipe in ~/.pretorin/recipes/<id>/
pretorin recipe new my-first-recipe
```

See [Authoring Recipes](../recipes/index.md) for the full guide.

## Browse STIGs and CCIs

Look up STIG benchmarks, rules, and CCI traceability:

```bash
# List available STIG benchmarks
pretorin stig list

# View STIG benchmark details
pretorin stig show <stig_id>

# Trace a CCI to its parent controls
pretorin cci chain <cci-id>
```

## Run the Demo Walkthrough

An interactive demo script is included in the repository:

```bash
bash tools/demo-walkthrough.sh
```
