"""CCI (Control Correlation Identifier) browsing commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

from pretorin.cli.output import is_json_mode, print_json

app = typer.Typer(
    name="cci",
    help="Browse CCIs and the full traceability chain.",
    no_args_is_help=True,
)


@app.command("list")
def cci_list(
    control: str | None = typer.Option(None, "--control", "-c", help="Filter by NIST 800-53 control ID (e.g., ac-2)"),
    status: str | None = typer.Option(None, "--status", help="Filter by status (draft/published/deprecated)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Max results"),
) -> None:
    """List CCIs, optionally filtered by NIST 800-53 control."""
    asyncio.run(_list_ccis(control, status, limit))


@app.command("show")
def cci_show(
    cci_id: str = typer.Argument(..., help="CCI ID (e.g., CCI-000015)"),
) -> None:
    """Show CCI detail with linked SRGs and STIG rules."""
    asyncio.run(_show_cci(cci_id))


@app.command("chain")
def cci_chain(
    control_id: str = typer.Argument(..., help="NIST 800-53 control ID (e.g., ac-2)"),
    system: str | None = typer.Option(None, "--system", "-s", help="System for test results"),
) -> None:
    """Show full traceability chain: Control → CCIs → STIG rules (→ test results)."""
    asyncio.run(_chain(control_id, system))


async def _list_ccis(control: str | None, status: str | None, limit: int) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            data = await client.list_ccis(nist_control_id=control, status=status, limit=limit)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    items = data.get("items", [])

    if is_json_mode():
        print_json(data)
        return

    if not items:
        rprint("[dim]No CCI entries found.[/dim]")
        return

    table = Table(title=f"CCIs ({data.get('total', len(items))} total)")
    table.add_column("CCI ID", style="bold")
    table.add_column("Control", style="cyan")
    table.add_column("Type")
    table.add_column("Definition")

    for item in items:
        table.add_row(
            item["cci_id"],
            item["nist_control_id"].upper(),
            item.get("cci_type", ""),
            (item.get("definition", "") or "")[:60],
        )

    rprint(table)


async def _show_cci(cci_id: str) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    # Normalize CCI ID format
    if not cci_id.startswith("CCI-"):
        cci_id = f"CCI-{cci_id.zfill(6)}"

    async with PretorianClient() as client:
        require_auth(client)
        try:
            data = await client.get_cci(cci_id)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    if is_json_mode():
        print_json(data)
        return

    # Build detail panel
    content = (
        f"[bold]{data['cci_id']}[/bold] → {data['nist_control_id'].upper()}\n\n"
        f"[dim]Type:[/dim]   {data.get('cci_type', 'N/A')}\n"
        f"[dim]Status:[/dim] {data['status']}\n\n"
        f"[bold]Definition:[/bold]\n{data['definition']}\n"
    )

    if data.get("assessment_objective"):
        content += f"\n[bold]Assessment Objective:[/bold]\n{data['assessment_objective']}\n"

    rprint(Panel(content, title="CCI Detail", border_style="#FF9010"))

    # Show linked STIG rules
    stig_rules = data.get("stig_rules", [])
    if stig_rules:
        table = Table(title=f"STIG Rules ({len(stig_rules)})")
        table.add_column("STIG", style="cyan")
        table.add_column("Rule ID", style="bold")
        table.add_column("Severity")
        table.add_column("Title")

        severity_styles = {"cat_i": "red bold", "cat_ii": "yellow", "cat_iii": "green"}

        for r in stig_rules:
            sev = r.get("severity", "")
            table.add_row(
                r.get("stig_id", ""),
                r.get("rule_id", "")[:30],
                (
                    f"[{severity_styles.get(sev, '')}]{sev.upper().replace('_', ' ')}[/{severity_styles.get(sev, '')}]"
                    if sev
                    else ""
                ),
                (r.get("title", "") or "")[:50],
            )

        rprint(table)

    # Show linked SRGs
    srgs = data.get("srgs", [])
    if srgs:
        rprint(f"\n[bold]SRG Requirements ({len(srgs)}):[/bold]")
        for s in srgs:
            rprint(f"  {s['srg_id']}  {s.get('title', '')[:60]}")


async def _chain(control_id: str, system: str | None) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)

        # Get CCIs for this control
        try:
            cci_data = await client.list_ccis(nist_control_id=control_id.lower(), limit=500)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

        ccis = cci_data.get("items", [])

        # Get test results if system specified
        cci_status = {}
        if system:
            try:
                system_id, _ = await resolve_execution_context(client, system=system)
                status_data = await client.get_cci_status(system_id, nist_control_id=control_id.lower())
                for item in status_data.get("ccis", []):
                    cci_status[item["cci_id"]] = item
            except PretorianClientError:
                pass  # No test results available

    if is_json_mode():
        print_json({"control_id": control_id, "ccis": ccis, "cci_status": cci_status})
        return

    if not ccis:
        rprint(f"[dim]No CCIs found for {control_id.upper()}[/dim]")
        return

    # Build tree view
    tree = Tree(f"[bold]{control_id.upper()}[/bold]  ({len(ccis)} CCIs)")

    for cci in ccis:
        cci_id = cci["cci_id"]
        status_info = cci_status.get(cci_id)

        if status_info:
            s = status_info["status"]
            icon_map = {"pass": "✓", "fail": "✗", "mixed": "◐", "not_tested": "—"}
            color_map = {"pass": "green", "fail": "red", "mixed": "yellow", "not_tested": "dim"}
            icon = icon_map.get(s, "?")
            color = color_map.get(s, "")
            passing = status_info["passing_rules"]
            total = status_info["total_rules"]
            label = f"[{color}]{icon} {cci_id}[/{color}]  {s.upper()}  ({passing}/{total} rules)"
        else:
            label = f"[dim]— {cci_id}[/dim]  [{cci.get('cci_type', '')}]"

        cci_branch = tree.add(label)
        cci_branch.add(f"[dim]{(cci.get('definition', '') or '')[:80]}[/dim]")

        # Show STIG results if available
        if status_info:
            for sr in status_info.get("stig_results", [])[:5]:
                sr_icon = "✓" if sr["status"] == "pass" else "✗"
                sr_color = "green" if sr["status"] == "pass" else "red"
                cci_branch.add(f"  [{sr_color}]{sr_icon}[/{sr_color}] {sr.get('stig_id', '')} {sr.get('rule_id', '')}")

    rprint(tree)
