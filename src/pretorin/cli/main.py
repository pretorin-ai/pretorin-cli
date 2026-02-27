"""Main CLI application setup for Pretorin."""

import json

import typer
from rich import print as rprint
from rich.console import Console

from pretorin import __version__
from pretorin.cli.agent import app as agent_app
from pretorin.cli.auth import app as auth_app
from pretorin.cli.commands import app as frameworks_app
from pretorin.cli.config import app as config_app
from pretorin.cli.context import app as context_app
from pretorin.cli.evidence import app as evidence_app
from pretorin.cli.harness import app as harness_app
from pretorin.cli.monitoring import app as monitoring_app
from pretorin.cli.narrative import app as narrative_app
from pretorin.cli.output import set_json_mode
from pretorin.cli.review import app as review_app

console = Console()

# Rome-bot expressions (for inline use)
ROMEBOT_HAPPY = "[#EAB536]\\[°◡°]/[/#EAB536]"
ROMEBOT_THINKING = "[#EAB536][°~°][/#EAB536]"
ROMEBOT_SAD = "[#EAB536][°︵°][/#EAB536]"

BANNER = """
[#FF9010]╔═══════════════════════════════════════════════════════════╗[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536] ∫[/#EAB536]                                                      [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536][°□°][/#EAB536]  [bold #FF9010]PRETORIN[/bold #FF9010]                                       [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]         [dim]Compliance Platform CLI[/dim]                         [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]                                                           [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]         [#EAB536]Making compliance the best part of your day.[/#EAB536]   [#FF9010]║[/#FF9010]
[#FF9010]╚═══════════════════════════════════════════════════════════╝[/#FF9010]
"""


def show_banner(check_updates: bool = True) -> None:
    """Display the branded welcome banner."""
    from pretorin.cli.version_check import get_update_message

    rprint(BANNER)
    rprint(f"  [dim]v{__version__}[/dim]\n")

    # Show update message if available
    if check_updates:
        update_msg = get_update_message()
        if update_msg:
            rprint(update_msg)
            rprint()


app = typer.Typer(
    name="pretorin",
    help="Access compliance frameworks, control families, and control details.",
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON (for scripting and AI agents)"),
) -> None:
    """CLI for the Pretorin Compliance Platform.

    Making compliance the best part of your day.
    """
    if json_output:
        set_json_mode(True)

    # Show banner and help when no subcommand is provided
    if ctx.invoked_subcommand is None:
        if json_output:
            print(json.dumps({"version": __version__}))
        else:
            show_banner()
            # Show the help text after the banner
            rprint(ctx.get_help())


# Add sub-command groups
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(context_app, name="context", help="Manage active system/framework context")
app.add_typer(frameworks_app, name="frameworks", help="Browse compliance frameworks and controls")
app.add_typer(monitoring_app, name="monitoring", help="Monitoring events and compliance tracking")
app.add_typer(evidence_app, name="evidence", help="Local evidence management and platform sync")
app.add_typer(narrative_app, name="narrative", help="Narrative management")
app.add_typer(review_app, name="review", help="Review local artifacts against compliance controls")
app.add_typer(agent_app, name="agent", help="Autonomous compliance agent")
app.add_typer(harness_app, name="harness", help="AI harness wrapper with Pretorin policy defaults")

# Add auth commands directly to root
for command in auth_app.registered_commands:
    app.registered_commands.append(command)


@app.command()
def version() -> None:
    """Show the CLI version."""
    from rich import print as rprint

    from pretorin.cli.version_check import get_update_message

    rprint(f"[#FF9010]pretorin[/#FF9010] version {__version__}")

    # Check for updates
    update_msg = get_update_message()
    if update_msg:
        rprint()
        rprint(update_msg)


@app.command()
def update() -> None:
    """Update Pretorin CLI to the latest version."""
    import subprocess
    import sys

    from pretorin.cli.version_check import check_for_updates

    latest = check_for_updates()
    if not latest:
        rprint(f"[#95D7E0]✓[/#95D7E0] You're already on the latest version ({__version__})")
        return

    rprint(f"[#FF9010]→[/#FF9010] Updating to version [#EAB536]{latest}[/#EAB536]...")
    rprint()

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pretorin"],
            check=True,
        )
        rprint()
        rprint(f"[#95D7E0]✓[/#95D7E0] Updated to version {latest}")
    except subprocess.CalledProcessError:
        rprint()
        rprint("[#FF9010]→[/#FF9010] Update failed. Try running manually:")
        rprint("  [bold]pip install --upgrade pretorin[/bold]")
        raise typer.Exit(1)


@app.command("mcp-serve")
def mcp_serve() -> None:
    """Start the MCP server (stdio transport)."""
    from pretorin.mcp.server import run_server

    run_server()


if __name__ == "__main__":
    app()
