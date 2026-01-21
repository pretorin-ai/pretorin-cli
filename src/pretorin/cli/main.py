"""Main CLI application setup for Pretorin."""

import typer

from pretorin import __version__
from pretorin.cli.auth import app as auth_app
from pretorin.cli.config import app as config_app
from pretorin.cli.commands import app as frameworks_app

app = typer.Typer(
    name="pretorin",
    help="CLI for the Pretorin Compliance Platform API.\n\nAccess compliance frameworks, control families, and control details.",
    no_args_is_help=True,
)

# Add sub-command groups
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(frameworks_app, name="frameworks", help="Browse compliance frameworks and controls")

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


if __name__ == "__main__":
    app()
