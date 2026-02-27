"""Context commands for the Pretorin CLI."""

from __future__ import annotations

import asyncio
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="context",
    help="Manage active system/framework context.",
    no_args_is_help=True,
)

ROMEBOT_HAPPY = "[#EAB536]\\[°◡°]/[/#EAB536]"
ROMEBOT_THINKING = "[#EAB536][°~°][/#EAB536]"
ROMEBOT_SAD = "[#EAB536][°︵°][/#EAB536]"


def resolve_context(
    system: str | None = None,
    framework: str | None = None,
) -> tuple[str, str]:
    """Resolve system_id and framework_id from flags or active context.

    Priority: explicit flags > stored context > error
    """
    from pretorin.client.config import Config

    config = Config()

    system_id = system or config.get("active_system_id")
    framework_id = framework or config.get("active_framework_id")

    if not system_id or not framework_id:
        rprint("[red]No system/framework context set.[/red]")
        rprint("Run [bold]pretorin context set[/bold] or use --system and --framework flags.")
        raise typer.Exit(1)

    return system_id, framework_id


@app.command("list")
def context_list() -> None:
    """List all systems and their compliance status."""
    asyncio.run(_context_list())


async def _context_list() -> None:
    """Fetch systems and compliance status from the API."""
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' or 'pretorin config set api-key <key>' first.[/red]")
            raise typer.Exit(1)

        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_THINKING}  Fetching systems...\n")

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("Loading systems and compliance data...", total=None)
                systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        if not systems:
            rprint(f"  {ROMEBOT_SAD}  No systems found. Create a system in the Pretorin platform first.")
            raise typer.Exit(0)

        # Gather compliance status for each system
        rows: list[dict[str, Any]] = []
        for sys in systems:
            system_id = sys["id"]
            system_name = sys["name"]
            try:
                status = await client.get_system_compliance_status(system_id)
                frameworks = status.get("frameworks", [])
                if frameworks:
                    for fw in frameworks:
                        rows.append(
                            {
                                "system_name": system_name,
                                "system_id": system_id,
                                "framework_id": fw.get("framework_id", "unknown"),
                                "progress": fw.get("progress", 0),
                                "status": fw.get("status", "not_started"),
                            }
                        )
                else:
                    rows.append(
                        {
                            "system_name": system_name,
                            "system_id": system_id,
                            "framework_id": "-",
                            "progress": 0,
                            "status": "no frameworks",
                        }
                    )
            except PretorianClientError:
                rows.append(
                    {
                        "system_name": system_name,
                        "system_id": system_id,
                        "framework_id": "-",
                        "progress": 0,
                        "status": "error fetching status",
                    }
                )

        if is_json_mode():
            print_json(rows)
            return

        # Rich table output
        table = Table(
            title=f"{ROMEBOT_HAPPY}  Systems & Compliance Status",
            show_header=True,
            header_style="bold #FF9010",
        )
        table.add_column("System Name", style="bold")
        table.add_column("Framework ID")
        table.add_column("Progress %", justify="right")
        table.add_column("Status")

        status_colors = {
            "not_started": "#888888",
            "in_progress": "#EAB536",
            "implemented": "#95D7E0",
            "complete": "#4CAF50",
            "no frameworks": "#888888",
            "error fetching status": "#FF4444",
        }

        for row in rows:
            progress_str = f"{row['progress']}%" if row["framework_id"] != "-" else "-"
            status_color = status_colors.get(row["status"], "#888888")
            table.add_row(
                row["system_name"],
                row["framework_id"],
                progress_str,
                f"[{status_color}]{row['status']}[/{status_color}]",
            )

        rprint()
        rprint(table)
        rprint()


@app.command("set")
def context_set(
    system: str | None = typer.Option(
        None,
        "--system",
        "-s",
        help="System name or ID.",
    ),
    framework: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help="Framework ID (e.g., fedramp-moderate).",
    ),
) -> None:
    """Set the active system and framework context.

    If no flags are provided, runs in interactive mode.
    """
    asyncio.run(_context_set(system=system, framework=framework))


async def _context_set(
    system: str | None,
    framework: str | None,
) -> None:
    """Set context interactively or from flags."""
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' or 'pretorin config set api-key <key>' first.[/red]")
            raise typer.Exit(1)

        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_THINKING}  Connecting to Pretorin...\n")

        try:
            systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        if not systems:
            rprint(f"  {ROMEBOT_SAD}  No systems found. Create a system in the Pretorin platform first.")
            raise typer.Exit(1)

        # --- Resolve system ---
        target_system = None

        if system is not None:
            # Match by name (partial, case-insensitive) or ID
            system_lower = system.lower()
            for s in systems:
                if s["id"] == system or s["name"].lower().startswith(system_lower):
                    target_system = s
                    break
            if target_system is None:
                rprint(f"[red]System not found: {system}[/red]")
                raise typer.Exit(1)
        else:
            # Interactive mode
            rprint("  [bold]Available systems:[/bold]\n")
            for i, s in enumerate(systems, 1):
                rprint(f"  {i}. {s['name']} ({s['id'][:8]}...)")

            rprint()
            choice = input("  Select system number: ")
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(systems):
                    raise ValueError
                target_system = systems[idx]
            except (ValueError, IndexError):
                rprint("[red]Invalid selection.[/red]")
                raise typer.Exit(1)

        system_id = target_system["id"]
        system_name = target_system["name"]

        # --- Resolve framework ---
        target_framework_id = None

        if framework is not None:
            # Validate framework is associated with this system
            try:
                status = await client.get_system_compliance_status(system_id)
                fw_ids = [fw.get("framework_id") for fw in status.get("frameworks", [])]
            except PretorianClientError:
                fw_ids = []

            if fw_ids and framework not in fw_ids:
                rprint(f"[red]Framework '{framework}' is not associated with system '{system_name}'.[/red]")
                rprint(f"  Available frameworks: {', '.join(fw_ids)}")
                raise typer.Exit(1)

            target_framework_id = framework
        else:
            # Interactive: list frameworks for the selected system
            try:
                status = await client.get_system_compliance_status(system_id)
                fw_list = status.get("frameworks", [])
            except PretorianClientError:
                fw_list = []

            if not fw_list:
                rprint(f"\n  {ROMEBOT_SAD}  No frameworks associated with system '{system_name}'.")
                rprint("  Add a framework to the system in the Pretorin platform first.")
                raise typer.Exit(1)

            rprint(f"\n  [bold]Frameworks for {system_name}:[/bold]\n")
            for i, fw in enumerate(fw_list, 1):
                fw_id = fw.get("framework_id", "unknown")
                fw_progress = fw.get("progress", 0)
                rprint(f"  {i}. {fw_id} ({fw_progress}% complete)")

            rprint()
            choice = input("  Select framework number: ")
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(fw_list):
                    raise ValueError
                target_framework_id = fw_list[idx].get("framework_id")
            except (ValueError, IndexError):
                rprint("[red]Invalid selection.[/red]")
                raise typer.Exit(1)

        # --- Save context ---
        config = Config()
        config.set("active_system_id", system_id)
        config.set("active_framework_id", target_framework_id)

        if is_json_mode():
            print_json(
                {
                    "system_id": system_id,
                    "system_name": system_name,
                    "framework_id": target_framework_id,
                }
            )
        else:
            rprint()
            rprint(
                Panel(
                    f"  [bold]System:[/bold]    {system_name} ({system_id[:8]}...)\n"
                    f"  [bold]Framework:[/bold] {target_framework_id}",
                    title=f"{ROMEBOT_HAPPY}  Context Set",
                    border_style="#95D7E0",
                    padding=(1, 2),
                )
            )


@app.command("show")
def context_show() -> None:
    """Show the currently active system and framework context."""
    asyncio.run(_context_show())


async def _context_show() -> None:
    """Display the current context with live status."""
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    config = Config()
    system_id = config.get("active_system_id")
    framework_id = config.get("active_framework_id")

    if not system_id or not framework_id:
        if is_json_mode():
            print_json({"active_system_id": None, "active_framework_id": None})
        else:
            rprint(f"\n  {ROMEBOT_SAD}  No active context set.\n")
            rprint("  Run [bold]pretorin context set[/bold] to select a system and framework.")
        return

    async with PretorianClient() as client:
        if not client.is_configured:
            # Show stored context even without API access
            if is_json_mode():
                print_json({"active_system_id": system_id, "active_framework_id": framework_id})
            else:
                rprint(
                    Panel(
                        f"  [bold]System ID:[/bold]  {system_id}\n"
                        f"  [bold]Framework:[/bold]  {framework_id}\n\n"
                        "  [dim]Not logged in — showing stored context only.[/dim]",
                        title=f"{ROMEBOT_THINKING}  Active Context",
                        border_style="#EAB536",
                        padding=(1, 2),
                    )
                )
            return

        # Fetch live info
        system_name = system_id
        progress = 0
        status = "unknown"

        try:
            sys_detail = await client.get_system(system_id)
            system_name = sys_detail.name
        except PretorianClientError:
            pass

        try:
            compliance = await client.get_system_compliance_status(system_id)
            for fw in compliance.get("frameworks", []):
                if fw.get("framework_id") == framework_id:
                    progress = fw.get("progress", 0)
                    status = fw.get("status", "unknown")
                    break
        except PretorianClientError:
            pass

        if is_json_mode():
            print_json(
                {
                    "active_system_id": system_id,
                    "active_system_name": system_name,
                    "active_framework_id": framework_id,
                    "progress": progress,
                    "status": status,
                }
            )
        else:
            rprint()
            rprint(
                Panel(
                    f"  [bold]System:[/bold]    {system_name} ({system_id[:8]}...)\n"
                    f"  [bold]Framework:[/bold] {framework_id}\n"
                    f"  [bold]Progress:[/bold]  {progress}%\n"
                    f"  [bold]Status:[/bold]    {status}",
                    title=f"{ROMEBOT_HAPPY}  Active Context",
                    border_style="#95D7E0",
                    padding=(1, 2),
                )
            )


@app.command("clear")
def context_clear() -> None:
    """Clear the active system and framework context."""
    from pretorin.client.config import Config

    config = Config()
    config.delete("active_system_id")
    config.delete("active_framework_id")

    if is_json_mode():
        print_json({"cleared": True})
    else:
        rprint(f"\n  {ROMEBOT_HAPPY}  Context cleared.\n")
        rprint("  Run [bold]pretorin context set[/bold] to select a new system and framework.")
