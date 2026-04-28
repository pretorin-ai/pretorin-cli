# Changelog

All notable changes to the Pretorin CLI will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2026-04-27

### Added
- **`pretorin evidence` capture is now mandatory (#88)**: when `evidence upsert` or `evidence create` is invoked with `--code-file` or `--log-file`, the CLI reads the referenced content, redacts API keys and password assignments, and embeds the redacted snippet as a fenced code block in the pushed `description`. Each captured description ends with an italic provenance footer matching the issue body design — `*Captured from \`<path>\` [lines N-M] [· commit \`<short>\`] · <RFC3339 UTC> [· N secrets redacted]*` — so auditors see file path, line range, commit, and capture timestamp directly under the snippet. The hard rule applies at the workflow boundary, so MCP tools, agent tools, and campaign apply paths cannot create an evidence record with `code_file_path` set but no fenced code block in the description. New companion flags: `--log-tail`, `--log-since`, `--redact-pii / --no-redact-pii`, `--no-redact` (interactive confirm required, refused in non-TTY).
- **`code_snippet` round-trips through `EvidenceWriter` (#89)**: previously `_format_frontmatter` silently dropped the field on disk. Snippets are now base64-encoded under `code_snippet_b64` so multi-line content, fenced markdown, unicode, and embedded `---` delimiters survive the write/read round-trip.

### Changed (BREAKING)
- `pretorin evidence upsert --code-file <p>` and `pretorin evidence create --code-file <p>` always capture the file content. The previous path-only behavior is no longer reachable; the `--no-capture` flag does not exist.
- The capture rule is enforced by a Pydantic `model_validator` on **`EvidenceCreate`** and **`EvidenceBatchItemCreate`**. Every write path (CLI single, CLI sync, campaign apply, agent batch tool, MCP `pretorin_create_evidence_batch`) constructs one of these models. The validator raises `ValidationError` when `code_file_path` is set but the description has no fenced code block.
- `pretorin.workflows.evidence_validation.enrich_evidence_recommendations` (used by campaign apply) runs the file content through the same redact + compose pipeline as CLI capture. The structured `code_snippet` API field stays populated, but with the *redacted* snippet rather than raw — closing a latent leak path where campaign apply was pushing unredacted file content to the platform.

### Redactor scope
- API keys (AWS / GitHub / Slack / Stripe / Google API / JWT / PEM private keys).
- Password-shaped assignments: `password`, `passwd`, `pwd`, `secret`, `api[_-]?key`, `access[_-]?token`, `auth[_-]?token` followed by `:` or `=` and a quoted value of length ≥ 4.
- That's it. Earlier prereleases of this work used `detect-secrets` (with its `Base64HighEntropyString` / `HexHighEntropyString` plugins) and a generic entropy fallback. Both produced false positives on every multi-character identifier in YAML / Python / Helm files (`resources`, `cpu`, `autoscaling`, …) and made captured snippets unreadable. Both have been removed.

## [0.16.3] - 2026-04-26

### Fixed
- **CCI chain test fix**: `test_cci_chain_with_system_status` now correctly mocks `resolve_execution_context` so CCI status rendering is exercised. No production code changes.

## [0.16.2] - 2026-04-21

### Fixed
- **`pretorin campaign controls --family` case-insensitive resolution (#84)**: `--family cc6` (or any casing/whitespace variant) now resolves to the canonical `CC6` before hitting the backend's case-sensitive `list_controls(family_id=...)`. Unknown families raise a structured `PretorianClientError` whose message lists available families and points at `pretorin frameworks families <framework-id>`; MCP clients receive `framework_id`, `requested_family_id`, and `available_families` in `details` for programmatic recovery. Raw user input is preserved on the campaign checkpoint's `request.family_id` field. Same resolver applied to the `pretorin_prepare_campaign` MCP handler. `--family` help text now references the discovery command.

## [0.16.1] - 2026-04-21

### Added
- **Gap questions for policy and scope Q&A**: MCP tool descriptions now guide agents through an answer-first workflow — answer from workspace evidence silently, then present structured "gap questions" to the user only for organizational knowledge the workspace can't provide. Ensures consistent interview formatting across any MCP-connected agent (Claude Code, Codex, Cursor, etc.).

## [0.16.0] - 2026-04-21

### Changed (BREAKING)
- `evidence_type` is now required on every CLI, MCP, agent, and workflow write path (#79). CLI paths hard-error when the user omits `-t/--type`; every other path runs a client-side normalizer before submission.
  - `pretorin evidence create` / `pretorin evidence upsert` require `-t/--type`. The error lists all 13 canonical values so users can self-correct.
  - `pretorin_create_evidence` MCP tool schema lists `evidence_type` in `required` and removes the `policy_document` default.
  - `EvidenceCreate` and `EvidenceBatchItemCreate` pydantic models reject missing and non-canonical `evidence_type` values via a shared `field_validator`.
  - `LocalEvidence` dataclass requires `evidence_type`. Existing on-disk evidence files missing the frontmatter field will fail to load — add the field manually (canonical values are listed in `pretorin.evidence.types.VALID_EVIDENCE_TYPES`).
  - `upsert_evidence()` and `build_narrative_todo_block()` no longer default `evidence_type` / `suggested_evidence_type` to `policy_document`.

### Added
- **Evidence provenance fields**: CLI now sends `code_file_path`, `code_line_numbers`, `code_snippet`, `code_repository`, and `code_commit_hash` to the platform on all evidence creation paths (single, batch, campaign). Auditors can trace evidence back to specific source files and commits.
- **Source verification**: CLI maps attested source identities to the platform's `SourceVerificationPayload` schema with proper `source_type` and `source_role` mapping. Sent alongside `_provenance` on all evidence writes when session is verified.
- **`pretorin evidence upload`**: New CLI command to upload files (screenshots, PDFs, configs, logs) as evidence. Computes SHA-256 checksum locally, verifies server-side. 25MB max, restricted MIME types.
- **`pretorin_upload_evidence` MCP tool**: AI agents and recipes can upload files as evidence via MCP.
- **File reference validation**: Campaign apply validates AI-reported file paths and line numbers before sending to the platform. Reads actual file content as the canonical snippet instead of trusting the agent's output.
- **`source_role` on `SourceIdentity`**: Each attestation provider declares its compliance role (code, identity, deployment, monitoring). Used for platform source verification mapping.
- **Git context from snapshot**: Evidence creation auto-populates `code_repository` and `code_commit_hash` from the attested snapshot instead of separate subprocess calls.
- **Code provenance on local evidence**: `pretorin evidence create` and `push` now support `code_file_path`, `code_line_numbers`, `code_repository`, `code_commit_hash` in markdown frontmatter.
- `pretorin.evidence.types` module: canonical 13-type enum, AI-drift alias map (`EVIDENCE_TYPE_ALIASES`), and `normalize_evidence_type()`. The normalizer uses a static alias map plus `difflib` fuzzy matching (stdlib, zero-cost, deterministic, future-proof) before falling back to `"other"`. Common AI near-misses like `audit_log` → `log_file`, plural `test_results` → `test_result`, `screenshoot` → `screenshot`, `policy_doc` → `policy_document` now normalize instead of causing HTTP 400s during campaign apply.
- `campaign.apply.control` telemetry adds `evidence_type_normalized` (alias + fuzzy hits) and `evidence_type_fallback` (unknown → `"other"`) counters. The legacy `rejected_invalid_type` counter is now always `0` (the normalizer no longer rejects) and is **deprecated**; it will be dropped in 0.17.0. Migrate dashboards to the new counters.
- `evidence_type.normalized` structured log records (INFO for alias/fuzzy matches, WARNING for unknown → `"other"` fallback) so post-ship telemetry can size the drift map.

### Changed
- `EvidenceCreate` and `EvidenceBatchItemCreate` models now include 5 optional code provenance fields.
- Campaign evidence batch construction now extracts `code_file_path`, `code_line_numbers`, `code_snippet`, and `relevance_notes` from AI recommendations (previously dropped).
- AI generation prompt schema includes code provenance fields in `evidence_recommendations`.
- `upsert_evidence()` accepts `code_context` parameter and creates enriched evidence (with provenance) as a new record rather than reusing a match that lacks provenance.
- `evidence upsert` CLI command has new `--code-file`, `--code-lines`, `--code-repo`, `--code-commit` options.

### Fixed
- SOC2 campaign batches that previously failed partially because the AI emitted non-canonical `evidence_type` strings (`report`, `procedure`, `contract`, `audit_log`, plural `test_results`, etc.) now succeed end-to-end. Unknown strings still emit a canonical gap note so reviewers see the drift, but the evidence lands rather than being dropped.
- Non-campaign write paths (CLI `evidence create`/`upsert`, MCP `create_evidence`/`create_evidence_batch`, agent tools, `upsert_evidence` workflow) can no longer silently tag missing-type evidence as `policy_document` and pollute the platform's custom-policies page.

## [0.15.5] - 2026-04-20

### Fixed
- Campaign `--apply` runs no longer flood the evidence locker with AI-authored summaries typed as `policy_document` (issue #77). The pipeline now wires `recommended_notes` through to the platform as real gap notes, rejects evidence recommendations with missing or invalid `evidence_type` (turning them into synthesized gap notes), and emits a structured `campaign.apply.control` telemetry line for post-ship measurement.
- Partial failures in the per-control notes write now raise `PretorianClientError` with the failing indexes, mirroring the existing evidence-batch behavior so checkpoint resumes are idempotent.
- Evidence batch result mapping now aligns offsets to the original recommendation index via the accepted-items list and asserts length match, fixing a latent index-drift bug that appeared once any recommendation was rejected mid-loop.
- Completion note now fires when all pending work has landed across runs, not only when something new was written in the current run.

### Changed
- `evidence_type` is now required on `EvidenceBatchItemCreate`. The campaign batch write path no longer silently tags missing types as `policy_document`; pydantic validation raises instead. Other evidence write paths (CLI, MCP, direct API) keep their existing defaults.
- Agent drafting prompts (`_build_generation_task`, `_draft_control_fix`, `_WORKFLOW_GUARDRAILS`, codex system prompt, `[[PRETORIN_TODO]]` template) now list all 13 valid evidence types verbatim and state that an empty `evidence_recommendations` list is a valid result — gaps belong in `recommended_notes`.
- `_WORKFLOW_GUARDRAILS` merged in the evidence-collection skill's "concrete, auditable artifacts" language so narrative-generation skill callers inherit the same rules.

## [0.15.4] - 2026-04-18

### Changed
- Updated 6 dependencies to resolve 7 known vulnerabilities (cryptography, pygments, pyjwt, pytest, python-multipart, requests)
- Added CLAUDE.md and AGENTS.md for AI agent context

## [0.15.3] - 2026-04-18

### Fixed
- `pretorin update` now checks PyPI before running pip, skipping reinstall when already current
- `pretorin update` verifies the installed version after pip runs, detecting silent failures in pipx/uv-managed environments
- `pretorin update` no longer compares against stale in-memory `__version__` after upgrading

### Added
- `pretorin update [VERSION]` accepts an optional version argument to install a specific release

## [0.15.2] - 2026-04-18

### Changed
- Documentation sync: rebuilt all docs to match current codebase

## [0.15.1] - 2026-04-17

### Added
- Evidence delete command: `pretorin evidence delete <evidence-id>` with `--yes` flag for non-interactive workflows
- MCP tool `pretorin_delete_evidence` for programmatic evidence deletion within system scope
- API client method `delete_evidence` wired to the public `DELETE /systems/{system_id}/evidence/{evidence_id}` endpoint

## [0.15.0] - 2026-04-16

### Added
- Source manifest requirement policy (Phase 3 of #64): declare which external sources a system expects and gate compliance writes on their presence
- `pretorin context manifest` command for viewing the resolved manifest and evaluating it against detected sources
- Manifest loading from four layered sources: `PRETORIN_SOURCE_MANIFEST` env var, repo-local `.pretorin/source-manifest.json`, per-system user config, or inline config key
- Family-level source requirements: manifest can declare that AC controls need AWS, CM controls need git, PS controls need HRIS, etc.
- Three requirement levels (required/recommended/optional) with write blocking on missing required sources and warnings for missing recommended
- Control family extraction for NIST 800-53, CMMC, and 800-171r3 control ID formats
- Anchored identity matching prevents org-name prefix collisions in manifest identity patterns
- Manifest evaluation results in write provenance (`manifest_status` and `missing_required_sources` fields)
- `control_id` threading through MCP `resolve_execution_scope` and 4 API write methods for family-level provenance
- Manifest version validation rejects unknown schema versions with a clear warning
- 134 new tests covering manifest models, parsing, loading, matching, evaluation, family extraction, write guard enforcement, and provenance enrichment

### Changed
- `_enforce_source_attestation` now evaluates manifest requirements after the existing MISMATCH check
- `resolve_execution_context` accepts an optional `control_id` for family-level manifest enforcement
- `build_write_provenance` accepts an optional `control_id` and includes manifest evaluation in provenance metadata
- `TODOS.md` added to `.gitignore`

## [0.14.0] - 2026-04-10

### Changed
- MCP and agent write workflows now treat the active CLI context as a strict execution boundary by default, with an explicit `allow_scope_override` escape hatch for intentional cross-scope writes
- Control-scoped MCP and agent workflows now route through one shared scope-validation path so exact control lookup happens in the resolved framework before any write proceeds
- Agent guidance now tells built-in workflows to resolve an exact user-supplied control in the active framework before doing broader discovery
- `pretorin mcp-serve` now emits a non-blocking stderr update prompt when a newer CLI release is available, so MCP-only users can discover upgrades without interrupting active tool calls

### Fixed
- `apply_campaign` now reports `apply: true` after a successful apply run and persists that state back to the checkpoint summary
- Stored active context and campaign checkpoints are now validated against the current API environment before campaign reads or writes proceed
- Control-scoped MCP and agent updates now refuse silent remaps like `cm-04.02` to a different control when the exact control does not resolve in the active framework

### Added
- `pretorin_get_cli_status` and the `status://cli` MCP resource expose local CLI version, update availability, and upgrade guidance to MCP hosts and agents

## [0.13.1] - 2026-04-07

### Added
- `pretorin_get_stig` MCP tool for STIG benchmark detail
- `pretorin_get_cci_chain` MCP tool for full Control → CCI → SRG → STIG rule traceability

## [0.13.0] - 2026-04-07

### Added
- Complete STIG/CCI MCP tools: `list_stigs`, `get_stig`, `list_stig_rules`, `get_stig_rule`, `list_ccis`, `get_cci`, `get_cci_chain`, `get_cci_status`, `get_stig_applicability`, `infer_stigs`, `get_test_manifest`, `submit_test_results`
- STIG/CCI agent tools for OpenAI Agents SDK
- `pretorin stig` CLI group: `list`, `show`, `rules`, `applicable`, `infer`
- `pretorin cci` CLI group: `list`, `show`, `chain`
- `pretorin scan` CLI group: `doctor`, `manifest`, `run`, `results`
- Scanner orchestration module with support for OpenSCAP, InSpec, AWS/Azure Cloud Scanners, and Manual review

## [0.12.0] - 2026-04-04

### Added
- Vendor management CLI: `pretorin vendor list/create/get/update/delete/upload-doc/list-docs`
- MCP vendor tools: `list_vendors`, `create_vendor`, `get_vendor`, `update_vendor`, `delete_vendor`, `upload_vendor_document`, `list_vendor_documents`, `link_evidence_to_vendor`
- Inheritance/responsibility MCP tools: `set_control_responsibility`, `get_control_responsibility`, `remove_control_responsibility`, `generate_inheritance_narrative`, `get_stale_edges`, `sync_stale_edges`

## [0.11.0] - 2026-04-02

### Added
- External-agent-first campaign orchestration with shared checkpointed prepare/claim/context/submit/apply/status flows
- Six MCP campaign tools: `pretorin_prepare_campaign`, `pretorin_claim_campaign_items`, `pretorin_get_campaign_item_context`, `pretorin_submit_campaign_proposal`, `pretorin_apply_campaign`, and `pretorin_get_campaign_status`
- `pretorin campaign status --checkpoint ...` for attach/read-only visibility into prepared or running campaigns
- Campaign workflow recipes for Codex, Claude Code, and other MCP-capable external agents

### Changed
- `pretorin campaign` now prepares runs for external execution by default when the optional builtin backend is unavailable, instead of failing item-by-item
- CLI and MCP campaign adapters now share one request-normalization and validation path to reduce drift
- Optional built-in executor dependencies are now exposed as `pretorin[builtin-agent]`, with `pretorin[agent]` preserved as a compatibility alias

## [0.10.0] - 2026-03-28

### Added
- Workflow state and analytics MCP tools: `get_workflow_state`, `get_analytics_summary`, `get_family_analytics`, `get_policy_analytics`
- Family operations MCP tools: `get_pending_families`, `get_family_bundle`, `trigger_family_review`, `get_family_review_results`
- Policy workflow MCP tools: `get_pending_policy_questions`, `get_policy_question_detail`, `answer_policy_question`, `get_policy_workflow_state`, `trigger_policy_generation`, `trigger_policy_review`, `get_policy_review_results`
- Scope workflow MCP tools: `get_pending_scope_questions`, `get_scope_question_detail`, `answer_scope_question`, `trigger_scope_generation`, `trigger_scope_review`, `get_scope_review_results`
- ExecutionScope for thread-safe parallel agent execution

## [0.9.7] - 2026-03-25

### Fixed
- Aligned CLI control status validation with the live platform status enum set, including `partially_implemented`
- Aligned MCP control status validation with the live platform status enum set to match public API behavior
- Synced package version metadata and release notes so PyPI builds publish a consistent CLI version

### Changed
- Updated CLI and MCP coverage tests to reflect the platform control status contract used by public control workflows

## [0.8.7] - 2026-03-23

### Added
- MCP questionnaire tooling for scope and organization policy workflows: `pretorin_patch_scope_qa`, `pretorin_list_org_policies`, `pretorin_get_org_policy_questionnaire`, and `pretorin_patch_org_policy_qa`

### Changed
- MCP documentation now reflects the full 29-tool surface, including existing batch evidence support and the new questionnaire tools

## [0.8.6] - 2026-03-23

### Added
- `pretorin context show --quiet` for a compact one-line context summary that works well in scripts and shell prompts
- `pretorin context show --check` to fail fast when the stored system/framework scope is missing, stale, or cannot be verified

### Changed
- `context show` now caches and displays the last known system name so offline or stale context output stays human-friendly instead of falling back to a raw UUID

### Fixed
- `context show` now validates stored context against the platform and clearly reports invalid or unverified scope instead of silently treating deleted systems as active

## [0.8.5] - 2026-03-23

### Fixed
- Reset active system/framework context when logging into a different API endpoint or with a different API key, preventing stale localhost scope context from bleeding into prod usage
- Align the model API base URL with the configured platform public API endpoint during login, so prod logins no longer keep talking to a localhost model proxy
- Make `scope populate --json --apply` and `policy populate --json --apply` persist questionnaire updates instead of exiting after preview output
- Raise the Codex subprocess line buffer to tolerate larger policy questionnaire responses without stream parsing failures

## [0.8.0] - 2026-03-07

### Added
- MCP `pretorin_generate_control_artifacts` for read-only AI drafting of control narratives and evidence-gap assessments using the same Codex workflow as the CLI
- Shared AI drafting workflow helper for structured MCP/CLI parity around generated compliance artifacts

### Changed
- MCP system-scoped tools now resolve friendly system names the same way the CLI does, returning canonical system IDs in responses
- Codex Desktop MCP configuration can be pinned to the UV-managed Pretorin wrapper to avoid PATH drift to incompatible installs

## [0.7.0] - 2026-03-07

### Fixed
- Made control implementation parsing tolerant of deployments that return `notes: null`, preventing narrative and implementation read crashes on untouched controls
- Added compatibility fallback for control note reads when the dedicated `/notes` endpoint returns `405 Method Not Allowed`
- Added compatibility fallback for evidence search on deployments that only expose system-scoped evidence routes
- Prevented `pretorin agent run --no-stream` from crashing when model output includes literal `[[PRETORIN_TODO]]` blocks

### Changed
- MCP and legacy agent evidence search tools now accept optional `system_id` context and use the same compatibility search path as the CLI

## [0.6.1] - 2026-03-05

### Fixed
- Added required MCP registry ownership marker (`mcp-name: io.github.pretorin-ai/pretorin`) to PyPI README metadata so MCP registry publish validation succeeds

## [0.6.0] - 2026-03-05

### Added
- Shared markdown quality validator for auditor-readable artifacts, including strict no-heading enforcement and rich-markdown requirements
- Dedicated tests for markdown quality guardrails, including explicit image rejection
- CLI/MCP/agent parity for reading notes via the dedicated control-notes endpoint

### Changed
- Narrative and evidence update flows now enforce markdown quality checks before push/upsert
- Agent prompts and skill guidance now require auditor-ready markdown (lists/tables/code/links) and ban image markdown until platform upload support is available
- Source tagging normalized to `cli` across CLI/MCP/agent write paths

### Removed
- Markdown image usage from narrative/evidence authoring contract (temporarily disabled pending platform-side attachment support)

## [0.5.4] - 2026-03-05

### Added
- `pretorin narrative get` to read current control narratives from the platform
- `pretorin notes list` and `pretorin notes add` for explicit control-note management
- `pretorin evidence search` for platform evidence visibility
- `pretorin evidence upsert` for find-or-create evidence with control/system linking
- Shared compliance workflow helpers for:
  - system resolution
  - evidence dedupe/upsert
  - canonical narrative TODO block rendering
  - canonical gap-note rendering
- MCP `pretorin_get_control_notes` tool for note read parity

### Changed
- `pretorin_create_evidence` MCP behavior now upserts by default (`dedupe: true`) and returns normalized upsert metadata (`evidence_id`, `created`, `linked`, `match_basis`)
- `pretorin evidence push` now uses find-or-create upsert logic (reused matches are reported separately)
- Agent skill prompts now include explicit no-hallucination guidance, structured TODO placeholders, and gap note format requirements
- Legacy agent toolset now includes `add_control_note`, `link_evidence`, and `get_control_notes`

### Removed
- Automatic control status updates and monitoring-event side effects from CLI evidence push workflow

## [0.5.3] - 2026-03-02

### Fixed
- CI lint failure from `ruff format --check` by formatting `src/pretorin/agent/codex_agent.py` and `src/pretorin/cli/auth.py`
- CLI model key precedence: `OPENAI_API_KEY` -> `config.api_key` -> `config.openai_api_key`

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
- Interactive demo walkthrough script (`tools/demo-walkthrough.sh`)
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

[0.16.2]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.16.1...v0.16.2
[0.16.1]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.5...v0.16.0
[0.15.5]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.4...v0.15.5
[0.15.4]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.3...v0.15.4
[0.15.3]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.2...v0.15.3
[0.15.2]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.1...v0.15.2
[0.15.1]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.14.0...v0.15.0
[0.17.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.16.3...v0.17.0
[0.16.3]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.16.2...v0.16.3
[0.14.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.13.1...v0.14.0
[0.13.1]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.13.0...v0.13.1
[0.13.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.12.0...v0.13.0
[0.12.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.11.0...v0.12.0
[0.11.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.10.0...v0.11.0
[0.10.0]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.9.7...v0.10.0
[0.9.7]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.8.7...v0.9.7
[0.8.7]: https://github.com/pretorin-ai/pretorin-cli/compare/v0.8.6...v0.8.7
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
