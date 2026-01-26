"""Main CLI application setup for Pretorin."""

import typer
from rich import print as rprint
from rich.console import Console

from pretorin import __version__
from pretorin.cli.auth import app as auth_app
from pretorin.cli.config import app as config_app
from pretorin.cli.commands import app as frameworks_app

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
def main(ctx: typer.Context) -> None:
    """CLI for the Pretorin Compliance Platform.

    Making compliance the best part of your day.
    """
    # Show banner and help when no subcommand is provided
    if ctx.invoked_subcommand is None:
        show_banner()
        # Show the help text after the banner
        rprint(ctx.get_help())

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


@app.command("assess")
def assess() -> None:
    """Run compliance assessment for JMCP (Joint Mission Command Platform).

    Analyzes the Joint Mission Command Platform codebase for DoD RMF and
    NIST 800-53 compliance, scanning for evidence across key security controls
    and submitting artifacts to the Pretorin platform.
    """
    from pretorin.cli.demo import run_demo

    run_demo()


@app.command("analyze")
def analyze(
    framework_id: str = typer.Option(
        "fedramp-moderate",
        "--framework",
        "-f",
        help="Framework ID (e.g., fedramp-moderate, nist-800-53-r5)",
    ),
    controls: str = typer.Option(
        None,
        "--controls",
        "-c",
        help="Comma-separated control IDs (e.g., ac-2,au-2,ia-2). Defaults to all available.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to code directory to analyze",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save artifacts to local JSON file instead of API",
    ),
) -> None:
    """Start a compliance analysis session.

    This command prepares your environment for AI-assisted compliance analysis.
    It validates the framework and controls, then prints instructions for
    using the Pretorin MCP tools to analyze your code.
    """
    from pretorin.cli.commands import analyze as _analyze

    # Delegate to the full implementation in commands.py
    _analyze(
        framework_id=framework_id,
        controls=controls,
        path=path,
        output=output,
    )


if __name__ == "__main__":
    app()
