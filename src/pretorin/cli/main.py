"""Main CLI application setup for Pretorin."""

import typer

from pretorin import __version__
from pretorin.cli.auth import app as auth_app
from pretorin.cli.config import app as config_app
from pretorin.cli.commands import app as commands_app

app = typer.Typer(
    name="pretorin",
    help="CLI and MCP server for Pretorin Compliance API",
    no_args_is_help=True,
)

# Add sub-command groups
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(commands_app, name="reports", help="Manage compliance reports")

# Add auth commands directly to root
for command in auth_app.registered_commands:
    app.registered_commands.append(command)


@app.command()
def version() -> None:
    """Show the CLI version."""
    from rich import print as rprint

    rprint(f"pretorin version {__version__}")


@app.command("mcp-serve")
def mcp_serve() -> None:
    """Start the MCP server (stdio transport)."""
    from pretorin.mcp.server import run_server

    run_server()


@app.command()
def check(
    file: str = typer.Argument(..., help="Path to the file to check"),
    rules: list[str] | None = typer.Option(None, "--rule", "-r", help="Specific rules to check"),
) -> None:
    """Run a compliance check on a document."""
    import asyncio
    from pathlib import Path

    from rich import print as rprint
    from rich.console import Console
    from rich.table import Table

    from pretorin.client import PretorianClient
    from pretorin.client.api import AuthenticationError, PretorianClientError

    console = Console()
    file_path = Path(file)

    if not file_path.exists():
        rprint(f"[red]Error:[/red] File not found: {file}")
        raise typer.Exit(1)

    async def run_check() -> None:
        async with PretorianClient() as client:
            if not client.is_configured:
                rprint("[red]Error:[/red] Not logged in. Run 'pretorin login' first.")
                raise typer.Exit(1)

            try:
                with console.status(f"Checking {file_path.name}..."):
                    result = await client.check_file(file_path, rules=rules)

                rprint(f"\n[bold]Compliance Check Results[/bold] - {result.file_name or file_path.name}")
                rprint(f"Status: [{'green' if result.status.value == 'completed' else 'yellow'}]{result.status.value}[/]")
                rprint(f"Check ID: {result.id}")

                if result.issues:
                    rprint(f"\n[bold red]Found {len(result.issues)} issue(s):[/bold red]\n")

                    table = Table(show_header=True, header_style="bold")
                    table.add_column("Severity", style="bold")
                    table.add_column("Rule")
                    table.add_column("Message")
                    table.add_column("Location")

                    severity_colors = {
                        "critical": "red",
                        "high": "red",
                        "medium": "yellow",
                        "low": "blue",
                    }

                    for issue in result.issues:
                        color = severity_colors.get(issue.severity.value, "white")
                        table.add_row(
                            f"[{color}]{issue.severity.value.upper()}[/{color}]",
                            issue.rule_name,
                            issue.message,
                            issue.location or "-",
                        )

                    console.print(table)
                else:
                    rprint("\n[green]No compliance issues found.[/green]")

            except AuthenticationError as e:
                rprint(f"[red]Authentication error:[/red] {e.message}")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[red]Error:[/red] {e.message}")
                raise typer.Exit(1)

    asyncio.run(run_check())


if __name__ == "__main__":
    app()
