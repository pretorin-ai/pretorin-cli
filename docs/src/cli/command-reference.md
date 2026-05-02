# Complete Command Reference

## Global Options

| Option | Description |
|--------|-------------|
| `--json` | JSON output mode for scripting and AI agents |
| `--version`, `-V` | Show version and exit |
| `--help` | Show command help |

## Root Commands

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API (`--api-key/-k`, `--api-url`) |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display authentication status |
| `pretorin version` | Show CLI version |
| `pretorin update [VERSION]` | Update to latest version, or a specific version |
| `pretorin mcp-serve` | Start the MCP server (stdio transport) |

## Framework Commands

| Command | Description |
|---------|-------------|
| `pretorin frameworks list` | List all frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks family <fw> <family>` | Get control family details |
| `pretorin frameworks controls <id> [FAMILY_ID]` | List controls (`--family/-f`, `--limit/-n`) |
| `pretorin frameworks control <fw> <ctrl>` | Get control details (`--brief/-b`) |
| `pretorin frameworks documents <id>` | Get document requirements |
| `pretorin frameworks metadata <id>` | Get per-control framework metadata |
| `pretorin frameworks submit-artifact <file>` | Submit a compliance artifact JSON file |

### Custom Frameworks

Subcommands of `pretorin frameworks` for authoring, validating, and uploading
custom or forked frameworks. See [Custom Frameworks](../frameworks/custom.md)
for the full authoring workflow.

| Command | Description |
|---------|-------------|
| `pretorin frameworks init-custom <framework_id>` | Scaffold a minimal valid `unified.json` (`--title/-t`, `--output/-o`, `--force/-f`) |
| `pretorin frameworks validate-custom <file>` | Validate a `unified.json` artifact against the bundled JSON Schema |
| `pretorin frameworks build-custom <input>` | Normalize a source catalog (unified, OSCAL, or known custom) into uploadable `unified.json` (`--framework-id/-f` required, `--output/-o`, `--force`) |
| `pretorin frameworks upload-custom <file>` | Upload a `unified.json` artifact as a draft revision (`--framework-id/-f`, `--version-label/-v`, `--publish`) |
| `pretorin frameworks fork-framework <source_id> <new_id>` | Create a linked-fork draft from an upstream framework (`--version-label/-v`) |
| `pretorin frameworks rebase-fork <framework_id>` | Create a rebase draft for a fork against the latest upstream revision (`--version-label/-v`) |
| `pretorin frameworks revisions <framework_id>` | List all draft and published revisions for a framework |
| `pretorin frameworks export-oscal <file>` | Regenerate an OSCAL catalog from a `unified.json` artifact (`--output/-o`, `--force`) |

## Context Commands

| Command | Description |
|---------|-------------|
| `pretorin context list` | List systems and frameworks with progress |
| `pretorin context set` | Set active system/framework context (`--system/-s`, `--framework/-f`, `--no-verify`) |
| `pretorin context show` | Display and validate current active context (`--quiet/-q`, `--check`) |
| `pretorin context clear` | Clear active context |
| `pretorin context verify` | Verify active context with source attestation (`--ttl`, `--quiet/-q`) |
| `pretorin context manifest` | Show resolved source manifest and evaluate against detected sources (`--quiet/-q`) |

## Control Commands

| Command | Description |
|---------|-------------|
| `pretorin control status <ctrl> <status>` | Update control implementation status (`--framework-id/-f`, `--system/-s`) |
| `pretorin control context <ctrl>` | Get rich control context with AI guidance (`--framework-id/-f`, `--system/-s`) |

## Evidence Commands

| Command | Description |
|---------|-------------|
| `pretorin evidence create <ctrl> <fw>` | Create a local evidence file (`--name/-n`, `--description/-d`, `--type/-t`) |
| `pretorin evidence list` | List local evidence files (`--framework/-f`) |
| `pretorin evidence push` | Push local evidence to the platform (`--dry-run`) |
| `pretorin evidence search` | Search platform evidence (`--control-id/-c`, `--framework-id/-f`, `--system/-s`, `--limit/-n`) |
| `pretorin evidence upsert <ctrl> <fw>` | Find-or-create evidence and link it (`--name/-n`, `--description/-d`, `--type/-t`, `--system/-s`, `--code-file`, `--code-lines`, `--code-repo`, `--code-commit`) |
| `pretorin evidence upload <file> <ctrl> <fw>` | Upload a file as evidence (`--name/-n`, `--type/-t`, `--description/-d`, `--system/-s`) |
| `pretorin evidence link <evidence_id> <ctrl>` | Link evidence to a control (`--framework-id/-f`, `--system/-s`) |
| `pretorin evidence delete <evidence_id>` | Delete an evidence item (`--system/-s`, `--framework-id/-f`, `--yes/-y`) |

## Narrative Commands

| Command | Description |
|---------|-------------|
| `pretorin narrative create <ctrl> <fw>` | Create a local narrative file (`--content/-c`, `--name/-n`, `--ai-generated`) |
| `pretorin narrative list` | List local narrative files (`--framework/-f`) |
| `pretorin narrative push` | Push local narratives to the platform (`--dry-run`) |
| `pretorin narrative push-file <ctrl> <fw> <sys> <file>` | Push a single narrative file to the platform |
| `pretorin narrative get <ctrl> <fw>` | Get current control narrative (`--system/-s`) |

## Notes Commands

| Command | Description |
|---------|-------------|
| `pretorin notes create <ctrl> <fw>` | Create a local note file (`--content/-c`, `--name/-n`) |
| `pretorin notes list [ctrl] [fw]` | List notes — platform (`--system/-s`) or local (`--local`, `--framework/-f`) |
| `pretorin notes push` | Push local notes to the platform (`--dry-run`) |
| `pretorin notes add <ctrl> <fw>` | Add a note directly on the platform (`--content/-c`, `--system/-s`) |
| `pretorin notes resolve <ctrl> <fw> <note_id>` | Resolve or reopen a control note (`--system/-s`, `--reopen`, `--content/-c`, `--pinned`) |

## Monitoring Commands

| Command | Description |
|---------|-------------|
| `pretorin monitoring push` | Push a monitoring event (`--system/-s`, `--framework/-f`, `--title/-t`, `--event-type`, `--severity`, `--control/-c`, `--description/-d`, `--update-control-status`) |

## Policy Commands

| Command | Description |
|---------|-------------|
| `pretorin policy list` | List org policies available for questionnaire work |
| `pretorin policy show` | Show persisted policy questionnaire state (`--policy`) |
| `pretorin policy populate` | Draft policy questionnaire updates from the current workspace (`--policy`, `--path/-p`, `--apply`) |

## Scope Commands

| Command | Description |
|---------|-------------|
| `pretorin scope show` | Show scope questionnaire state and review findings (`--system/-s`, `--framework-id/-f`) |
| `pretorin scope populate` | Draft scope questionnaire updates from the current workspace (`--system/-s`, `--framework-id/-f`, `--path/-p`, `--apply`) |

## Agent Commands

| Command | Description |
|---------|-------------|
| `pretorin agent run "<task>"` | Run a compliance task (`--skill/-s`, `--model/-m`, `--base-url`, `--working-dir/-w`, `--no-stream`, `--legacy`, `--max-turns`, `--no-mcp`) |
| `pretorin agent doctor` | Validate Codex runtime setup |
| `pretorin agent install` | Download the pinned Codex binary |
| `pretorin agent version` | Show pinned Codex version and install status |
| `pretorin agent skills` | List available agent skills |
| `pretorin agent mcp-list` | List configured MCP servers for the agent |
| `pretorin agent mcp-add <name> <transport> <cmd>` | Add an MCP server configuration (`--arg/-a`, `--scope`) |
| `pretorin agent mcp-remove <name>` | Remove an MCP server configuration |

## Skill Commands

| Command | Description |
|---------|-------------|
| `pretorin skill install` | Install the Pretorin skill for AI coding agents (`--agent/-a`, `--path/-p`, `--force/-f`) |
| `pretorin skill uninstall` | Uninstall the Pretorin skill (`--agent/-a`, `--path/-p`) |
| `pretorin skill status` | Show installation status of the Pretorin skill |
| `pretorin skill list-agents` | List all known agents and their skill directories |

## Review Commands

| Command | Description |
|---------|-------------|
| `pretorin review run` | Review code against a control (`--control-id/-c`, `--framework-id/-f`, `--system/-s`, `--path/-p`, `--local`, `--output-dir/-o`) |
| `pretorin review status` | Check implementation status for a control (`--control-id/-c`, `--framework-id/-f`, `--system/-s`) |

## Config Commands

| Command | Description |
|---------|-------------|
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |

## Campaign Commands

| Command | Description |
|---------|-------------|
| `pretorin campaign controls` | Run bulk control narrative/evidence campaign (`--system`, `--framework-id`, `--mode`, `--family`, `--controls`, `--all-controls`, `--artifacts`, `--review-job`, `--concurrency`, `--max-retries`, `--checkpoint`, `--apply`, `--output`) |
| `pretorin campaign policy` | Run bulk policy questionnaire campaign (`--mode`, `--policies`, `--all-incomplete`, `--system`, `--concurrency`, `--max-retries`, `--checkpoint`, `--apply`, `--output`) |
| `pretorin campaign scope` | Run bulk scope questionnaire campaign (`--system`, `--framework-id`, `--mode`, `--concurrency`, `--max-retries`, `--checkpoint`, `--apply`, `--output`) |
| `pretorin campaign status` | Show campaign progress from a checkpoint file (`--checkpoint`, `--output`) |

### Campaign Modes

| Domain | Mode | Description |
|--------|------|-------------|
| controls | `initial` | Draft new narratives and evidence for controls |
| controls | `notes-fix` | Address platform notes on existing controls |
| controls | `review-fix` | Fix findings from a family review job |
| policy | `answer` | Generate answers for policy questions |
| policy | `review-fix` | Fix findings from a policy review |
| scope | `answer` | Generate answers for scope questions |
| scope | `review-fix` | Fix findings from a scope review |

## Vendor Commands

| Command | Description |
|---------|-------------|
| `pretorin vendor list` | List all vendors in the organization |
| `pretorin vendor create <name>` | Create a vendor (`--type/-t`, `--description/-d`, `--authorization-level/-a`) |
| `pretorin vendor get <vendor_id>` | Get vendor details |
| `pretorin vendor update <vendor_id>` | Update vendor fields (`--name`, `--description/-d`, `--type/-t`, `--authorization-level/-a`) |
| `pretorin vendor delete <vendor_id>` | Delete a vendor (`--force/-f`) |
| `pretorin vendor upload-doc <vendor_id> <file>` | Upload a vendor evidence document (`--name/-n`, `--description/-d`, `--attestation-type`) |
| `pretorin vendor list-docs <vendor_id>` | List documents linked to a vendor |

### Vendor Types

`csp`, `saas`, `managed_service`, `internal`

## STIG Commands

| Command | Description |
|---------|-------------|
| `pretorin stig list` | List STIG benchmarks (`--technology-area/-t`, `--product/-p`, `--limit/-l`) |
| `pretorin stig show <stig_id>` | Show STIG benchmark detail with severity breakdown |
| `pretorin stig rules <stig_id>` | List rules for a benchmark (`--severity/-s`, `--cci`, `--limit/-l`) |
| `pretorin stig applicable` | Show applicable STIGs for the active system (`--system/-s`) |
| `pretorin stig infer` | AI-infer applicable STIGs from system profile (`--system/-s`) |

## CCI Commands

| Command | Description |
|---------|-------------|
| `pretorin cci list` | List CCIs (`--control/-c`, `--status`, `--limit/-l`) |
| `pretorin cci show <cci_id>` | Show CCI detail with linked SRGs and STIG rules (e.g., `CCI-000015`) |
| `pretorin cci chain <control_id>` | Full traceability chain: Control -> CCIs -> SRGs -> STIG rules (`--system/-s`) |

## Recipe Commands

Recipes are markdown + script playbooks the calling AI agent executes. See
[Recipes](../recipes/index.md) for authoring guidance.

| Command | Description |
|---------|-------------|
| `pretorin recipe list` | List all loaded recipes with id, name, tier, author, and source path (`--tier`, `--source`) |
| `pretorin recipe show <recipe_id>` | Display a recipe's manifest, body, and (with `--sources`) all loader paths |
| `pretorin recipe new <recipe_id>` | Scaffold a new recipe directory (`--location` user/project/builtin, `--author`, `--name`) |
| `pretorin recipe validate <recipe_id>` | Validate a recipe's manifest, scripts, and description quality (`--path` for path-based override) |
| `pretorin recipe run <recipe_id>` | Run a recipe's script locally for testing (`--script/-s`, `--param/-p` repeatable, `--path`, `--system`, `--framework`, `--no-context`) |

## Scanning

The legacy `pretorin scan` command was removed when the recipes system landed.
Scanning now happens through built-in recipes that the calling AI agent invokes
via MCP. See [STIG Scanning](./scanning.md) for the recipe-based workflow.

| Recipe ID | Wraps | CLI requirement |
|-----------|-------|-----------------|
| `inspec-baseline` | Chef InSpec | `inspec` |
| `openscap-baseline` | OpenSCAP | `oscap` |
| `cloud-aws-baseline` | AWS APIs | `aws` |
| `cloud-azure-baseline` | Azure APIs | `az` |
| `manual-attestation` | Human attestation | — |

## Deprecated Commands

| Command | Description |
|---------|-------------|
| `pretorin harness init` | Deprecated: initialize harness config |
| `pretorin harness doctor` | Deprecated: validate harness setup |
| `pretorin harness run "<task>"` | Deprecated: run task through harness backend |
