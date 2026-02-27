# Changelog

All notable changes to the Pretorin CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.2] - 2026-02-27

### Fixed
- Rich markup error in login flow — unbalanced `[dim]` tags caused `MarkupError` crash
- Evidence type mismatch — CLI used `documentation` but API expects `policy_document`, `screenshot`, `configuration`, etc.
- Control ID casing — CMMC-style IDs like `AC.L1-3.1.1` were incorrectly lowercased by `normalize_control_id`
- `monitoring push` now checks active context before requiring `--system` flag
- `pretorin login` skips API key prompt when already authenticated (validates key against API)
- Demo script: `--json` flag position (`pretorin --json context show`, not `pretorin context show --json`)
- Demo script: `pause` reads from `/dev/tty` so commands no longer consume stdin meant for prompts

### Changed
- Default evidence type changed from `documentation` to `policy_document` across CLI, MCP, and agent tools
- Valid evidence types aligned with API: `screenshot`, `screen_recording`, `log_file`, `configuration`, `test_result`, `certificate`, `attestation`, `code_snippet`, `repository_link`, `policy_document`, `scan_result`, `interview_notes`, `other`
- Demo walkthrough adds prerequisites note, fedramp-moderate validation, and checkpoint pauses between sections
- Added `.pretorin/` and `evidence/` to `.gitignore` to prevent accidental credential commits

## [0.5.0] - 2026-02-27

### Added
- `pretorin context list` — List available systems and frameworks with compliance progress
- `pretorin context set` — Set active system/framework context (interactive or via `--system`/`--framework` flags)
- `pretorin context show` — Display current active context with live progress stats
- `pretorin context clear` — Clear active system/framework context
- `pretorin evidence create` — Create local evidence files with YAML frontmatter
- `pretorin evidence list` — List local evidence files with optional framework filter
- `pretorin evidence push` — Push local evidence to the platform with review flagging
- `pretorin narrative push` — Push a narrative file to the platform for a control
- `pretorin monitoring push` — Push monitoring events (security scans, config changes, access reviews)
- `pretorin agent run` — Run autonomous compliance tasks using the Codex agent runtime
- `pretorin agent run --skill <name>` — Run predefined skills (gap-analysis, narrative-generation, evidence-collection, security-review)
- `pretorin agent doctor/install/version/skills` — Agent runtime management commands
- `pretorin agent mcp-list/mcp-add/mcp-remove` — Manage MCP servers available to the agent
- `pretorin review run` — Review local code against framework controls with AI guidance
- `pretorin review status` — Check implementation status for a specific control
- `resolve_context()` helper for resolving system/framework from flags > stored config > error
- Local-only mode: commands work without platform access, saving artifacts locally
- 14 new MCP tools: system management, evidence CRUD, narrative push, monitoring events, control notes, control status, control implementation details
- `pretorin_add_control_note` MCP tool — Add notes with suggestions for manual steps or systems to connect
- `add_control_note` added to narrative-generation, evidence-collection, and security-review agent skills
- `ControlContext`, `ScopeResponse`, `MonitoringEventCreate`, `EvidenceCreate` client models
- Control ID normalization (zero-padding NIST IDs like ac-3 → ac-03)
- Codex agent runtime with isolated binary management under `~/.pretorin/bin/`
- Interactive demo walkthrough script (`scripts/demo-walkthrough.sh`)
- Beta messaging across CLI banner, login flow, MCP server instructions, and README
- MCP server `instructions` field guides AI agents on beta status and system creation requirements

### Changed
- Default platform API base URL changed to `/api/v1/public` for public API routing
- Client methods updated to match new public API path structure
- `list_evidence()` and `create_evidence()` now scoped to system (not organization)
- `update_control_status()` changed from PATCH to POST with body

### Removed
- `pretorin narrative generate` command — use `pretorin agent run --skill narrative-generation` instead
- `pretorin_generate_narrative` MCP tool — the CLI generates narratives locally, never via the platform

### Security
- All MCP mutation handlers now validate required parameters (system_id, framework_id) before API calls
- Added `system_id` to `create_evidence` and `link_evidence` MCP tool schemas (was missing)
- Client-side enum validation for evidence_type, severity, event_type, and control status
- Path traversal protection in evidence writer (sanitized framework_id and control_id in file paths)
- TOML injection prevention in Codex runtime config writer
- Connection error handling now shows the URL being contacted

## [0.2.0] - 2026-02-06

### Added
- `--json` flag for machine-readable output across all commands (for scripting and AI agents)
- `pretorin frameworks family <framework> <family>` command to get control family details
- `pretorin frameworks metadata <framework>` command to get control metadata for a framework
- `pretorin frameworks submit-artifact <file>` command to submit compliance artifacts
- Positional `FAMILY_ID` argument on `controls` command (`pretorin frameworks controls fedramp-low access-control`)
- Full AI Guidance content rendering on control detail view
- `.mcp.json` for Claude Code MCP auto-discovery
- Usage examples in all command docstrings and error messages

### Changed
- Control references (statement, guidance, objectives) now shown by default on `control` command
- `--references/-r` flag replaced by `--brief/-b` to skip references (old flag kept as hidden deprecated no-op)
- Default controls limit changed from 50 to 0 (show all) to prevent truncated results
- Improved error messages with example command syntax

## [0.1.0] - 2025-02-03

### Added
- Initial public release
- CLI commands for browsing compliance frameworks
  - `pretorin frameworks list` - List all frameworks
  - `pretorin frameworks get` - Get framework details
  - `pretorin frameworks families` - List control families
  - `pretorin frameworks controls` - List controls
  - `pretorin frameworks control` - Get control details
  - `pretorin frameworks documents` - Get document requirements
- Authentication commands
  - `pretorin login` - Authenticate with API key
  - `pretorin logout` - Clear stored credentials
  - `pretorin whoami` - Show authentication status
- Configuration management
  - `pretorin config list` - List all configuration
  - `pretorin config get` - Get a config value
  - `pretorin config set` - Set a config value
  - `pretorin config path` - Show config file path
- MCP (Model Context Protocol) server for AI assistant integration
  - 7 tools for accessing compliance data
  - Resources for analysis guidance
  - Setup instructions for Claude Desktop, Claude Code, Cursor, Codex CLI, and Windsurf
- Self-update functionality via `pretorin update`
- Version checking with PyPI update notifications
- Rich terminal output with branded styling
- Rome-bot ASCII mascot with expressive animations
- Docker support with multi-stage Dockerfile
- Docker Compose configuration for containerized testing
- GitHub Actions CI/CD workflows for testing and PyPI publishing
- Integration test suite for CLI commands and MCP tools
- Comprehensive MCP documentation in `docs/MCP.md`

### Supported Frameworks
- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2/3
- FedRAMP (Low, Moderate, High)
- CMMC Level 1, 2, and 3
- Additional frameworks available on the platform

[0.5.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.3.1...v0.5.0
[0.2.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pretorin-ai/pretorin-cli/releases/tag/v0.1.0
