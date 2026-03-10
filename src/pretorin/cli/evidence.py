"""Evidence CLI commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.utils import normalize_control_id

console = Console()

app = typer.Typer(
    name="evidence",
    help="Local evidence management and platform sync.",
    no_args_is_help=True,
)

ROMEBOT_EVIDENCE = "[#EAB536]\\[°□°][/#EAB536]"
_VALID_EVIDENCE_TYPES = {
    "screenshot",
    "screen_recording",
    "log_file",
    "configuration",
    "test_result",
    "certificate",
    "attestation",
    "code_snippet",
    "repository_link",
    "policy_document",
    "scan_result",
    "interview_notes",
    "other",
}


@app.command("create")
def evidence_create(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    description: str = typer.Option(
        ...,
        "--description",
        "-d",
        help="Evidence description",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Evidence name (defaults to description summary)",
    ),
    evidence_type: str = typer.Option(
        "policy_document",
        "--type",
        "-t",
        help=(
            "Evidence type: screenshot, screen_recording, log_file, configuration, "
            "test_result, certificate, attestation, code_snippet, repository_link, "
            "policy_document, scan_result, interview_notes, other"
        ),
    ),
) -> None:
    """Create a local evidence file.

    Creates a markdown file in evidence/<framework>/<control>/<slug>.md
    with YAML frontmatter for tracking.

    Examples:
        pretorin evidence create ac-02 fedramp-moderate -d "RBAC configuration in Kubernetes"
        pretorin evidence create sc-07 nist-800-53-r5 -d "Firewall rules" -t configuration
    """
    from pretorin.evidence.writer import EvidenceWriter, LocalEvidence

    control_id = normalize_control_id(control_id)
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
        print_json(
            {
                "path": str(path),
                "control_id": control_id,
                "framework_id": framework_id,
                "name": evidence_name,
            }
        )
        return

    rprint(
        Panel(
            f"  [bold]File:[/bold]      {path}\n"
            f"  [bold]Control:[/bold]   {control_id.upper()}\n"
            f"  [bold]Framework:[/bold] {framework_id}\n"
            f"  [bold]Type:[/bold]      {evidence_type}",
            title=f"{ROMEBOT_EVIDENCE}  Evidence Created",
            border_style="#95D7E0",
            padding=(1, 2),
        )
    )
    rprint("[dim]Edit the file to add details, then push with: pretorin evidence push[/dim]")


@app.command("list")
def evidence_list(
    framework: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help="Filter by framework ID",
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
        print_json(
            [
                {
                    "control_id": e.control_id,
                    "framework_id": e.framework_id,
                    "name": e.name,
                    "evidence_type": e.evidence_type,
                    "status": e.status,
                    "platform_id": e.platform_id,
                    "path": str(e.path),
                }
                for e in items
            ]
        )
        return

    if not items:
        rprint("[dim]No local evidence found.[/dim]")
        rprint(
            '[dim]Create one with: [bold]pretorin evidence create ac-02 fedramp-moderate -d "description"[/bold][/dim]'
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

    New evidence (without platform_id) is upserted on the platform.
    Already-synced evidence is skipped.

    Examples:
        pretorin evidence push --dry-run
        pretorin evidence push
    """
    asyncio.run(_push_evidence(dry_run))


async def _push_evidence(dry_run: bool) -> None:
    """Push evidence to platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.evidence.sync import EvidenceSync

    async with PretorianClient() as client:
        require_auth(client)

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
            print_json(
                {
                    "created": result.created,
                    "reused": result.reused,
                    "skipped": result.skipped,
                    "errors": result.errors,
                    # Deprecated: retained for compatibility.
                    "events": result.events,
                }
            )
            return

        if result.created:
            rprint("[bold]Created:[/bold]")
            for item in result.created:
                rprint(f"  [#95D7E0]+[/#95D7E0] {item}")

        if result.reused:
            rprint("\n[bold]Reused:[/bold]")
            for item in result.reused:
                rprint(f"  [#EAB536]=[/#EAB536] {item}")

        if result.skipped:
            rprint(f"\n[dim]Skipped {len(result.skipped)} already-synced item(s)[/dim]")

        if result.errors:
            rprint("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                rprint(f"  [red]![/red] {err}")

        if not result.created and not result.reused and not result.errors:
            rprint("[dim]Nothing to push — all evidence is already synced.[/dim]")


@app.command("link")
def evidence_link(
    evidence_id: str = typer.Argument(..., help="Evidence item ID"),
    control_id: str = typer.Argument(..., help="Control ID to link to (e.g., ac-02)"),
    framework_id: str | None = typer.Option(None, "--framework-id", "-f", help="Framework ID."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Link an existing evidence item to a control.

    Examples:
        pretorin evidence link abc123 ac-02
        pretorin evidence link abc123 sc-07 --framework-id fedramp-moderate
    """
    asyncio.run(
        _link_evidence(
            evidence_id=evidence_id,
            control_id=normalize_control_id(control_id),
            framework_id=framework_id,
            system=system,
        )
    )


async def _link_evidence(
    evidence_id: str,
    control_id: str,
    framework_id: str | None,
    system: str | None,
) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            system_name = (await client.get_system(system_id)).name
            result = await client.link_evidence_to_control(
                evidence_id=evidence_id,
                control_id=control_id,
                system_id=system_id,
                framework_id=resolved_framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]Link failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "evidence_id": evidence_id,
            "control_id": control_id,
            "framework_id": resolved_framework_id,
            "result": result,
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(
            Panel(
                f"  [bold]System:[/bold]      {system_name}\n"
                f"  [bold]Evidence ID:[/bold] {evidence_id}\n"
                f"  [bold]Control:[/bold]     {control_id.upper()}\n"
                f"  [bold]Framework:[/bold]   {resolved_framework_id}",
                title=f"{ROMEBOT_EVIDENCE}  Evidence Linked",
                border_style="#95D7E0",
                padding=(1, 2),
            )
        )


@app.command("search")
def evidence_search(
    control_id: str | None = typer.Option(None, "--control-id", "-c", help="Optional control ID filter."),
    framework_id: str | None = typer.Option(None, "--framework-id", "-f", help="Framework ID."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max results."),
) -> None:
    """Search platform evidence items within one active system/framework scope."""
    asyncio.run(
        _search_evidence(
            control_id=control_id,
            framework_id=framework_id,
            system=system,
            limit=limit,
        )
    )


async def _search_evidence(
    control_id: str | None,
    framework_id: str | None,
    system: str | None,
    limit: int,
) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError

    control_filter = normalize_control_id(control_id) if control_id else None

    async with PretorianClient() as client:
        require_auth(client)

        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            system_name = (await client.get_system(system_id)).name
            items = await client.list_evidence(
                system_id=system_id,
                framework_id=resolved_framework_id,
                control_id=control_filter,
                limit=limit,
            )
        except PretorianClientError as e:
            rprint(f"[red]Search failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(
                {
                    "scope": f"system:{system_id}/framework:{resolved_framework_id}",
                    "system_name": system_name,
                    "framework_id": resolved_framework_id,
                    "total": len(items),
                    "evidence": [item.model_dump() for item in items],
                }
            )
            return

        scope = f"[bold]{system_name}[/bold] / [bold]{resolved_framework_id}[/bold]"
        rprint(f"\n  {ROMEBOT_EVIDENCE}  Evidence Search Scope: {scope}\n")
        if not items:
            rprint("[dim]No evidence found for the current filters.[/dim]")
            return

        table = Table(title="Platform Evidence", show_header=True, header_style="bold")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name")
        table.add_column("Type")
        table.add_column("Status")

        for item in items:
            table.add_row(item.id[:8], item.name, item.evidence_type or "-", item.status or "-")

        console.print(table)
        rprint(f"\n[dim]Total: {len(items)} evidence item(s)[/dim]")


@app.command("upsert")
def evidence_upsert(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    name: str = typer.Option(..., "--name", "-n", help="Evidence name"),
    description: str = typer.Option(
        ...,
        "--description",
        "-d",
        help=(
            "Evidence markdown with no headings and at least one rich element "
            "(code block, table, list, or link). Images are not allowed yet."
        ),
    ),
    evidence_type: str = typer.Option("policy_document", "--type", "-t", help="Evidence type."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Find-or-create evidence and ensure system/control link."""
    if evidence_type not in _VALID_EVIDENCE_TYPES:
        rprint(
            f"[red]Invalid evidence type: {evidence_type}. "
            f"Choose one of: {', '.join(sorted(_VALID_EVIDENCE_TYPES))}[/red]"
        )
        raise typer.Exit(1)

    asyncio.run(
        _upsert_evidence(
            control_id=normalize_control_id(control_id),
            framework_id=framework_id,
            name=name,
            description=description,
            evidence_type=evidence_type,
            system=system,
        )
    )


async def _upsert_evidence(
    control_id: str,
    framework_id: str,
    name: str,
    description: str,
    evidence_type: str,
    system: str | None,
) -> None:
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.workflows.compliance_updates import upsert_evidence

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            system_name = (await client.get_system(system_id)).name
            result = await upsert_evidence(
                client,
                system_id=system_id,
                name=name,
                description=description,
                evidence_type=evidence_type,
                control_id=control_id,
                framework_id=resolved_framework_id,
                source="cli",
                dedupe=True,
            )
        except ValueError as e:
            rprint(f"[red]Upsert failed: {e}[/red]")
            raise typer.Exit(1)
        except PretorianClientError as e:
            rprint(f"[red]Upsert failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = result.to_dict()
        payload.update(
            {
                "system_id": system_id,
                "system_name": system_name,
                "control_id": control_id,
                "framework_id": resolved_framework_id,
            }
        )
        if is_json_mode():
            print_json(payload)
            return

        action = "Created" if result.created else "Reused"
        link_state = "linked" if result.linked else "link_pending"
        rprint(
            Panel(
                f"  [bold]Action:[/bold]    {action}\n"
                f"  [bold]Evidence ID:[/bold] {result.evidence_id}\n"
                f"  [bold]System:[/bold]    {system_name}\n"
                f"  [bold]Control:[/bold]   {control_id.upper()}\n"
                f"  [bold]Framework:[/bold] {resolved_framework_id}\n"
                f"  [bold]Link:[/bold]      {link_state}\n",
                title=f"{ROMEBOT_EVIDENCE}  Evidence Upserted",
                border_style="#95D7E0",
                padding=(1, 2),
            )
        )
        if result.link_error:
            rprint(f"[yellow]Warning: evidence link failed: {result.link_error}[/yellow]")
