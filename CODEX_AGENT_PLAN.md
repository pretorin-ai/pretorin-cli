# Codex Agent Integration Plan

## Goal

Replace the current `harness` subprocess wrapper with a proper Codex SDK integration that:
- Embeds Codex as a **managed runtime** inside the Pretorin CLI
- Pins and manages the Codex binary version (no surprise upstream updates)
- Is **fully isolated** from any standalone Codex installation the user may have
- Supports **any OpenAI-spec LLM endpoint** (Azure OpenAI, vLLM, LiteLLM, Ollama, etc.)
- Streams agent events for real-time output, evidence capture, and audit logging

---

## Architecture Overview

```
~/.pretorin/
├── config.json              # Existing — API key, base URLs, active system/framework
├── bin/
│   └── codex-v0.88.0        # Pinned Codex binary (per-platform)
└── codex/                   # Isolated Codex home (NOT ~/.codex)
    └── config.toml          # Generated at runtime, never shared with user's Codex
```

```
src/pretorin/
├── agent/
│   ├── __init__.py
│   ├── codex_runtime.py     # NEW — Binary management (download, verify, cache)
│   ├── codex_agent.py       # NEW — Codex SDK session management + event streaming
│   ├── runner.py            # EXISTING — Keep for OpenAI Agents SDK path (non-Codex)
│   ├── tools.py             # EXISTING — Keep for Agents SDK path
│   ├── skills.py            # EXISTING — Extend with Codex-compatible skill definitions
│   └── mcp_config.py        # EXISTING — Reuse for injecting MCP servers into Codex
├── cli/
│   ├── agent.py             # UPDATE — Add `codex` subcommands alongside existing `run`
│   ├── harness.py           # DEPRECATE — Keep for backward compat, add deprecation warning
│   └── main.py              # UPDATE — Wire new commands
└── client/
    └── config.py            # UPDATE — Add codex_version, codex_home properties
```

---

## Phase 1: Codex Runtime Manager (`codex_runtime.py`)

Manages the Codex binary lifecycle with full isolation.

### Constants & Version Pinning

```python
CODEX_VERSION = "rust-v0.88.0-alpha.3"  # Maintainer bumps this deliberately

# SHA256 checksums per platform — verified on download
CODEX_CHECKSUMS = {
    "darwin-arm64": "abc123...",
    "darwin-x64":   "def456...",
    "linux-x64":    "789ghi...",
}

# GitHub release URL pattern
CODEX_DOWNLOAD_URL = (
    "https://github.com/openai/codex/releases/download/{version}/"
    "codex-{platform}.tar.gz"
)
```

### Key Functions

```python
class CodexRuntime:
    """Manages the pinned Codex binary."""

    def __init__(self, version: str = CODEX_VERSION):
        self.version = version
        self.bin_dir = Path.home() / ".pretorin" / "bin"
        self.codex_home = Path.home() / ".pretorin" / "codex"

    @property
    def binary_path(self) -> Path:
        """Path to the pinned binary."""
        return self.bin_dir / f"codex-{self.version}"

    @property
    def is_installed(self) -> bool:
        """Check if pinned version is available."""
        return self.binary_path.exists() and self.binary_path.stat().st_mode & 0o111

    def ensure_installed(self) -> Path:
        """Download and verify if not present. Returns binary path."""
        if self.is_installed:
            return self.binary_path
        self._download()
        self._verify_checksum()
        self._make_executable()
        return self.binary_path

    def build_env(self, api_key: str, base_url: str, **extra) -> dict[str, str]:
        """Build isolated environment for Codex process.

        Sets CODEX_HOME to ~/.pretorin/codex/ so the binary never
        reads ~/.codex/config.toml.
        """
        env = {
            "CODEX_HOME": str(self.codex_home),
            "OPENAI_API_KEY": api_key,
            "OPENAI_BASE_URL": base_url,
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
        }
        env.update(extra)
        return env

    def write_config(self, model: str, provider_name: str, base_url: str,
                     env_key: str, wire_api: str = "responses") -> Path:
        """Write an isolated config.toml under CODEX_HOME.

        This config is Pretorin-managed and never touches ~/.codex/.
        """
        ...

    def cleanup_old_versions(self) -> list[Path]:
        """Remove binaries that don't match the current pinned version."""
        ...
```

### Platform Detection

```python
def _detect_platform() -> str:
    """Returns 'darwin-arm64', 'darwin-x64', or 'linux-x64'."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    if system == "darwin":
        return "darwin-arm64" if machine == "arm64" else "darwin-x64"
    elif system == "linux":
        return "linux-x64"
    raise RuntimeError(f"Unsupported platform: {system}/{machine}")
```

### Design Decisions

- **No auto-update.** Binary only changes when user upgrades `pretorin` package.
- **Checksum verification.** SHA256 per platform, fails loudly if mismatch.
- **Old version cleanup.** `cleanup_old_versions()` available but not automatic — user controls when.
- **`CODEX_HOME` isolation.** The binary reads config from `~/.pretorin/codex/` not `~/.codex/`.

---

## Phase 2: Codex Agent Session (`codex_agent.py`)

Wraps the `openai-codex-sdk` Python SDK with Pretorin-specific behavior.

### Core Class

```python
class CodexAgent:
    """Manages Codex SDK sessions with Pretorin isolation."""

    def __init__(
        self,
        runtime: CodexRuntime | None = None,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.runtime = runtime or CodexRuntime()
        self._config = Config()

        # Resolve model settings — Pretorin config → env vars → defaults
        self.model = model or self._config.openai_model
        self.base_url = base_url or self._config.model_api_base_url
        self.api_key = api_key or self._resolve_api_key()

    def _resolve_api_key(self) -> str:
        """Resolve API key: PRETORIN_LLM_API_KEY → OPENAI_API_KEY → config."""
        ...

    async def run(
        self,
        task: str,
        working_directory: Path | None = None,
        skill: str | None = None,
        stream: bool = True,
    ) -> AgentResult:
        """Execute a compliance task via Codex.

        1. Ensures pinned binary is installed
        2. Writes isolated config.toml
        3. Spawns Codex via SDK with codex_path_override
        4. Injects Pretorin MCP server for compliance tools
        5. Streams events (tool calls, text output, errors)
        6. Captures findings for evidence creation
        """
        binary_path = self.runtime.ensure_installed()
        env = self.runtime.build_env(
            api_key=self.api_key,
            base_url=self.base_url,
        )

        # Write isolated config with model settings
        self.runtime.write_config(
            model=self.model,
            provider_name="pretorin",
            base_url=self.base_url,
            env_key="OPENAI_API_KEY",
        )

        from openai_codex_sdk import Codex

        codex = Codex({
            "codex_path_override": str(binary_path),
            "env": env,
        })

        thread = codex.start_thread({
            "working_directory": str(working_directory or Path.cwd()),
        })

        prompt = self._build_prompt(task, skill)

        if stream:
            return await self._run_streamed(thread, prompt)
        else:
            turn = await thread.run(prompt)
            return AgentResult(
                response=turn.final_response,
                items=turn.items,
            )

    async def _run_streamed(self, thread, prompt: str) -> AgentResult:
        """Stream events with real-time output and evidence capture."""
        streamed = await thread.run_streamed(prompt)
        items = []
        response_text = ""

        async for event in streamed.events:
            if event.type == "text.delta":
                # Real-time output to console
                rprint(event.text, end="")
                response_text += event.text
            elif event.type == "item.completed":
                items.append(event.item)
                # Could intercept tool calls here for evidence capture
            elif event.type == "turn.completed":
                # Token usage tracking
                pass

        return AgentResult(response=response_text, items=items)

    def _build_prompt(self, task: str, skill: str | None) -> str:
        """Build compliance-focused prompt, optionally with skill guidance."""
        from pretorin.agent.skills import get_skill

        base = (
            "You are a compliance-focused coding assistant operating through Pretorin.\n"
            "You have access to Pretorin MCP tools for querying frameworks, controls, "
            "evidence, and narratives.\n\n"
            "Rules:\n"
            "1. Use Pretorin MCP tools to get authoritative compliance data.\n"
            "2. Reference framework/control IDs explicitly (e.g., AC-02, SC-07).\n"
            "3. Use zero-padded control IDs (ac-02 not ac-2).\n"
            "4. Return actionable output with evidence gaps and next steps.\n\n"
        )

        if skill:
            skill_def = get_skill(skill)
            if skill_def:
                base += f"Skill: {skill_def.name}\n{skill_def.system_prompt}\n\n"

        return base + f"Task:\n{task}"
```

### AgentResult Dataclass

```python
@dataclass
class AgentResult:
    """Result from a Codex agent session."""
    response: str
    items: list[Any] = field(default_factory=list)
    usage: dict[str, int] | None = None
    evidence_created: list[str] = field(default_factory=list)
```

### MCP Server Injection

The Codex config.toml written by `write_config()` includes the Pretorin MCP server:

```toml
[mcp_servers.pretorin]
command = "pretorin"
args = ["mcp-serve"]
```

This gives the Codex agent access to all 21 Pretorin MCP tools automatically. Additional user-configured MCP servers from `~/.pretorin/mcp.json` are merged in.

---

## Phase 3: CLI Commands (`cli/agent.py`)

### New Commands

Add to the existing `agent` command group:

```
pretorin agent run "task"              # Codex-powered (new default)
    --skill gap-analysis               # Optional predefined skill
    --model gpt-4o                     # Model override
    --base-url https://...             # Endpoint override
    --working-dir ./my-project         # Working directory
    --no-stream                        # Buffered output instead of streaming

pretorin agent doctor                  # Validate Codex runtime setup
pretorin agent install                 # Force (re)install pinned Codex binary
pretorin agent version                 # Show pinned Codex version + binary status
```

### Updated `agent run` Command

```python
@app.command("run")
def agent_run(
    message: str = typer.Argument(..., help="Compliance task or question."),
    skill: str | None = typer.Option(None, "--skill", "-s", help="Predefined skill."),
    model: str | None = typer.Option(None, "--model", "-m", help="Model override."),
    base_url: str | None = typer.Option(None, "--base-url", help="LLM endpoint override."),
    working_dir: Path | None = typer.Option(None, "--working-dir", "-w", help="Working directory."),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output."),
    use_agents_sdk: bool = typer.Option(False, "--legacy", help="Use OpenAI Agents SDK instead of Codex."),
) -> None:
    """Run a compliance task using the Codex agent runtime."""
    if use_agents_sdk:
        # Preserve existing Agents SDK path for backward compat
        _run_legacy_agent(message, skill, model)
        return

    _check_agent_deps()  # Verify openai-codex-sdk is installed

    asyncio.run(_run_codex_agent(
        message=message,
        skill=skill,
        model=model,
        base_url=base_url,
        working_dir=working_dir,
        stream=not no_stream,
    ))
```

### Deprecation of `harness` Commands

```python
# In harness.py — add deprecation warnings
@app.command("run")
def harness_run(...):
    """[DEPRECATED] Use 'pretorin agent run' instead."""
    rprint("[yellow]⚠ 'pretorin harness run' is deprecated. Use 'pretorin agent run' instead.[/yellow]")
    # ... existing implementation continues to work ...
```

---

## Phase 4: Config & Dependency Updates

### `pyproject.toml` Changes

```toml
[project.optional-dependencies]
agent = [
    "openai-agents>=0.2.9",
    "openai>=1.0.0",
    "openai-codex-sdk>=0.1.11",   # ADD — Codex Python SDK
]
```

### `client/config.py` Additions

```python
# New properties on Config class

@property
def codex_home(self) -> Path:
    """Isolated Codex home directory."""
    return Path.home() / ".pretorin" / "codex"

@property
def codex_bin_dir(self) -> Path:
    """Directory for managed Codex binaries."""
    return Path.home() / ".pretorin" / "bin"
```

---

## Phase 5: Testing

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `tests/test_codex_runtime.py` | Version pinning, platform detection, checksum verification, env building, config writing, old version cleanup |
| `tests/test_codex_agent.py` | Prompt building, skill integration, API key resolution, config isolation |
| `tests/test_agent_cli.py` | CLI argument parsing, deprecation warnings, doctor/install/version commands |

### Key Test Cases

1. **Binary isolation**: Verify `codex_path_override` is always set, `CODEX_HOME` points to `~/.pretorin/codex/`
2. **Config isolation**: Verify config.toml is written under `CODEX_HOME`, not `~/.codex/`
3. **Model flexibility**: Verify custom `base_url` and `model` flow through to the SDK env/config
4. **Checksum failure**: Verify download is rejected if hash doesn't match
5. **Platform detection**: Verify correct binary is selected for darwin-arm64, darwin-x64, linux-x64
6. **Backward compat**: Verify `--legacy` flag still uses OpenAI Agents SDK path
7. **Control ID normalization**: Verify the compliance prompt instructs zero-padded IDs
8. **Skill prompts**: Verify skill system prompts are injected correctly
9. **Deprecation**: Verify `harness run` shows deprecation warning

### Integration Test (Manual)

```bash
# Install with agent extras
pip install -e ".[agent]"

# Verify binary management
pretorin agent version          # Shows pinned version + status
pretorin agent install          # Downloads binary
pretorin agent doctor           # Validates full setup

# Run against a real endpoint
export OPENAI_API_KEY=sk-...
pretorin agent run "Analyze this codebase for FedRAMP Moderate AC-02" \
    --working-dir /path/to/project \
    --skill gap-analysis

# Verify isolation
ls ~/.pretorin/bin/              # Should have codex-{version}
ls ~/.pretorin/codex/            # Should have config.toml
ls ~/.codex/                     # Should be UNTOUCHED
```

---

## Migration Path

| Stage | Action |
|-------|--------|
| **v0.5.0** | Add `codex_runtime.py`, `codex_agent.py`, update `agent run` to use Codex by default, deprecate `harness` commands |
| **v0.6.0** | Remove `harness` command group entirely, remove old Agents SDK runner if unused |
| **Ongoing** | Bump `CODEX_VERSION` + checksums as needed, release new Pretorin version |

---

## Isolation Summary

| Resource | User's Codex | Pretorin's Codex |
|----------|-------------|-----------------|
| Binary | System PATH (`npm`, `brew`) | `~/.pretorin/bin/codex-{version}` |
| Config | `~/.codex/config.toml` | `~/.pretorin/codex/config.toml` |
| MCP servers | User's own config | Pretorin MCP auto-injected |
| API key env var | `OPENAI_API_KEY` | `PRETORIN_LLM_API_KEY` (or `OPENAI_API_KEY` via env dict) |
| Model | User's choice | Pretorin config → `--model` flag → env var |
| Python package | Not affected | `pretorin[agent]` optional extras |

---

## Lessons Applied from Today's Session

1. **Control ID normalization** — The compliance prompt explicitly instructs "use zero-padded control IDs (ac-02 not ac-2)". The `normalize_control_id()` utility is already in `utils.py` for any programmatic paths.

2. **Model provider flexibility** — No hardcoded model names. Everything flows through config with overrides: `Config.model_api_base_url` → `--base-url` CLI flag → `OPENAI_BASE_URL` env var. Supports Azure OpenAI, vLLM, LiteLLM, Ollama, or any OpenAI-spec endpoint.

3. **Default to production URL** — `DEFAULT_MODEL_API_BASE_URL = "https://platform.pretorin.com/v1"`. No test/dev URLs in source code.

4. **Evidence integration** — The streamed event loop in `_run_streamed()` is designed so you can intercept agent findings and auto-create evidence via `pretorin evidence create` or the MCP tools. This closes the loop between "agent found something" and "evidence is tracked on the platform."

5. **Config file ownership** — Today's `harness init` wrote to `~/.codex/config.toml` which risks collision. The new approach owns `~/.pretorin/codex/config.toml` exclusively via `CODEX_HOME`.

6. **Backward compatibility** — The `--legacy` flag preserves the existing OpenAI Agents SDK path. The `harness` commands get deprecation warnings but keep working through v0.5.x.
