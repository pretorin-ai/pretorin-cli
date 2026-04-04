"""STIG browsing and applicability commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

app = typer.Typer(
    name="stig",
    help="Browse STIG benchmarks, rules, and applicability.",
    no_args_is_help=True,
)


@app.command("list")
def stig_list(
    technology_area: str | None = typer.Option(None, "--technology-area", "-t", help="Filter by technology area (OS, Container, Database, etc.)"),
    product: str | None = typer.Option(None, "--product", "-p", help="Filter by product name (partial match)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max results"),
) -> None:
    """List all STIG benchmarks."""
    asyncio.run(_list_stigs(technology_area, product, limit))


@app.command("show")
def stig_show(
    stig_id: str = typer.Argument(..., help="STIG benchmark ID (e.g., RHEL_9_STIG)"),
) -> None:
    """Show STIG benchmark detail with severity breakdown."""
    asyncio.run(_show_stig(stig_id))


@app.command("rules")
def stig_rules(
    stig_id: str = typer.Argument(..., help="STIG benchmark ID"),
    severity: str | None = typer.Option(None, "--severity", "-s", help="Filter: cat_i, cat_ii, cat_iii"),
    cci_id: str | None = typer.Option(None, "--cci", help="Filter by CCI ID"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max results"),
) -> None:
    """List rules for a STIG benchmark."""
    asyncio.run(_list_rules(stig_id, severity, cci_id, limit))


@app.command("applicable")
def stig_applicable(
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID"),
) -> None:
    """Show applicable STIGs for the active system."""
    asyncio.run(_applicable(system))


@app.command("infer")
def stig_infer(
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID"),
) -> None:
    """AI-infer applicable STIGs based on system profile."""
    asyncio.run(_infer(system))


async def _list_stigs(
    technology_area: str | None, product: str | None, limit: int
) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            data = await client.list_stigs(
                technology_area=technology_area, product=product, limit=limit
            )
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    items = data.get("items", [])

    if is_json_mode():
        print_json(data)
        return

    if not items:
        rprint("[dim]No STIG benchmarks found.[/dim]")
        return

    table = Table(title=f"STIG Benchmarks ({data.get('total', len(items))} total)")
    table.add_column("STIG ID", style="bold")
    table.add_column("Title")
    table.add_column("Area", style="cyan")
    table.add_column("Rules", justify="right")
    table.add_column("CAT I", justify="right", style="red")
    table.add_column("CAT II", justify="right", style="yellow")
    table.add_column("CAT III", justify="right", style="green")

    for item in items:
        sc = item.get("severity_counts", {})
        table.add_row(
            item["stig_id"],
            item.get("title", "")[:50],
            item.get("technology_area", ""),
            str(item.get("rule_count", 0)),
            str(sc.get("cat_i", 0)),
            str(sc.get("cat_ii", 0)),
            str(sc.get("cat_iii", 0)),
        )

    rprint(table)


async def _show_stig(stig_id: str) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            data = await client.list_stigs()
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    # Find matching STIG
    items = data.get("items", [])
    match = next((i for i in items if i["stig_id"] == stig_id), None)

    if is_json_mode():
        print_json(match or {"error": "not found"})
        return

    if not match:
        rprint(f"[red]STIG {stig_id} not found[/red]")
        raise typer.Exit(1)

    sc = match.get("severity_counts", {})
    panel_content = (
        f"[bold]{match['title']}[/bold]\n\n"
        f"STIG ID:     {match['stig_id']}\n"
        f"Version:     {match.get('version', 'N/A')}\n"
        f"Area:        {match.get('technology_area', 'N/A')}\n"
        f"Product:     {match.get('product', 'N/A')}\n"
        f"Vendor:      {match.get('vendor', 'N/A')}\n\n"
        f"Total Rules: {match.get('rule_count', 0)}\n"
        f"  [red]CAT I:   {sc.get('cat_i', 0)}[/red]\n"
        f"  [yellow]CAT II:  {sc.get('cat_ii', 0)}[/yellow]\n"
        f"  [green]CAT III: {sc.get('cat_iii', 0)}[/green]"
    )
    rprint(Panel(panel_content, title="STIG Benchmark", border_style="#FF9010"))


async def _list_rules(
    stig_id: str, severity: str | None, cci_id: str | None, limit: int
) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            data = await client.list_stig_rules(
                stig_id, severity=severity, cci_id=cci_id, limit=limit
            )
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    items = data.get("items", [])

    if is_json_mode():
        print_json(data)
        return

    if not items:
        rprint(f"[dim]No rules found for {stig_id}.[/dim]")
        return

    table = Table(title=f"{stig_id} Rules ({data.get('total', len(items))} total)")
    table.add_column("Rule ID", style="bold")
    table.add_column("V-ID")
    table.add_column("Severity")
    table.add_column("Title")
    table.add_column("CCIs", style="dim")

    severity_styles = {"cat_i": "red bold", "cat_ii": "yellow", "cat_iii": "green"}

    for item in items:
        sev = item.get("severity", "")
        table.add_row(
            item.get("stig_ref", item.get("rule_id", ""))[:25],
            item.get("group_id", ""),
            f"[{severity_styles.get(sev, '')}]{sev.upper().replace('_', ' ')}[/{severity_styles.get(sev, '')}]" if sev else "",
            (item.get("title", "") or "")[:50],
            ", ".join(item.get("cci_ids", [])[:3]),
        )

    rprint(table)


async def _applicable(system: str | None) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, _ = await resolve_execution_context(client, system=system)
            data = await client.get_stig_applicability(system_id)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    items = data.get("applicability", [])

    if is_json_mode():
        print_json(data)
        return

    if not items:
        rprint("[dim]No STIG applicability data for this system.[/dim]")
        rprint("[dim]Run 'pretorin stig infer' to detect applicable STIGs.[/dim]")
        return

    table = Table(title="STIG Applicability")
    table.add_column("STIG", style="bold")
    table.add_column("Name")
    table.add_column("Source")
    table.add_column("Confidence", justify="right")
    table.add_column("Status")

    for item in items:
        status = "✓ Confirmed" if item["is_confirmed"] else ("✗ Excluded" if item["is_excluded"] else "Pending")
        style = "green" if item["is_confirmed"] else ("red" if item["is_excluded"] else "yellow")
        conf = f"{item['confidence']:.0%}" if item.get("confidence") is not None else ""
        table.add_row(
            item["stig_id"],
            item.get("stig_name", "")[:40],
            item["source"],
            conf,
            f"[{style}]{status}[/{style}]",
        )

    rprint(table)


async def _infer(system: str | None) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, _ = await resolve_execution_context(client, system=system)
            data = await client.infer_stigs(system_id)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    if is_json_mode():
        print_json(data)
        return

    inferred = data.get("inferred", [])
    if not inferred:
        rprint("[dim]No applicable STIGs inferred for this system.[/dim]")
        rprint("[dim]This may mean the system profile lacks tech stack details.[/dim]")
        return

    rprint(Panel(
        f"System: {data.get('system_name', data.get('system_id', ''))}\n"
        f"Inferred: {len(inferred)} applicable STIGs",
        title="STIG Inference Results",
        border_style="#FF9010",
    ))

    table = Table()
    table.add_column("STIG", style="bold")
    table.add_column("Name")
    table.add_column("Area", style="cyan")
    table.add_column("Confidence", justify="right")
    table.add_column("Rationale", style="dim")

    for item in inferred:
        conf = item.get("confidence", 0)
        conf_style = "green" if conf >= 0.7 else ("yellow" if conf >= 0.4 else "dim")
        table.add_row(
            item["stig_id"],
            item.get("stig_name", "")[:35],
            item.get("technology_area", ""),
            f"[{conf_style}]{conf:.0%}[/{conf_style}]",
            item.get("rationale", "")[:50],
        )

    rprint(table)
