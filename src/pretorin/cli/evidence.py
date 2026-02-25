"""Evidence CLI commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="evidence",
    help="Local evidence management and platform sync.",
    no_args_is_help=True,
)

ROMEBOT_EVIDENCE = "[#EAB536][°□°][/#EAB536]"


@app.command("create")
def evidence_create(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-2)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    description: str = typer.Option(
        ..., "--description", "-d", help="Evidence description",
    ),
    name: str | None = typer.Option(
        None, "--name", "-n", help="Evidence name (defaults to description summary)",
    ),
    evidence_type: str = typer.Option(
        "documentation", "--type", "-t",
        help="Evidence type: documentation, configuration, screenshot, log, code",
    ),
) -> None:
    """Create a local evidence file.

    Creates a markdown file in evidence/<framework>/<control>/<slug>.md
    with YAML frontmatter for tracking.

    Examples:
        pretorin evidence create ac-2 fedramp-moderate -d "RBAC configuration in Kubernetes"
        pretorin evidence create sc-7 nist-800-53-r5 -d "Firewall rules" -t configuration
    """
    from pretorin.evidence.writer import EvidenceWriter, LocalEvidence

    evidence_name = name or description[:60]

    evidence = LocalEvidence(
        control_id=control_id,
        framework_id=framework_id,
        name=evidence_name,
        description=description,
        evidence_type=evidence_type,
    )

    writer = EvidenceWriter()
    path = writer.write(evidence)

    if is_json_mode():
        print_json({
            "path": str(path),
            "control_id": control_id,
            "framework_id": framework_id,
            "name": evidence_name,
        })
        return

    rprint(Panel(
        f"  [bold]File:[/bold]      {path}\n"
        f"  [bold]Control:[/bold]   {control_id.upper()}\n"
        f"  [bold]Framework:[/bold] {framework_id}\n"
        f"  [bold]Type:[/bold]      {evidence_type}",
        title=f"{ROMEBOT_EVIDENCE}  Evidence Created",
        border_style="#95D7E0",
        padding=(1, 2),
    ))
    rprint("[dim]Edit the file to add details, then push with: pretorin evidence push[/dim]")


@app.command("list")
def evidence_list(
    framework: str | None = typer.Option(
        None, "--framework", "-f", help="Filter by framework ID",
    ),
) -> None:
    """List local evidence files.

    Examples:
        pretorin evidence list
        pretorin evidence list --framework fedramp-moderate
    """
    from pretorin.evidence.writer import EvidenceWriter

    writer = EvidenceWriter()
    items = writer.list_local(framework)

    if is_json_mode():
        print_json([{
            "control_id": e.control_id,
            "framework_id": e.framework_id,
            "name": e.name,
            "evidence_type": e.evidence_type,
            "status": e.status,
            "platform_id": e.platform_id,
            "path": str(e.path),
        } for e in items])
        return

    if not items:
        rprint("[dim]No local evidence found.[/dim]")
        rprint(
            '[dim]Create one with: [bold]pretorin evidence create ac-2'
            ' fedramp-moderate -d "description"[/bold][/dim]'
        )
        return

    table = Table(title="Local Evidence", show_header=True, header_style="bold")
    table.add_column("Control", style="cyan")
    table.add_column("Framework")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Synced")

    for e in items:
        synced = "[#95D7E0]Yes[/#95D7E0]" if e.platform_id else "[dim]No[/dim]"
        table.add_row(
            e.control_id.upper(),
            e.framework_id,
            e.name[:40] + "..." if len(e.name) > 40 else e.name,
            e.evidence_type,
            synced,
        )

    console.print(table)
    rprint(f"\n[dim]Total: {len(items)} evidence item(s)[/dim]")


@app.command("push")
def evidence_push(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be pushed without pushing"),
) -> None:
    """Push local evidence to the Pretorin platform.

    New evidence (without platform_id) gets created on the platform.
    Already-synced evidence is skipped.

    Examples:
        pretorin evidence push --dry-run
        pretorin evidence push
    """
    asyncio.run(_push_evidence(dry_run))


async def _push_evidence(dry_run: bool) -> None:
    """Push evidence to platform."""
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.evidence.sync import EvidenceSync

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' first.[/red]")
            raise typer.Exit(1)

        sync = EvidenceSync()

        if not is_json_mode():
            mode = "[yellow]DRY RUN[/yellow] " if dry_run else ""
            rprint(f"\n  {ROMEBOT_EVIDENCE}  {mode}Pushing evidence to platform...\n")

        try:
            result = await sync.push(client, dry_run=dry_run)
        except PretorianClientError as e:
            rprint(f"[red]Push failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json({
                "created": result.created,
                "skipped": result.skipped,
                "errors": result.errors,
            })
            return

        if result.created:
            rprint("[bold]Created:[/bold]")
            for item in result.created:
                rprint(f"  [#95D7E0]+[/#95D7E0] {item}")

        if result.skipped:
            rprint(f"\n[dim]Skipped {len(result.skipped)} already-synced item(s)[/dim]")

        if result.errors:
            rprint("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                rprint(f"  [red]![/red] {err}")

        if not result.created and not result.errors:
            rprint("[dim]Nothing to push — all evidence is already synced.[/dim]")
