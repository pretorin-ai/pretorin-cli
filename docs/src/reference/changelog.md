# Changelog

All notable changes to the Pretorin CLI are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.8.6] - 2026-03-23

### Added
- `pretorin context show --quiet` for compact shell-friendly context checks
- `pretorin context show --check` to fail fast when stored scope is missing, stale, or unverified

### Changed
- `context show` caches the last known system name so offline and stale context output stays human-friendly

### Fixed
- `context show` validates stored context against the platform instead of silently treating deleted systems as active

## [0.8.5] - 2026-03-23

### Fixed
- Reset active system/framework context when logging into a different API endpoint or with a different API key
- Model API base URL now follows the configured platform public API endpoint during login
- `scope populate --json --apply` and `policy populate --json --apply` now persist questionnaire updates
- Larger Codex subprocess line buffer for policy questionnaire responses

## [0.8.0] - 2026-03-07

### Added
- MCP `pretorin_generate_control_artifacts` for read-only AI drafting of control narratives and evidence-gap assessments
- Shared AI drafting workflow helper for structured MCP/CLI parity

### Changed
- MCP system-scoped tools now resolve friendly system names the same way the CLI does
- Codex Desktop MCP configuration can be pinned to the UV-managed Pretorin wrapper

## [0.7.0] - 2026-03-07

### Fixed
- Control implementation parsing tolerant of `notes: null` deployments
- Compatibility fallback for control note reads when `/notes` endpoint returns `405`
- Compatibility fallback for evidence search on system-scoped evidence routes
- Agent `--no-stream` crash on literal `[[PRETORIN_TODO]]` blocks

### Changed
- MCP and legacy agent evidence search tools accept optional `system_id` context

## [0.6.1] - 2026-03-05

### Fixed
- Added required MCP registry ownership marker for PyPI validation

## [0.6.0] - 2026-03-05

### Added
- Shared markdown quality validator for auditor-readable artifacts
- Dedicated tests for markdown quality guardrails
- CLI/MCP/agent parity for reading notes via dedicated endpoint

### Changed
- Narrative and evidence update flows enforce markdown quality checks before push/upsert
- Agent prompts require auditor-ready markdown (lists/tables/code/links)
- Source tagging normalized to `cli` across write paths

### Removed
- Markdown image usage from narrative/evidence authoring contract (temporarily)

## [0.5.4] - 2026-03-05

### Added
- `pretorin narrative get` to read current control narratives
- `pretorin notes list` and `pretorin notes add` for control-note management
- `pretorin evidence search` for platform evidence visibility
- `pretorin evidence upsert` for find-or-create evidence with control linking
- Shared compliance workflow helpers (system resolution, evidence dedupe/upsert, TODO blocks, gap notes)
- MCP `pretorin_get_control_notes` tool

### Changed
- `pretorin_create_evidence` now upserts by default (`dedupe: true`)
- `pretorin evidence push` uses find-or-create upsert logic
- Agent skill prompts include no-hallucination guidance and gap note format

### Removed
- Automatic control status updates from CLI evidence push workflow

## [0.5.3] - 2026-03-02

### Fixed
- CI lint failure formatting
- CLI model key precedence: `OPENAI_API_KEY` → `config.api_key` → `config.openai_api_key`

## [0.5.2] - 2026-02-27

### Fixed
- Rich markup `MarkupError` crash in login flow
- Evidence type mismatch (`documentation` → `policy_document`)
- CMMC control ID casing preserved (no longer incorrectly lowercased)
- `monitoring push` checks active context before requiring `--system`
- `pretorin login` skips prompt when already authenticated
- Demo script `--json` flag position and stdin handling

### Changed
- Default evidence type changed to `policy_document`
- Valid evidence types aligned with API
- Added `.pretorin/` and `evidence/` to `.gitignore`

## [0.5.0] - 2026-02-27

### Added
- Context management (`context list/set/show/clear`)
- Evidence commands (`evidence create/list/push/search/upsert`)
- Narrative push (`narrative push`)
- Monitoring events (`monitoring push`)
- Codex agent runtime (`agent run` with skills, `agent doctor/install/version/skills`)
- Agent MCP management (`agent mcp-list/mcp-add/mcp-remove`)
- Code review (`review run/status`)
- 14 new MCP tools for system, evidence, narrative, monitoring, notes, and control operations
- Control ID normalization (zero-padding)
- Interactive demo walkthrough script
- Beta messaging across CLI, MCP, and README

### Changed
- Platform API base URL changed to `/api/v1/public`
- Evidence and linking scoped to system
- `update_control_status()` changed from PATCH to POST

### Removed
- `pretorin narrative generate` — use `pretorin agent run --skill narrative-generation`
- `pretorin_generate_narrative` MCP tool

### Security
- MCP mutation handler parameter validation
- Client-side enum validation
- Path traversal protection in evidence writer
- TOML injection prevention in Codex config writer
- Connection error URL display

## [0.2.0] - 2026-02-06

### Added
- `--json` flag for machine-readable output
- `pretorin frameworks family/metadata/submit-artifact` commands
- Full AI Guidance rendering on control detail view
- `.mcp.json` for Claude Code auto-discovery
- Usage examples in command docstrings

### Changed
- Control references shown by default (replaced `--references` with `--brief`)
- Default controls limit changed to 0 (show all)

## [0.1.0] - 2025-02-03

### Added
- Initial public release
- CLI commands for browsing compliance frameworks
- Authentication commands (login, logout, whoami)
- Configuration management
- MCP server with 7 tools and analysis resources
- Self-update functionality
- Rich terminal output with Rome-bot mascot
- Docker support
- GitHub Actions CI/CD
- Integration test suite

### Supported Frameworks
- NIST SP 800-53 Rev 5
- NIST SP 800-171 Rev 2/3
- FedRAMP (Low, Moderate, High)
- CMMC Level 1, 2, and 3

[0.8.6]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.8.5...v0.8.6
[0.8.5]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.8.0...v0.8.5
[0.8.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.6.1...v0.7.0
[0.6.1]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.5.6...v0.6.0
[0.5.4]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.5.0...v0.5.2
[0.5.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.3.1...v0.5.0
[0.2.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pretorin-ai/pretorin-cli/releases/tag/v0.1.0
