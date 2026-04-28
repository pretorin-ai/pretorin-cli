# Changelog

All notable changes to the Pretorin CLI are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2026-04-28

### Added
- **`pretorin evidence` capture is mandatory (#88)**: `evidence upsert` and `evidence create` always read, redact, and embed `--code-file` / `--log-file` content into the pushed `description`. New companion flags: `--log-file`, `--log-tail`, `--log-since`, `--redact-pii / --no-redact-pii`, `--no-redact` (interactive confirm only).
- **`code_snippet` round-trips through `EvidenceWriter` (#89)**: previously the field was silently dropped on disk. Now base64-encoded under `code_snippet_b64` so multi-line content survives the write/read cycle.
- **Inline env-var value resolution (#92)**: when `--code-file` capture detects env-var references (`os.getenv`, `process.env.X`, `${PORT:-8080}`, k8s `$(VAR)`), the CLI resolves them against the current process env and renders the result in a unified variable table at the end of the description. New `pretorin.evidence.env_resolve` module.
- **Two-tier safety on resolved values (#92)**: tier 1 hides values for vars whose name contains a secret-shaped substring (`KEY` / `SECRET` / `TOKEN` / `PASSWORD` / `CRED` / `PRIVATE` / `AUTH` / `SESSION` / `COOKIE` / `SALT` / `SIGNATURE` / `CERT` / `BEARER`). Tier 2 runs the value through the snippet redactor — AWS / GitHub / Stripe / JWT / PEM / `proto://user:pass@host` URLs all hide the value. Tier 2 runs independently of `--no-redact`.
- **`cred_url` redaction pattern (#92)**: catches credential-bearing URLs (`postgres://user:pass@host`, `redis://:pass@host`, `https://user:pass@api.example.com`, etc.) without flagging clean URLs or `@` in path/query strings.
- **Languages detected (#92)**: Python (`os.getenv`, `os.environ.get`, `os.environ["X"]` — AST-based so docstrings/string literals don't false-match), JS/TS (`process.env.X`, `process.env["X"]`), shell-family — bash / fish / **YAML** / **Dockerfile** (`$VAR`, `${VAR}`, `${VAR:-default}`), plus Kubernetes `$(VAR)` in YAML. YAML coverage catches CI-workflow env refs in `run:` blocks. Bare `$var` / `$(var)` require uppercase first char so JSON-schema YAML (`$ref`, `$schema`) and shell substitution (`$(date)`) don't false-match. GitHub Actions `${{ ... }}` is intentionally not matched.
- **Inline-definition resolution (#92)**: when the snippet itself defines a variable (YAML `env:` mapping, k8s `- name: X / value: Y`, Dockerfile `ARG`/`ENV`, shell `export`), that takes priority over the agent's process env. Resolution order: inline def → process env → source default → unset. Tier-1/tier-2 redaction still runs on whichever value wins.
- **Cross-file definition tracing for Python (#92)**: when a captured Python snippet references a module-level constant imported from another file (`from app.config import DELETION_GRACE_PERIOD_DAYS`), the CLI traces it to the definition file and embeds the relevant lines as a second fenced code block. AST-based detection, hybrid AST-import / `git grep -nE` lookup with config-path priority, self-reference guard, bounded scan (5000 files / 30s).
- **Unified variable table (#92)** at the end of every captured description. Columns: Variable · Value · Source. Source distinguishes `inline` / `env` / `default` / `<file>:<line>` / `—`. Env-var resolutions and cross-file constants share one table.
- **`--no-resolve-env` and `--no-trace-defs` flags (#92)** to disable env-var resolution and cross-file tracing per-capture. Both default on.
- **Footer counts (#92)**: provenance footer now reports env-resolution and definition-tracing activity alongside redactions.

### Changed (BREAKING)
- `--code-file` / `--log-file` always capture; the `--no-capture` flag does not exist.
- The capture rule is enforced by a Pydantic `model_validator` on `EvidenceCreate` and `EvidenceBatchItemCreate`, so every write path (CLI, MCP, agent batch, campaign apply) trips it equally. Setting `code_file_path` without an embedded fenced code block in the description raises `ValidationError`. Source provenance lives on the structured columns of the API record (path / lines / commit / `collected_at`); the description does not duplicate it.
- The redactor scope is API keys (AWS / GitHub / Slack / Stripe / Google / JWT / PEM private keys) plus password-shaped assignments plus credential-bearing URLs. Vendor plugin sets and entropy heuristics from earlier prereleases were removed because they false-positived on every multi-character identifier in YAML / Python / Helm files.
- Captured descriptions render a markdown variable table instead of a bullet list (#92). Truncation preserves the table; the original snippet body truncates first, then cross-file definition snippets, then the table.

### Out of scope (#92, intentionally deferred)
- `.env` autoload (resolution is against the live process env only).
- Recursive resolution (`X = int(os.getenv("Y"))` doesn't also resolve Y).
- Class-attribute / pydantic-settings / dataclass field lookups.
- Languages other than Python for cross-file tracing.
- Cross-repo references.
- Logs (`--log-file`) are unchanged. Log lines are runtime output already.
- The campaign-apply path (`enrich_evidence_recommendations`) is intentionally untouched — agent-runtime env / filesystem layout is not the user's local repo.

### Changed (BREAKING)
- `--code-file` / `--log-file` always capture; the `--no-capture` flag does not exist.
- The capture rule is enforced by a Pydantic `model_validator` on `EvidenceCreate` and `EvidenceBatchItemCreate`, so every write path (CLI, MCP, agent batch, campaign apply) trips it equally. Setting `code_file_path` without an embedded fenced code block in the description raises `ValidationError`. Source provenance lives on the structured columns of the API record (path / lines / commit / `collected_at`); the description does not duplicate it.
- The redactor scope is API keys (AWS / GitHub / Slack / Stripe / Google / JWT / PEM private keys) plus password-shaped assignments. Vendor plugin sets and entropy heuristics from earlier prereleases were removed because they false-positived on every multi-character identifier in YAML / Python / Helm files.

## [0.16.3] - 2026-04-26

### Fixed
- **CCI chain test fix**: `test_cci_chain_with_system_status` now correctly mocks `resolve_execution_context` so CCI status rendering is exercised. No production code changes.

## [0.16.2] - 2026-04-21

### Fixed
- **`pretorin campaign controls --family` case-insensitive resolution (#84)**: `--family cc6` now resolves to canonical `CC6` before hitting the backend. Unknown families raise a structured error listing available families and pointing at `pretorin frameworks families <framework-id>`. Same fix applied to `pretorin_prepare_campaign` MCP handler.

## [0.16.1] - 2026-04-21

### Added
- **Gap questions for policy and scope Q&A**: MCP tool descriptions guide agents through answer-first workflow with structured gap questions for organizational knowledge gaps.

## [0.16.0] - 2026-04-21

### Changed (BREAKING)
- `evidence_type` is now required on every CLI, MCP, agent, and workflow write path (#79). CLI paths hard-error when the user omits `-t/--type`; every other path runs a client-side normalizer before submission.

### Added
- **Evidence provenance fields**: CLI sends `code_file_path`, `code_line_numbers`, `code_snippet`, `code_repository`, `code_commit_hash` on all evidence creation paths. Auditors can trace evidence to source files and commits.
- **Source verification mapping**: Attested source identities mapped to platform's `SourceVerificationPayload` with `source_type` and `source_role`.
- **`pretorin evidence upload`**: Upload files (screenshots, PDFs, configs) as evidence with SHA-256 integrity verification.
- **`pretorin_upload_evidence` MCP tool**: Agents and recipes can upload evidence files via MCP.
- **File reference validation**: Campaign apply reads actual file content as canonical snippet, validates paths and line ranges.
- **Code provenance on local evidence**: Frontmatter supports code_* fields for local evidence create and push.
- `pretorin.evidence.types` module: canonical 13-type enum, AI-drift alias map, and `normalize_evidence_type()` with fuzzy matching.

### Changed
- Evidence models include code provenance fields. Campaign extracts `code_*` and `relevance_notes` from AI recommendations.
- `upsert_evidence()` creates enriched evidence as new record when provenance fields are provided.
- AI generation prompt requests code file paths and line numbers in evidence recommendations.

### Fixed
- SOC2 campaign batches with non-canonical `evidence_type` strings now succeed end-to-end via the normalizer.
- Non-campaign write paths can no longer silently tag missing-type evidence as `policy_document`.

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

---

## [0.15.4] - 2026-04-18

### Changed
- Updated 6 dependencies to resolve 7 known vulnerabilities (cryptography, pygments, pyjwt, pytest, python-multipart, requests)
- Added CLAUDE.md and AGENTS.md for AI agent context

---

## [0.15.3] - 2026-04-18

### Fixed
- `pretorin update` now checks PyPI before running pip, skipping reinstall when already current
- `pretorin update` verifies the installed version after pip runs, detecting silent failures in pipx/uv-managed environments

### Added
- `pretorin update [VERSION]` accepts an optional version argument to install a specific release

---

## [0.15.2] - 2026-04-18

### Changed
- Documentation sync: rebuilt all docs to match current codebase

---

## [0.15.1] - 2026-04-17

### Added
- `pretorin evidence delete <evidence-id>` command with `--yes` flag for non-interactive workflows
- MCP tool `pretorin_delete_evidence` for programmatic evidence deletion within system scope
- API client method `delete_evidence` for the public DELETE endpoint

---

## [0.15.0] - 2026-04-16

### Added
- Source manifest requirement policy: declare which external sources a system expects and gate compliance writes on their presence
- `pretorin context manifest` command for viewing the resolved manifest and evaluating it against detected sources
- Manifest loading from four layered sources: env var, repo-local `.pretorin/source-manifest.json`, per-system user config, or inline config key
- Family-level source requirements with three requirement levels (required/recommended/optional) and write blocking on missing required sources
- Manifest evaluation results in write provenance (`manifest_status` and `missing_required_sources` fields)

### Changed
- `_enforce_source_attestation` now evaluates manifest requirements after the existing MISMATCH check
- `resolve_execution_context` and `build_write_provenance` accept optional `control_id` for family-level manifest enforcement

---

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

---

## [0.13.1] - 2026-04-07

### Added
- `pretorin_get_stig` MCP tool for STIG benchmark detail
- `pretorin_get_cci_chain` MCP tool for full Control → CCI → SRG → STIG rule traceability

---

## [0.13.0] - 2026-04-07

### Added
- Complete STIG/CCI MCP tools: `list_stigs`, `get_stig`, `list_stig_rules`, `get_stig_rule`, `list_ccis`, `get_cci`, `get_cci_chain`, `get_cci_status`, `get_stig_applicability`, `infer_stigs`, `get_test_manifest`, `submit_test_results`
- STIG/CCI agent tools for OpenAI Agents SDK
- `pretorin stig` CLI group: `list`, `show`, `rules`, `applicable`, `infer`
- `pretorin cci` CLI group: `list`, `show`, `chain`
- `pretorin scan` CLI group: `doctor`, `manifest`, `run`, `results`
- Scanner orchestration module with support for OpenSCAP, InSpec, AWS/Azure Cloud Scanners, and Manual review

---

## [0.12.0] - 2026-04-04

### Added
- Vendor management CLI: `pretorin vendor list/create/get/update/delete/upload-doc/list-docs`
- MCP vendor tools: `list_vendors`, `create_vendor`, `get_vendor`, `update_vendor`, `delete_vendor`, `upload_vendor_document`, `list_vendor_documents`, `link_evidence_to_vendor`
- Inheritance/responsibility MCP tools: `set_control_responsibility`, `get_control_responsibility`, `remove_control_responsibility`, `generate_inheritance_narrative`, `get_stale_edges`, `sync_stale_edges`

---

## [0.11.0] - 2026-04-02

### Added
- Campaign CLI: `pretorin campaign controls/policy/scope/status`
- Campaign MCP tools: `prepare_campaign`, `claim_campaign_items`, `get_campaign_item_context`, `submit_campaign_proposal`, `apply_campaign`, `get_campaign_status`
- External-agent-first campaign pattern with checkpoint persistence and lease-based concurrency
- Campaign builtin executor for local execution

---

## [0.10.0] - 2026-03-28

### Added
- Workflow state and analytics MCP tools: `get_workflow_state`, `get_analytics_summary`, `get_family_analytics`, `get_policy_analytics`
- Family operations MCP tools: `get_pending_families`, `get_family_bundle`, `trigger_family_review`, `get_family_review_results`
- Policy workflow MCP tools: `get_pending_policy_questions`, `get_policy_question_detail`, `answer_policy_question`, `get_policy_workflow_state`, `trigger_policy_generation`, `trigger_policy_review`, `get_policy_review_results`
- Scope workflow MCP tools: `get_pending_scope_questions`, `get_scope_question_detail`, `answer_scope_question`, `trigger_scope_generation`, `trigger_scope_review`, `get_scope_review_results`
- ExecutionScope for thread-safe parallel agent execution

---

## [0.9.7] - 2026-03-25

### Fixed
- Aligned CLI control status validation with the live platform status enum set, including `partially_implemented`
- Aligned MCP control status validation with the live platform status enum set to match public API behavior
- Synced package version metadata and release notes so PyPI builds publish a consistent CLI version

### Changed
- Updated CLI and MCP coverage tests to reflect the platform control status contract used by public control workflows

## [0.8.7] - 2026-03-23

### Added
- MCP questionnaire tooling for scope and organization policy workflows

### Changed
- MCP documentation now reflects the full 29-tool surface, including batch evidence support

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
