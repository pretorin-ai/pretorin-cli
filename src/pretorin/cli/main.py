"""Main CLI application setup for Pretorin."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Annotated

import typer
from rich import print as rprint
from rich.console import Console

from pretorin import __version__
from pretorin.cli.agent import app as agent_app
from pretorin.cli.auth import app as auth_app
from pretorin.cli.campaign import app as campaign_app
from pretorin.cli.cci import app as cci_app
from pretorin.cli.commands import app as frameworks_app
from pretorin.cli.config import app as config_app
from pretorin.cli.context import app as context_app
from pretorin.cli.control import app as control_app
from pretorin.cli.evidence import app as evidence_app
from pretorin.cli.harness import app as harness_app
from pretorin.cli.monitoring import app as monitoring_app
from pretorin.cli.narrative import app as narrative_app
from pretorin.cli.notes import app as notes_app
from pretorin.cli.output import set_json_mode
from pretorin.cli.policy import app as policy_app
from pretorin.cli.review import app as review_app
from pretorin.cli.scan import app as scan_app
from pretorin.cli.scope import app as scope_app
from pretorin.cli.skill import app as skill_app
from pretorin.cli.stig import app as stig_app
from pretorin.cli.vendor import app as vendor_app

console = Console()

BANNER = """
[#FF9010]╔═══════════════════════════════════════════════════════════╗[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536] ∫[/#EAB536]                                                      [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]   [#EAB536]\\[°□°][/#EAB536]  [bold #FF9010]PRETORIN[/bold #FF9010]  [dim]\\[BETA][/dim]                              [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]         [dim]Compliance Platform CLI[/dim]                         [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]                                                           [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]         [#EAB536]Making compliance the best part of your day.[/#EAB536]   [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]                                                           [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]  [dim]Platform features require a beta code. Browse frameworks[/dim]  [#FF9010]║[/#FF9010]
[#FF9010]║[/#FF9010]  [dim]and controls freely. Sign up: https://pretorin.com[/dim]       [#FF9010]║[/#FF9010]
[#FF9010]╚═══════════════════════════════════════════════════════════╝[/#FF9010]
"""


def show_banner(check_updates: bool = True) -> None:
    """Display the branded welcome banner."""
    rprint(BANNER)
    rprint(f"  [dim]v{__version__}[/dim]\n")

    # Show update message if available
    if check_updates:
        _maybe_print_update_notice()


def _should_show_update_notice(
    *,
    json_output: bool = False,
    invoked_subcommand: str | None = None,
) -> bool:
    """Return True when passive update notices should be shown."""
    if json_output:
        return False
    if invoked_subcommand in {"update", "mcp-serve"}:
        return False
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


def _maybe_print_update_notice(
    *,
    json_output: bool = False,
    invoked_subcommand: str | None = None,
) -> None:
    """Print a passive update notice when appropriate."""
    if not _should_show_update_notice(
        json_output=json_output,
        invoked_subcommand=invoked_subcommand,
    ):
        return

    from pretorin.cli.version_check import get_update_message

    update_msg = get_update_message()
    if update_msg:
        rprint(update_msg)
        rprint()


def _version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        rprint(f"[#FF9010]pretorin[/#FF9010] version {__version__}")
        _maybe_print_update_notice()
        raise typer.Exit()


app = typer.Typer(
    name="pretorin",
    help="Access compliance frameworks, control families, and control details.",
    no_args_is_help=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    json_output: bool = typer.Option(False, "--json", help="Output results as JSON (for scripting and AI agents)"),
    _version: bool = typer.Option(
        False,
        "--version",
        "-V",
        help="Show version and exit.",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """CLI for the Pretorin Compliance Platform.

    Making compliance the best part of your day.
    """
    # Configure stdlib logging: default WARNING, overridable via PRETORIN_LOG_LEVEL
    log_level = os.environ.get("PRETORIN_LOG_LEVEL", "WARNING").upper()
    logging.basicConfig(
        stream=sys.stderr,
        level=getattr(logging, log_level, logging.WARNING),
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

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
        return

    _maybe_print_update_notice(
        json_output=json_output,
        invoked_subcommand=ctx.invoked_subcommand,
    )


# Add sub-command groups
app.add_typer(config_app, name="config", help="Manage configuration")
app.add_typer(campaign_app, name="campaign", help="Workflow-aligned bulk campaign runs")
app.add_typer(control_app, name="control", help="Control implementation management")
app.add_typer(context_app, name="context", help="Manage active system/framework context")
app.add_typer(frameworks_app, name="frameworks", help="Browse compliance frameworks and controls")
app.add_typer(monitoring_app, name="monitoring", help="Monitoring events and compliance tracking")
app.add_typer(evidence_app, name="evidence", help="Local evidence management and platform sync")
app.add_typer(narrative_app, name="narrative", help="Local narrative management and platform sync.")
app.add_typer(notes_app, name="notes", help="Local note management and platform sync.")
app.add_typer(policy_app, name="policy", help="Stateful org-policy questionnaire workflows")
app.add_typer(review_app, name="review", help="Review local artifacts against compliance controls")
app.add_typer(scope_app, name="scope", help="Stateful scope questionnaire workflows")
app.add_typer(agent_app, name="agent", help="Autonomous compliance agent")
app.add_typer(skill_app, name="skill", help="Install/manage the Pretorin skill for AI agents")
app.add_typer(vendor_app, name="vendor", help="Vendor management and evidence linking")
app.add_typer(stig_app, name="stig", help="Browse STIG benchmarks, rules, and applicability")
app.add_typer(cci_app, name="cci", help="Browse CCIs and the full traceability chain")
app.add_typer(scan_app, name="scan", help="Run STIG compliance scans and view results")
app.add_typer(harness_app, name="harness", help="[Deprecated] AI harness wrapper")

# Add auth commands directly to root
for command in auth_app.registered_commands:
    app.registered_commands.append(command)


@app.command()
def version() -> None:
    """Show the CLI version."""
    rprint(f"[#FF9010]pretorin[/#FF9010] version {__version__}")
    _maybe_print_update_notice()


@app.command()
def update(
    version: Annotated[
        str | None,
        typer.Argument(help="Target version to install (e.g. 0.15.1). Defaults to latest."),
    ] = None,
) -> None:
    """Update Pretorin CLI to the latest version, or a specific version."""
    import subprocess
    import sys

    from pretorin.cli.version_check import _fetch_latest_version, _parse_version

    current = __version__

    if version:
        target = version
        rprint(f"[#FF9010]→[/#FF9010] Installing pretorin {target} (current: [#EAB536]{current}[/#EAB536])...")
        pip_spec = f"pretorin=={target}"
    else:
        rprint(f"[#FF9010]→[/#FF9010] Checking for updates (current: [#EAB536]{current}[/#EAB536])...")
        latest = _fetch_latest_version()
        if not latest:
            rprint("[#FF9010]→[/#FF9010] Could not reach PyPI. Try again later or run manually:")
            rprint("  [bold]pip install --upgrade pretorin[/bold]")
            raise typer.Exit(1)

        if _parse_version(latest) <= _parse_version(current):
            rprint(f"[#95D7E0]✓[/#95D7E0] Already on the latest version ({current})")
            return

        target = latest
        pip_spec = "pretorin"

    rprint(f"[#FF9010]→[/#FF9010] Upgrading pretorin {current} → {target}...")
    rprint()

    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", pip_spec],
            check=True,
        )
    except subprocess.CalledProcessError:
        rprint()
        rprint("[#FF9010]→[/#FF9010] pip failed. Try running manually:")
        rprint(f"  [bold]pip install {pip_spec}[/bold]")
        raise typer.Exit(1)

    # Verify the upgrade actually took effect by reading the installed version
    try:
        result = subprocess.run(
            [sys.executable, "-c", "from pretorin import __version__; print(__version__)"],
            capture_output=True,
            text=True,
            check=True,
        )
        installed = result.stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        installed = None

    rprint()
    if installed and _parse_version(installed) >= _parse_version(target):
        rprint(f"[#95D7E0]✓[/#95D7E0] Updated to version {installed}")
    elif installed and installed == current:
        rprint(f"[#FF9010]⚠[/#FF9010] pip ran but version is still {current}.")
        rprint("  This can happen with pipx or uv-managed installs. Try:")
        rprint("  [bold]pipx upgrade pretorin[/bold]  or  [bold]uv tool upgrade pretorin[/bold]")
    else:
        rprint("[#95D7E0]✓[/#95D7E0] Update complete.")


@app.command("mcp-serve")
def mcp_serve() -> None:
    """Start the MCP server (stdio transport)."""
    from pretorin.mcp.server import run_server

    run_server()


if __name__ == "__main__":
    app()
