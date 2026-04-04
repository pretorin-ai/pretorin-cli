"""Scan commands — run STIG compliance scans and manage results."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

app = typer.Typer(
    name="scan",
    help="Run STIG compliance scans and view results.",
    no_args_is_help=True,
)


@app.command("doctor")
def scan_doctor() -> None:
    """Check which scanner tools are installed and available."""
    asyncio.run(_doctor())


@app.command("manifest")
def scan_manifest(
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID"),
    stig_id: str | None = typer.Option(None, "--stig", help="Filter to specific STIG"),
) -> None:
    """Show test manifest for the active system."""
    asyncio.run(_manifest(system, stig_id))


@app.command("run")
def scan_run(
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID"),
    stig_id: str | None = typer.Option(None, "--stig", help="Specific STIG to scan"),
    tool: str | None = typer.Option(None, "--tool", "-t", help="Force specific scanner (openscap, inspec, manual)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Preview scan plan without executing"),
) -> None:
    """Run STIG compliance scans against a system."""
    asyncio.run(_run_scan(system, stig_id, tool, dry_run))


@app.command("results")
def scan_results(
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID"),
    control: str | None = typer.Option(None, "--control", "-c", help="Filter by NIST control ID"),
) -> None:
    """Show latest CCI-level test results for the active system."""
    asyncio.run(_results(system, control))


async def _doctor() -> None:
    from pretorin.scanners.orchestrator import ScanOrchestrator

    orchestrator = ScanOrchestrator()
    infos = await orchestrator.detect_scanners()

    if is_json_mode():
        print_json(
            [
                {
                    "name": info.name,
                    "version": info.version,
                    "available": info.available,
                    "supported_stigs": info.supported_stigs,
                    "install_hint": info.install_hint,
                }
                for info in infos
            ]
        )
        return

    table = Table(title="Scanner Availability")
    table.add_column("Scanner", style="bold")
    table.add_column("Status")
    table.add_column("Version")
    table.add_column("STIGs")
    table.add_column("Install Hint", style="dim")

    for info in infos:
        status = "[green]✓ Available[/green]" if info.available else "[red]✗ Missing[/red]"
        stigs = ", ".join(info.supported_stigs[:3])
        if len(info.supported_stigs) > 3:
            stigs += f" (+{len(info.supported_stigs) - 3})"
        table.add_row(
            info.name,
            status,
            info.version or "",
            stigs,
            info.install_hint if not info.available else "",
        )

    rprint(table)

    available_count = sum(1 for i in infos if i.available)
    rprint(f"\n[dim]{available_count}/{len(infos)} scanners available[/dim]")


async def _manifest(system: str | None, stig_id: str | None) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, _ = await resolve_execution_context(client, system=system)
            manifest = await client.get_test_manifest(system_id, stig_id=stig_id)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    if is_json_mode():
        print_json(manifest)
        return

    stigs = manifest.get("applicable_stigs", [])
    if not stigs:
        rprint("[dim]No applicable STIGs found for this system.[/dim]")
        rprint("[dim]Run 'pretorin stig applicable' to check STIG applicability.[/dim]")
        return

    total_rules = sum(len(s.get("rules", [])) for s in stigs)
    rprint(
        Panel(
            f"System: {manifest['system_id']}\nSTIGs:  {len(stigs)}\nRules:  {total_rules}",
            title="Test Manifest",
            border_style="#FF9010",
        )
    )

    for stig in stigs:
        rules = stig.get("rules", [])
        cat_i = sum(1 for r in rules if r.get("severity") == "cat_i")
        cat_ii = sum(1 for r in rules if r.get("severity") == "cat_ii")
        cat_iii = sum(1 for r in rules if r.get("severity") == "cat_iii")
        rprint(
            f"  [bold]{stig['stig_id']}[/bold] ({stig.get('stig_name', '')[:40]}) "
            f"— {len(rules)} rules "
            f"([red]CAT I: {cat_i}[/red] [yellow]CAT II: {cat_ii}[/yellow] [green]CAT III: {cat_iii}[/green])"
        )


async def _run_scan(system: str | None, stig_id: str | None, tool: str | None, dry_run: bool) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.scanners.orchestrator import ScanOrchestrator

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, _ = await resolve_execution_context(client, system=system)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

        orchestrator = ScanOrchestrator()

        if dry_run:
            rprint("[bold]Scan Plan (dry run)[/bold]\n")

            # Detect scanners
            infos = await orchestrator.detect_scanners()
            available = [i for i in infos if i.available]
            rprint(f"Available scanners: {', '.join(i.name for i in available)}")

            # Get manifest
            try:
                manifest = await client.get_test_manifest(system_id, stig_id=stig_id)
            except PretorianClientError as e:
                rprint(f"[red]Error getting manifest: {e.message}[/red]")
                raise typer.Exit(1)

            plan = orchestrator.plan_scan(manifest, preferred_scanner=tool)

            for step in plan.steps:
                rprint(f"  [bold]{step.scanner_name}[/bold] → {step.benchmark_id} ({len(step.rules)} rules)")

            if plan.unassigned_rules:
                rprint(
                    f"\n  [yellow]⚠ {len(plan.unassigned_rules)} rules have no "
                    f"automated scanner (require manual review)[/yellow]"
                )

            rprint("\n[dim]Run without --dry-run to execute.[/dim]")
            return

        # Full scan
        rprint("[bold]Starting STIG compliance scan...[/bold]\n")

        try:
            report = await orchestrator.run(
                client,
                system_id=system_id,
                stig_id=stig_id,
                preferred_scanner=tool,
            )
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    if is_json_mode():
        print_json(
            {
                "cli_run_id": report.cli_run_id,
                "total": report.total,
                "passed": report.passed,
                "failed": report.failed,
                "not_reviewed": report.not_reviewed,
                "errors": report.errors,
            }
        )
        return

    # Display results summary
    rprint(
        Panel(
            f"Run ID:       {report.cli_run_id}\n"
            f"Total rules:  {report.total}\n"
            f"[green]Passed:       {report.passed}[/green]\n"
            f"[red]Failed:       {report.failed}[/red]\n"
            f"Not reviewed: {report.not_reviewed}",
            title="Scan Complete",
            border_style="#FF9010",
        )
    )

    if report.errors:
        rprint(f"\n[yellow]Errors ({len(report.errors)}):[/yellow]")
        for err in report.errors[:5]:
            rprint(f"  [red]• {err}[/red]")


async def _results(system: str | None, control: str | None) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, _ = await resolve_execution_context(client, system=system)
            data = await client.get_cci_status(system_id, nist_control_id=control)
        except PretorianClientError as e:
            rprint(f"[red]Error: {e.message}[/red]")
            raise typer.Exit(1)

    if is_json_mode():
        print_json(data)
        return

    ccis = data.get("ccis", [])
    if not ccis:
        rprint("[dim]No CCI test results found.[/dim]")
        return

    table = Table(title="CCI Compliance Status")
    table.add_column("CCI", style="bold")
    table.add_column("Control", style="cyan")
    table.add_column("Status")
    table.add_column("Rules", justify="right")
    table.add_column("Pass", justify="right", style="green")
    table.add_column("Fail", justify="right", style="red")
    table.add_column("Last Tested", style="dim")

    status_styles = {
        "pass": "[green]✓ Pass[/green]",
        "fail": "[red]✗ Fail[/red]",
        "mixed": "[yellow]◐ Mixed[/yellow]",
        "not_tested": "[dim]— Not tested[/dim]",
    }

    for cci in ccis:
        table.add_row(
            cci["cci_id"],
            cci["nist_control_id"].upper(),
            status_styles.get(cci["status"], cci["status"]),
            str(cci["total_rules"]),
            str(cci["passing_rules"]),
            str(cci["failing_rules"]),
            cci.get("last_tested", "")[:10] if cci.get("last_tested") else "",
        )

    rprint(table)

    # Summary
    total = len(ccis)
    passing = sum(1 for c in ccis if c["status"] == "pass")
    failing = sum(1 for c in ccis if c["status"] == "fail")
    not_tested = sum(1 for c in ccis if c["status"] == "not_tested")
    rprint(f"\n[dim]Summary: {passing} passing, {failing} failing, {not_tested} not tested ({total} total CCIs)[/dim]")
