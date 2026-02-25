"""Agent CLI commands for Pretorin.

Requires optional `agent` dependency group: `pip install pretorin[agent]`
"""

from __future__ import annotations

import asyncio

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


@app.command("run")
def agent_run(
    message: str = typer.Argument(..., help="Task or question for the agent"),
    skill: str | None = typer.Option(
        None, "--skill", "-s",
        help="Skill to use: gap-analysis, narrative-generation, evidence-collection, security-review",
    ),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model to use"),
    max_turns: int = typer.Option(15, "--max-turns", help="Maximum agent turns"),
    no_mcp: bool = typer.Option(False, "--no-mcp", help="Disable external MCP servers"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable streaming output"),
) -> None:
    """Run the compliance agent with a message or task.

    Examples:
        pretorin agent run "List my systems and check AC-2 compliance"
        pretorin agent run "Generate narratives for all AC controls" --skill narrative-generation
        pretorin agent run "Review security posture" --skill security-review --model gpt-4o-mini
    """
    _check_agent_deps()
    asyncio.run(_run_agent(message, skill, model, max_turns, no_mcp, not no_stream))


async def _run_agent(
    message: str,
    skill: str | None,
    model: str,
    max_turns: int,
    no_mcp: bool,
    stream: bool,
) -> None:
    """Execute the agent."""
    from pretorin.agent.runner import ComplianceAgent
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    config = Config()

    # Resolve OpenAI settings
    import os
    api_key = os.environ.get("OPENAI_API_KEY", config.get("openai_api_key"))
    base_url = os.environ.get("OPENAI_BASE_URL", config.get("openai_base_url"))
    model = os.environ.get("OPENAI_MODEL", model)

    if not api_key:
        rprint("[red]OPENAI_API_KEY is required for agent features.[/red]")
        rprint("[dim]Set it with: [bold]export OPENAI_API_KEY=sk-...[/bold][/dim]")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' first.[/red]")
            raise typer.Exit(1)

        # Load MCP servers
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
                pass  # MCP servers are optional

        if not is_json_mode():
            skill_label = f" with skill [bold]{skill}[/bold]" if skill else ""
            rprint(f"  {ROMEBOT_AGENT}  Starting agent{skill_label} (model: {model})\n")

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
    rprint("\n[dim]Use with: pretorin agent run \"your task\" --skill <name>[/dim]")


@app.command("mcp-list")
def mcp_list() -> None:
    """List configured MCP servers."""
    from pretorin.agent.mcp_config import MCPConfigManager

    mgr = MCPConfigManager()
    servers = mgr.servers

    if is_json_mode():
        print_json([{
            "name": s.name, "transport": s.transport,
            "command": s.command, "url": s.url,
        } for s in servers])
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
