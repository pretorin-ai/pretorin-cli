"""Agent CLI commands for Pretorin.

Requires optional `agent` dependency group: `pip install pretorin[agent]`
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="agent",
    help="Autonomous compliance agent (requires pip install pretorin[agent]).",
    no_args_is_help=True,
)

ROMEBOT_AGENT = "[#EAB536][°□°][/#EAB536]"


def _check_agent_deps() -> None:
    """Check that agent dependencies are installed."""
    try:
        import agents  # noqa: F401
    except ImportError:
        rprint("[red]Agent features require openai-agents.[/red]")
        rprint("[dim]Install with: [bold]pip install pretorin\\[agent][/bold][/dim]")
        raise typer.Exit(1)


def _check_codex_deps() -> None:
    """Check that Codex SDK dependencies are installed."""
    try:
        import openai_codex_sdk  # noqa: F401
    except ImportError:
        rprint("[red]Codex agent features require openai-codex-sdk.[/red]")
        rprint("[dim]Install with: [bold]pip install pretorin\\[agent][/bold][/dim]")
        raise typer.Exit(1)


@app.command("run")
def agent_run(
    message: str = typer.Argument(..., help="Compliance task or question."),
    skill: str | None = typer.Option(
        None,
        "--skill",
        "-s",
        help="Skill to use: gap-analysis, narrative-generation, evidence-collection, security-review",
    ),
    model: str | None = typer.Option(None, "--model", "-m", help="Model override."),
    base_url: str | None = typer.Option(None, "--base-url", help="LLM endpoint override."),
    working_dir: Path | None = typer.Option(None, "--working-dir", "-w", help="Working directory."),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output."),
    use_legacy: bool = typer.Option(False, "--legacy", help="Use OpenAI Agents SDK instead of Codex runtime."),
    max_turns: int = typer.Option(15, "--max-turns", help="Maximum agent turns (legacy mode only)."),
    no_mcp: bool = typer.Option(False, "--no-mcp", help="Disable external MCP servers (legacy mode only)."),
) -> None:
    """Run a compliance task using the Codex agent runtime.

    Examples:
        pretorin agent run "Analyze this codebase for FedRAMP Moderate AC-02"
        pretorin agent run "Generate narratives for AC controls" --skill narrative-generation
        pretorin agent run "Review security posture" --skill security-review
        pretorin agent run "List my systems" --base-url https://my-vllm.example.com/v1
        pretorin agent run "Check compliance" --legacy  # Use OpenAI Agents SDK
    """
    if use_legacy:
        _check_agent_deps()
        resolved_model = model or "gpt-4o"
        asyncio.run(_run_legacy_agent(message, skill, resolved_model, max_turns, no_mcp, not no_stream))
        return

    _check_codex_deps()
    asyncio.run(
        _run_codex_agent(
            message=message,
            skill=skill,
            model=model,
            base_url=base_url,
            working_dir=working_dir,
            stream=not no_stream,
        )
    )


async def _run_codex_agent(
    message: str,
    skill: str | None,
    model: str | None,
    base_url: str | None,
    working_dir: Path | None,
    stream: bool,
) -> None:
    """Execute a task using the Codex agent runtime."""
    from pretorin.agent.codex_agent import CodexAgent

    try:
        agent = CodexAgent(
            model=model,
            base_url=base_url,
        )
    except RuntimeError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(1)

    if not is_json_mode():
        skill_label = f" with skill [bold]{skill}[/bold]" if skill else ""
        rprint(f"  {ROMEBOT_AGENT}  Starting Codex agent{skill_label} (model: {agent.model})\n")

    try:
        result = await agent.run(
            task=message,
            working_directory=working_dir,
            skill=skill,
            stream=stream,
        )
        if not stream and result:
            if is_json_mode():
                print_json({"response": result.response, "evidence_created": result.evidence_created})
            else:
                rprint(result.response)
    except RuntimeError as e:
        rprint(f"[red]Agent error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Agent error: {e}[/red]")
        raise typer.Exit(1)


async def _run_legacy_agent(
    message: str,
    skill: str | None,
    model: str,
    max_turns: int,
    no_mcp: bool,
    stream: bool,
) -> None:
    """Execute the agent using the legacy OpenAI Agents SDK path."""
    import os

    from pretorin.agent.runner import ComplianceAgent
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    config = Config()

    api_key = os.environ.get("OPENAI_API_KEY", config.get("openai_api_key"))
    base_url = os.environ.get("OPENAI_BASE_URL", config.get("openai_base_url"))
    model = os.environ.get("OPENAI_MODEL", model)

    if not api_key:
        rprint("[red]OPENAI_API_KEY is required for legacy agent features.[/red]")
        rprint("[dim]Set it with: [bold]export OPENAI_API_KEY=sk-...[/bold][/dim]")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' first.[/red]")
            raise typer.Exit(1)

        mcp_servers = None
        if not no_mcp:
            try:
                from pretorin.agent.mcp_config import MCPConfigManager

                mgr = MCPConfigManager()
                if mgr.servers:
                    mcp_servers = mgr.to_sdk_servers()
                    if not is_json_mode():
                        rprint(f"  {ROMEBOT_AGENT}  Connected to {len(mcp_servers)} MCP server(s)\n")
            except Exception:
                pass

        if not is_json_mode():
            skill_label = f" with skill [bold]{skill}[/bold]" if skill else ""
            rprint(f"  {ROMEBOT_AGENT}  Starting legacy agent{skill_label} (model: {model})\n")

        agent = ComplianceAgent(
            client=client,
            model=model,
            api_key=api_key,
            base_url=base_url,
        )

        try:
            result = await agent.run(
                message=message,
                skill=skill,
                mcp_servers=mcp_servers,
                max_turns=max_turns,
                stream=stream,
            )
            if not stream and result:
                rprint(result)
        except PretorianClientError as e:
            rprint(f"[red]Agent error: {e.message}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Agent error: {e}[/red]")
            raise typer.Exit(1)


@app.command("doctor")
def agent_doctor() -> None:
    """Validate Codex runtime setup and configuration."""
    from pretorin.agent.codex_runtime import CodexRuntime

    runtime = CodexRuntime()
    errors: list[str] = []
    warnings: list[str] = []
    info: dict[str, str] = {}

    info["codex_version"] = runtime.version
    info["binary_path"] = str(runtime.binary_path)
    info["binary_installed"] = str(runtime.is_installed)
    info["codex_home"] = str(runtime.codex_home)

    if not runtime.is_installed:
        errors.append(f"Codex binary not found at {runtime.binary_path}. Run 'pretorin agent install'.")

    config_path = runtime.codex_home / "config.toml"
    info["config_exists"] = str(config_path.exists())
    if not config_path.exists():
        warnings.append("Codex config.toml not yet written (will be created on first run).")

    # Check for API key availability
    import os

    has_key = bool(os.environ.get("PRETORIN_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))
    if not has_key:
        warnings.append("No LLM API key found. Set PRETORIN_LLM_API_KEY or OPENAI_API_KEY.")

    ok = len(errors) == 0

    if is_json_mode():
        print_json({"ok": ok, "info": info, "errors": errors, "warnings": warnings})
        if not ok:
            raise typer.Exit(1)
        return

    table = Table(title="Codex Runtime Check", show_header=True, header_style="bold")
    table.add_column("Item")
    table.add_column("Value")
    for key, value in info.items():
        table.add_row(key, value)
    console.print(table)

    for warning in warnings:
        rprint(f"[yellow]! {warning}[/yellow]")
    if errors:
        for error in errors:
            rprint(f"[red]x {error}[/red]")
        raise typer.Exit(1)

    rprint("[#95D7E0]v[/#95D7E0] Codex runtime is ready.")


@app.command("install")
def agent_install() -> None:
    """Download and install the pinned Codex binary."""
    from pretorin.agent.codex_runtime import CodexRuntime

    runtime = CodexRuntime()

    if not is_json_mode():
        rprint(f"  {ROMEBOT_AGENT}  Installing Codex {runtime.version}...")

    try:
        path = runtime.ensure_installed()
        if is_json_mode():
            print_json({"installed": True, "path": str(path), "version": runtime.version})
        else:
            rprint(f"[#95D7E0]v[/#95D7E0] Codex binary installed at {path}")
    except RuntimeError as e:
        if is_json_mode():
            print_json({"installed": False, "error": str(e)})
        else:
            rprint(f"[red]Installation failed: {e}[/red]")
        raise typer.Exit(1)


@app.command("version")
def agent_version() -> None:
    """Show pinned Codex version and binary status."""
    from pretorin.agent.codex_runtime import CodexRuntime

    runtime = CodexRuntime()
    installed = runtime.is_installed
    status = "installed" if installed else "not installed"

    if is_json_mode():
        print_json(
            {
                "codex_version": runtime.version,
                "binary_path": str(runtime.binary_path),
                "status": status,
            }
        )
        return

    rprint(f"[#FF9010]Codex version:[/#FF9010] {runtime.version}")
    rprint(f"[#FF9010]Binary path:[/#FF9010]   {runtime.binary_path}")
    if installed:
        rprint(f"[#FF9010]Status:[/#FF9010]        [#95D7E0]{status}[/#95D7E0]")
    else:
        rprint(f"[#FF9010]Status:[/#FF9010]        [yellow]{status}[/yellow]")
        rprint("[dim]Run 'pretorin agent install' to download.[/dim]")


@app.command("skills")
def agent_skills() -> None:
    """List available agent skills."""
    from pretorin.agent.skills import list_skills

    skills = list_skills()

    if is_json_mode():
        print_json([{"name": s.name, "description": s.description, "max_turns": s.max_turns} for s in skills])
        return

    table = Table(title="Available Skills", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Max Turns", justify="right")

    for s in skills:
        table.add_row(s.name, s.description, str(s.max_turns))

    console.print(table)
    rprint('\n[dim]Use with: pretorin agent run "your task" --skill <name>[/dim]')


@app.command("mcp-list")
def mcp_list() -> None:
    """List configured MCP servers."""
    from pretorin.agent.mcp_config import MCPConfigManager

    mgr = MCPConfigManager()
    servers = mgr.servers

    if is_json_mode():
        print_json(
            [
                {
                    "name": s.name,
                    "transport": s.transport,
                    "command": s.command,
                    "url": s.url,
                }
                for s in servers
            ]
        )
        return

    if not servers:
        rprint("[dim]No MCP servers configured.[/dim]")
        rprint("[dim]Add one with: [bold]pretorin agent mcp-add <name> stdio <command>[/bold][/dim]")
        return

    table = Table(title="MCP Servers", show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Transport")
    table.add_column("Command / URL")

    for s in servers:
        endpoint = s.url if s.transport == "http" else f"{s.command} {' '.join(s.args)}"
        table.add_row(s.name, s.transport, endpoint)

    console.print(table)


@app.command("mcp-add")
def mcp_add(
    name: str = typer.Argument(..., help="Server name"),
    transport: str = typer.Argument(..., help="Transport: stdio or http"),
    command_or_url: str = typer.Argument(..., help="Command (stdio) or URL (http)"),
    args: list[str] | None = typer.Option(None, "--arg", "-a", help="Additional args for stdio"),
    scope: str = typer.Option("project", "--scope", help="Config scope: project or global"),
) -> None:
    """Add an MCP server configuration.

    Examples:
        pretorin agent mcp-add github stdio uvx --arg mcp-server-github
        pretorin agent mcp-add aws http https://mcp.example.com/aws
    """
    from pretorin.agent.mcp_config import MCPConfigManager, MCPServerConfig

    config = MCPServerConfig(
        name=name,
        transport=transport,
        command=command_or_url if transport == "stdio" else None,
        args=args or [],
        url=command_or_url if transport == "http" else None,
    )

    try:
        config.validate()
    except ValueError as e:
        rprint(f"[red]{e}[/red]")
        raise typer.Exit(1)

    mgr = MCPConfigManager()
    mgr.add_server(config, scope=scope)
    rprint(f"[#95D7E0]Added MCP server:[/#95D7E0] {name} ({transport})")


@app.command("mcp-remove")
def mcp_remove(
    name: str = typer.Argument(..., help="Server name to remove"),
) -> None:
    """Remove an MCP server configuration."""
    from pretorin.agent.mcp_config import MCPConfigManager

    mgr = MCPConfigManager()
    if mgr.remove_server(name):
        rprint(f"[#95D7E0]Removed MCP server:[/#95D7E0] {name}")
    else:
        rprint(f"[yellow]Server not found: {name}[/yellow]")
