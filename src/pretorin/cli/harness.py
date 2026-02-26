"""AI harness integration commands.

Provides an opinionated wrapper so Pretorin can run as a compliance-focused
front-end for coding-agent harnesses.
"""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer
from rich import print as rprint
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.client.config import Config

HARNESS_CONFIG_FILE = Path.home() / ".codex" / "config.toml"
PRETORIN_PROVIDER_NAME = "pretorin"
OPENAI_PROVIDER_NAME = "openai"
PRETORIN_ENV_KEY = "PRETORIN_LLM_API_KEY"
OPENAI_ENV_KEY = "OPENAI_API_KEY"
DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_WIRE_API = "responses"
DISALLOWED_ENDPOINT_SNIPPETS = ("chatgpt.com", "api.openai.com")

app = typer.Typer(
    name="harness",
    help="[Deprecated] AI harness wrapper. Use 'pretorin agent' instead.",
    no_args_is_help=True,
    deprecated=True,
)


@dataclass
class DoctorReport:
    """Harness setup assessment."""

    ok: bool
    provider: str | None
    provider_base_url: str | None
    provider_env_key: str | None
    mcp_enabled: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        """Serialize report for JSON output."""
        return {
            "ok": self.ok,
            "provider": self.provider,
            "provider_base_url": self.provider_base_url,
            "provider_env_key": self.provider_env_key,
            "mcp_enabled": self.mcp_enabled,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def _set_scalar(content: str, key: str, value: str) -> str:
    """Set or append a top-level string scalar key in TOML text."""
    line = f'{key} = "{value}"'
    pattern = re.compile(rf"(?m)^{re.escape(key)}\s*=\s*.*$")
    if pattern.search(content):
        return pattern.sub(line, content, count=1)
    prefix = "" if not content.strip() else "\n"
    return f"{content.rstrip()}{prefix}\n{line}\n"


def _replace_or_append_table(content: str, table_name: str, body_lines: list[str]) -> str:
    """Replace a table block if present, else append it."""
    header = f"[{table_name}]"
    table_pattern = re.compile(
        rf"(?ms)^\[{re.escape(table_name)}\]\n.*?(?=^\[|\Z)",
    )
    block = "\n".join([header, *body_lines]).rstrip() + "\n"
    if table_pattern.search(content):
        return table_pattern.sub(block, content, count=1)
    separator = "" if not content.strip() else "\n"
    return f"{content.rstrip()}{separator}\n{block}"


def _read_harness_config_text() -> str:
    if not HARNESS_CONFIG_FILE.exists():
        return ""
    return HARNESS_CONFIG_FILE.read_text()


def _write_harness_config_text(content: str) -> None:
    HARNESS_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    HARNESS_CONFIG_FILE.write_text(content.strip() + "\n")


def _get_scalar_value(content: str, key: str) -> str | None:
    match = re.search(rf'(?m)^{re.escape(key)}\s*=\s*"([^"]+)"\s*$', content)
    return match.group(1) if match else None


def _get_table_value(content: str, table_name: str, key: str) -> str | None:
    section_match = re.search(
        rf"(?ms)^\[{re.escape(table_name)}\]\n(.*?)(?=^\[|\Z)",
        content,
    )
    if not section_match:
        return None
    section = section_match.group(1)
    value_match = re.search(rf'(?m)^{re.escape(key)}\s*=\s*"([^"]+)"\s*$', section)
    return value_match.group(1) if value_match else None


def _get_table_array(content: str, table_name: str, key: str) -> list[str] | None:
    section_match = re.search(
        rf"(?ms)^\[{re.escape(table_name)}\]\n(.*?)(?=^\[|\Z)",
        content,
    )
    if not section_match:
        return None
    section = section_match.group(1)
    value_match = re.search(rf"(?m)^{re.escape(key)}\s*=\s*\[([^\]]*)\]\s*$", section)
    if not value_match:
        return None
    raw_items = value_match.group(1).split(",")
    return [item.strip().strip('"').strip("'") for item in raw_items if item.strip()]


def _contains_disallowed_endpoint(base_url: str | None) -> bool:
    if not base_url:
        return False
    lower = base_url.lower()
    return any(snippet in lower for snippet in DISALLOWED_ENDPOINT_SNIPPETS)


def _evaluate_setup(content: str, allow_openai_api: bool, backend_command: str) -> DoctorReport:
    errors: list[str] = []
    warnings: list[str] = []

    if shutil.which(backend_command) is None:
        errors.append(f"`{backend_command}` binary not found in PATH.")

    provider = _get_scalar_value(content, "model_provider")
    if not provider:
        errors.append("`model_provider` is not set in ~/.codex/config.toml.")

    expected_provider = OPENAI_PROVIDER_NAME if allow_openai_api else PRETORIN_PROVIDER_NAME
    if provider and provider != expected_provider:
        errors.append(f"model_provider is `{provider}`, expected `{expected_provider}` for this mode.")

    provider_base_url = None
    provider_env_key = None
    if provider:
        provider_base_url = _get_table_value(content, f"model_providers.{provider}", "base_url")
        provider_env_key = _get_table_value(content, f"model_providers.{provider}", "env_key")

    if provider == PRETORIN_PROVIDER_NAME:
        if not provider_base_url:
            errors.append("Pretorin provider is missing `base_url`.")
        elif _contains_disallowed_endpoint(provider_base_url):
            errors.append("Pretorin provider base_url points to OpenAI/ChatGPT endpoint.")
        if provider_env_key != PRETORIN_ENV_KEY:
            warnings.append(f"Pretorin provider env_key should be `{PRETORIN_ENV_KEY}`.")

    if provider == OPENAI_PROVIDER_NAME and not allow_openai_api:
        errors.append("OpenAI API provider is configured, but this mode forbids OpenAI endpoints.")

    if provider_env_key and not os.environ.get(provider_env_key):
        warnings.append(f"Environment variable `{provider_env_key}` is not set in this shell.")

    mcp_command = _get_table_value(content, "mcp_servers.pretorin", "command")
    mcp_args = _get_table_array(content, "mcp_servers.pretorin", "args")
    mcp_enabled = bool(mcp_command == "pretorin" and mcp_args and "mcp-serve" in mcp_args)
    if not mcp_enabled:
        errors.append("Pretorin MCP server is not configured under `[mcp_servers.pretorin]`.")

    ok = len(errors) == 0
    return DoctorReport(
        ok=ok,
        provider=provider,
        provider_base_url=provider_base_url,
        provider_env_key=provider_env_key,
        mcp_enabled=mcp_enabled,
        errors=errors,
        warnings=warnings,
    )


def _build_compliance_prompt(task: str) -> str:
    """Wrap a user task with Pretorin-specific operating guidance."""
    return (
        "You are a compliance-focused coding assistant operating through Pretorin.\n"
        "Rules:\n"
        "1. Prefer authoritative data from Pretorin MCP tools before assumptions.\n"
        "2. Surface framework/control IDs explicitly in findings and recommendations.\n"
        "3. Return actionable output with evidence gaps and next remediation steps.\n\n"
        f"Task:\n{task}"
    )


def _deprecation_warning(command: str) -> None:
    """Print deprecation warning for harness commands."""
    if not is_json_mode():
        rprint(f"[yellow]Warning: 'pretorin harness {command}' is deprecated. Use 'pretorin agent' instead.[/yellow]")


@app.command("init")
def harness_init(
    provider_url: str | None = typer.Option(
        None,
        "--provider-url",
        help="Pretorin model provider base URL (required unless --allow-openai-api is used).",
    ),
    allow_openai_api: bool = typer.Option(
        False,
        "--allow-openai-api",
        help="Testing mode: configure the harness to use OpenAI API instead of Pretorin provider.",
    ),
    backend_command: str = typer.Option(
        "codex",
        "--backend-command",
        help="Executable name for the coding harness binary.",
    ),
) -> None:
    """[Deprecated] Create or update harness config with Pretorin policy defaults.

    Use 'pretorin agent install' and 'pretorin agent run' instead.
    """
    _deprecation_warning("init")
    config = Config()
    resolved_provider_url = provider_url or config.model_api_base_url
    if not allow_openai_api and not resolved_provider_url:
        rprint("[red]Pretorin provider URL is required.[/red]")
        raise typer.Exit(1)

    content = _read_harness_config_text()

    if allow_openai_api:
        content = _set_scalar(content, "model_provider", OPENAI_PROVIDER_NAME)
        content = _set_scalar(content, "web_search", "disabled")
        content = _replace_or_append_table(
            content,
            "model_providers.openai",
            [
                'name = "OpenAI API"',
                f'base_url = "{DEFAULT_OPENAI_BASE_URL}"',
                f'wire_api = "{DEFAULT_WIRE_API}"',
                f'env_key = "{OPENAI_ENV_KEY}"',
            ],
        )
    else:
        content = _set_scalar(content, "model_provider", PRETORIN_PROVIDER_NAME)
        content = _set_scalar(content, "web_search", "disabled")
        content = _replace_or_append_table(
            content,
            "model_providers.pretorin",
            [
                'name = "Pretorin Platform"',
                f'base_url = "{resolved_provider_url}"',
                f'wire_api = "{DEFAULT_WIRE_API}"',
                f'env_key = "{PRETORIN_ENV_KEY}"',
            ],
        )

    content = _replace_or_append_table(
        content,
        "mcp_servers.pretorin",
        [
            'command = "pretorin"',
            'args = ["mcp-serve"]',
        ],
    )

    _write_harness_config_text(content)

    report = _evaluate_setup(content, allow_openai_api=allow_openai_api, backend_command=backend_command)
    if is_json_mode():
        print_json(
            {
                "config_path": str(HARNESS_CONFIG_FILE),
                "mode": "openai-api-test" if allow_openai_api else "pretorin-provider",
                "backend_command": backend_command,
                "report": report.to_dict(),
            }
        )
        return

    mode = "OpenAI API test mode" if allow_openai_api else "Pretorin provider mode"
    rprint(f"[#95D7E0]✓[/#95D7E0] Updated harness config at [bold]{HARNESS_CONFIG_FILE}[/bold]")
    rprint(f"[#95D7E0]✓[/#95D7E0] Mode: {mode}")
    if report.errors:
        for error in report.errors:
            rprint(f"[red]✗ {error}[/red]")
        raise typer.Exit(1)
    for warning in report.warnings:
        rprint(f"[yellow]! {warning}[/yellow]")


@app.command("doctor")
def harness_doctor(
    allow_openai_api: bool = typer.Option(
        False,
        "--allow-openai-api",
        help="Allow OpenAI API endpoint checks for testing only.",
    ),
    backend_command: str = typer.Option(
        "codex",
        "--backend-command",
        help="Executable name for the coding harness binary.",
    ),
) -> None:
    """[Deprecated] Validate harness integration. Use 'pretorin agent doctor' instead."""
    _deprecation_warning("doctor")
    content = _read_harness_config_text()
    if not content:
        report = DoctorReport(
            ok=False,
            provider=None,
            provider_base_url=None,
            provider_env_key=None,
            mcp_enabled=False,
            errors=[f"Harness config not found at {HARNESS_CONFIG_FILE}."],
            warnings=[],
        )
    else:
        report = _evaluate_setup(content, allow_openai_api=allow_openai_api, backend_command=backend_command)

    if is_json_mode():
        print_json(report.to_dict())
        if not report.ok:
            raise typer.Exit(1)
        return

    table = Table(title="Harness Integration Check", show_header=True, header_style="bold")
    table.add_column("Item")
    table.add_column("Value")
    table.add_row("Config file", str(HARNESS_CONFIG_FILE))
    table.add_row("Backend command", backend_command)
    table.add_row("Provider", report.provider or "missing")
    table.add_row("Base URL", report.provider_base_url or "missing")
    table.add_row("Env key", report.provider_env_key or "missing")
    table.add_row("Pretorin MCP", "configured" if report.mcp_enabled else "missing")
    rprint(table)

    for warning in report.warnings:
        rprint(f"[yellow]! {warning}[/yellow]")

    if report.errors:
        for error in report.errors:
            rprint(f"[red]✗ {error}[/red]")
        raise typer.Exit(1)

    rprint("[#95D7E0]✓[/#95D7E0] Harness integration is ready.")


@app.command("run")
def harness_run(
    task: str = typer.Argument(..., help="Compliance task for the coding harness."),
    allow_openai_api: bool = typer.Option(
        False,
        "--allow-openai-api",
        help="Allow OpenAI API provider for testing only.",
    ),
    backend_command: str = typer.Option(
        "codex",
        "--backend-command",
        help="Executable name for the coding harness binary.",
    ),
    backend_exec_subcommand: str = typer.Option(
        "exec",
        "--backend-exec-subcommand",
        help="Subcommand used by the harness for one-shot execution.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the command that would run without executing it.",
    ),
) -> None:
    """[Deprecated] Run harness. Use 'pretorin agent run' instead."""
    _deprecation_warning("run")
    content = _read_harness_config_text()
    report = _evaluate_setup(content, allow_openai_api=allow_openai_api, backend_command=backend_command)
    if not report.ok:
        if is_json_mode():
            print_json(report.to_dict())
        else:
            rprint("[red]Harness setup is not ready. Run `pretorin harness doctor`.[/red]")
            for error in report.errors:
                rprint(f"[red]✗ {error}[/red]")
        raise typer.Exit(1)

    prompt = _build_compliance_prompt(task)
    cmd = [backend_command]
    if backend_exec_subcommand:
        cmd.append(backend_exec_subcommand)
    cmd.append(prompt)

    if dry_run:
        payload = {"command": cmd, "prompt": prompt}
        if is_json_mode():
            print_json(payload)
        else:
            rprint(" ".join(shlex.quote(part) for part in cmd))
        return

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
