# Complete Command Reference

## Global Options

| Option | Description |
|--------|-------------|
| `--json` | JSON output mode for scripting and AI agents |
| `--help` | Show command help |

## Root Commands

| Command | Description |
|---------|-------------|
| `pretorin login` | Authenticate with the Pretorin API |
| `pretorin logout` | Clear stored credentials |
| `pretorin whoami` | Display authentication status |
| `pretorin version` | Show CLI version |
| `pretorin update` | Update to latest version |
| `pretorin mcp-serve` | Start the MCP server (stdio transport) |

## Framework Commands

| Command | Description |
|---------|-------------|
| `pretorin frameworks list` | List all frameworks |
| `pretorin frameworks get <id>` | Get framework details |
| `pretorin frameworks families <id>` | List control families |
| `pretorin frameworks family <fw> <family>` | Get control family details |
| `pretorin frameworks controls <id>` | List controls (`--family`, `--limit`) |
| `pretorin frameworks control <fw> <ctrl>` | Get control details (`--references`) |
| `pretorin frameworks documents <id>` | Get document requirements |
| `pretorin frameworks metadata <id>` | Get per-control framework metadata |
| `pretorin frameworks submit-artifact <file>` | Submit a compliance artifact JSON file |

## Context Commands

| Command | Description |
|---------|-------------|
| `pretorin context list` | List systems and frameworks with progress |
| `pretorin context set` | Set active system/framework context (`--system`, `--framework`) |
| `pretorin context show` | Display current active context |
| `pretorin context clear` | Clear active context |

## Evidence Commands

| Command | Description |
|---------|-------------|
| `pretorin evidence create <ctrl> <fw>` | Create a local evidence file (`--name`, `--description`) |
| `pretorin evidence list` | List local evidence files (`--framework`) |
| `pretorin evidence push` | Push local evidence to the platform |
| `pretorin evidence search` | Search platform evidence (`--control-id`, `--framework-id`, `--system`, `--limit`) |
| `pretorin evidence upsert <ctrl> <fw>` | Find-or-create evidence and link it (`--name`, `--description`, `--type`) |

## Narrative Commands

| Command | Description |
|---------|-------------|
| `pretorin narrative get <ctrl> <fw>` | Get current control narrative (`--system`) |
| `pretorin narrative push <ctrl> <fw> <sys> <file>` | Push a narrative file to the platform |

## Notes Commands

| Command | Description |
|---------|-------------|
| `pretorin notes list <ctrl> <fw>` | List control notes (`--system`) |
| `pretorin notes add <ctrl> <fw>` | Add a control note (`--content`) |

## Monitoring Commands

| Command | Description |
|---------|-------------|
| `pretorin monitoring push` | Push a monitoring event (`--system`, `--title`, `--event-type`, `--severity`) |

## Agent Commands

| Command | Description |
|---------|-------------|
| `pretorin agent run "<task>"` | Run a compliance task (`--skill`, `--model`, `--base-url`, `--working-dir`, `--no-stream`, `--legacy`) |
| `pretorin agent doctor` | Validate Codex runtime setup |
| `pretorin agent install` | Download the pinned Codex binary |
| `pretorin agent version` | Show pinned Codex version and install status |
| `pretorin agent skills` | List available agent skills |
| `pretorin agent mcp-list` | List configured MCP servers for the agent |
| `pretorin agent mcp-add <name> stdio <cmd>` | Add an MCP server configuration (`--arg`) |
| `pretorin agent mcp-remove <name>` | Remove an MCP server configuration |

## Review Commands

| Command | Description |
|---------|-------------|
| `pretorin review run` | Review code against a control (`--control-id`, `--framework-id`, `--path`, `--local`, `--output-dir`) |
| `pretorin review status` | Check implementation status for a control (`--control-id`) |

## Config Commands

| Command | Description |
|---------|-------------|
| `pretorin config list` | List all configuration |
| `pretorin config get <key>` | Get a config value |
| `pretorin config set <key> <value>` | Set a config value |
| `pretorin config path` | Show config file path |

## Deprecated Commands

| Command | Description |
|---------|-------------|
| `pretorin harness init` | Deprecated: initialize harness config |
| `pretorin harness doctor` | Deprecated: validate harness setup |
| `pretorin harness run "<task>"` | Deprecated: run task through harness backend |
