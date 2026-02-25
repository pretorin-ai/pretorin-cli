"""Monitoring commands for the Pretorin CLI."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pretorin.cli.output import is_json_mode

console = Console()

app = typer.Typer(
    name="monitoring",
    help="Monitoring events and compliance tracking.",
    no_args_is_help=True,
)

# Rome-bot expressions
ROMEBOT_ALERT = "[#EAB536][°!°][/#EAB536]"
ROMEBOT_WORKING = "[#EAB536][°~°][/#EAB536]"
ROMEBOT_DONE = "[#EAB536]\\[°◡°]/[/#EAB536]"

SEVERITY_COLORS = {
    "critical": "#FF4444",
    "high": "#FF9010",
    "medium": "#EAB536",
    "low": "#95D7E0",
    "info": "#888888",
}


@app.command("push")
def push(
    system: str = typer.Option(
        None,
        "--system", "-s",
        help="System name or ID. Auto-selects if only one system exists.",
    ),
    title: str = typer.Option(
        ...,
        "--title", "-t",
        help="Event title.",
    ),
    severity: str = typer.Option(
        "high",
        "--severity",
        help="Event severity: critical, high, medium, low, info.",
    ),
    control: str | None = typer.Option(
        None,
        "--control", "-c",
        help="Control ID (e.g., sc-7, ac-2).",
    ),
    description: str = typer.Option(
        "",
        "--description", "-d",
        help="Detailed event description.",
    ),
    event_type: str = typer.Option(
        "security_scan",
        "--event-type",
        help="Event type: security_scan, configuration_change, access_review, compliance_check.",
    ),
    update_control_status: bool = typer.Option(
        False,
        "--update-control-status",
        help="Also update the control status to 'in_progress'.",
    ),
) -> None:
    """Push a monitoring event to a system.

    Creates a new monitoring event and optionally updates the
    associated control's implementation status.
    """
    asyncio.run(_push_event(
        system=system,
        title=title,
        severity=severity,
        control=control,
        description=description,
        event_type=event_type,
        update_control_status=update_control_status,
    ))


async def _push_event(
    system: str | None,
    title: str,
    severity: str,
    control: str | None,
    description: str,
    event_type: str,
    update_control_status: bool,
) -> None:
    """Push a monitoring event to the API."""
    import json as json_mod

    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.models import MonitoringEventCreate

    severity = severity.lower()
    if severity not in SEVERITY_COLORS:
        rprint(f"[red]Invalid severity: {severity}. Must be one of: critical, high, medium, low, info[/red]")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' or 'pretorin config set api-key <key>' first.[/red]")
            raise typer.Exit(1)

        # Resolve system
        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_WORKING}  Connecting to Pretorin...\n")

        try:
            systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        if not systems:
            rprint("[red]No systems found. Create a system first.[/red]")
            raise typer.Exit(1)

        # Find the target system
        target = None
        if system is None:
            if len(systems) == 1:
                target = systems[0]
            else:
                rprint("[red]Multiple systems found. Use --system to specify one:[/red]")
                for s in systems:
                    rprint(f"  - {s['name']} ({s['id'][:8]}...)")
                raise typer.Exit(1)
        else:
            # Match by name (partial) or ID
            system_lower = system.lower()
            for s in systems:
                if s["id"] == system or s["name"].lower().startswith(system_lower):
                    target = s
                    break
            if target is None:
                rprint(f"[red]System not found: {system}[/red]")
                raise typer.Exit(1)

        system_id = target["id"]
        system_name = target["name"]

        if not is_json_mode():
            sev_color = SEVERITY_COLORS.get(severity, "#FF9010")
            rprint(
                f"  {ROMEBOT_ALERT}  Pushing [{sev_color}]{severity.upper()}"
                f"[/{sev_color}] event to [bold]{system_name}[/bold]\n"
            )

        # Create the event
        event_data = MonitoringEventCreate(
            event_type=event_type,
            title=title,
            description=description,
            severity=severity,
            control_id=control,
            event_data={"source": "pretorin-cli", "cli_version": "0.1.0"},
        )

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("Creating monitoring event...", total=None)
                result = await client.create_monitoring_event(system_id, event_data)
        except PretorianClientError as e:
            rprint(f"[red]Failed to create event: {e.message}[/red]")
            raise typer.Exit(1)

        event_id = result.get("id", "unknown")

        # Optionally update control status
        if update_control_status and control:
            try:
                with Progress(
                    SpinnerColumn(style="#EAB536"),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    disable=is_json_mode(),
                ) as progress:
                    progress.add_task(f"Updating {control.upper()} status to in_progress...", total=None)
                    await client.update_control_status(
                        system_id=system_id,
                        control_id=control,
                        status="in_progress",
                    )
            except PretorianClientError as e:
                rprint(f"[yellow]Warning: Failed to update control status: {e.message}[/yellow]")

        if is_json_mode():
            print(json_mod.dumps({
                "event_id": event_id,
                "system_id": system_id,
                "system_name": system_name,
                "title": title,
                "severity": severity,
                "control_id": control,
                "control_status_updated": update_control_status and control is not None,
            }))
        else:
            rprint()
            sev_color = SEVERITY_COLORS.get(severity, "#FF9010")
            panel_content = (
                f"  [bold]Event ID:[/bold]  {event_id[:8]}...\n"
                f"  [bold]System:[/bold]   {system_name}\n"
                f"  [bold]Severity:[/bold] [{sev_color}]{severity.upper()}[/{sev_color}]\n"
                f"  [bold]Title:[/bold]    {title}\n"
            )
            if control:
                panel_content += f"  [bold]Control:[/bold]  {control.upper()}\n"
            if update_control_status and control:
                panel_content += "  [bold]Status:[/bold]   Control updated to [yellow]in_progress[/yellow]\n"

            rprint(Panel(
                panel_content,
                title=f"{ROMEBOT_DONE}  Event Created",
                border_style="#95D7E0",
                padding=(1, 2),
            ))
