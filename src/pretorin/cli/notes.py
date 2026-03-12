"""Control note commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.utils import normalize_control_id

console = Console()

app = typer.Typer(
    name="notes",
    help="Local note management and platform sync.",
    no_args_is_help=True,
)

ROMEBOT_NOTE = "[#EAB536]\\[°□°][/#EAB536]"


@app.command("create")
def notes_create(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    content: str = typer.Option(
        ...,
        "--content",
        "-c",
        help="Note content",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Note name (defaults to content summary)",
    ),
) -> None:
    """Create a local note file.

    Creates a markdown file in notes/<framework>/<control>/<slug>.md
    with YAML frontmatter for tracking.

    Examples:
        pretorin notes create ac-02 fedramp-moderate -c "Gap: missing SSO evidence"
        pretorin notes create sc-07 nist-800-53-r5 -c "Need firewall config" -n "firewall-gap"
    """
    from pretorin.notes.writer import LocalNote, NotesWriter

    control_id = normalize_control_id(control_id)
    note_name = name or content[:60]

    note = LocalNote(
        control_id=control_id,
        framework_id=framework_id,
        name=note_name,
        content=content,
    )

    writer = NotesWriter()
    path = writer.write(note)

    if is_json_mode():
        print_json(
            {
                "path": str(path),
                "control_id": control_id,
                "framework_id": framework_id,
                "name": note_name,
            }
        )
        return

    rprint(
        f"\n  {ROMEBOT_NOTE}  [bold]Note Created[/bold]\n"
        f"  [bold]File:[/bold]      {path}\n"
        f"  [bold]Control:[/bold]   {control_id.upper()}\n"
        f"  [bold]Framework:[/bold] {framework_id}"
    )
    rprint("[dim]Push with: pretorin notes push[/dim]")


@app.command("list")
def notes_list(
    control_id: str | None = typer.Argument(None, help="Control ID (e.g., ac-02). Required for platform list."),
    framework_id: str | None = typer.Argument(None, help="Framework ID. Required for platform list."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
    local: bool = typer.Option(False, "--local", help="List local note files instead of platform notes"),
    framework_filter: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help="Filter local notes by framework ID (only with --local)",
    ),
) -> None:
    """List notes for a control (platform) or local note files.

    Examples:
        pretorin notes list ac-02 fedramp-moderate
        pretorin notes list --local
        pretorin notes list --local --framework fedramp-moderate
    """
    if local:
        _list_local_notes(framework_filter)
    else:
        if not control_id or not framework_id:
            rprint("[red]control_id and framework_id are required for platform notes list.[/red]")
            rprint("[dim]Use --local to list local note files instead.[/dim]")
            raise typer.Exit(1)
        asyncio.run(_list_notes(normalize_control_id(control_id), framework_id, system))


def _list_local_notes(framework_filter: str | None) -> None:
    """List local note files."""
    from pretorin.notes.writer import NotesWriter

    writer = NotesWriter()
    items = writer.list_local(framework_filter)

    if is_json_mode():
        print_json(
            [
                {
                    "control_id": n.control_id,
                    "framework_id": n.framework_id,
                    "name": n.name,
                    "platform_synced": n.platform_synced,
                    "path": str(n.path),
                }
                for n in items
            ]
        )
        return

    if not items:
        rprint("[dim]No local notes found.[/dim]")
        rprint('[dim]Create one with: [bold]pretorin notes create ac-02 fedramp-moderate -c "content"[/bold][/dim]')
        return

    table = Table(title="Local Notes", show_header=True, header_style="bold")
    table.add_column("Control", style="cyan")
    table.add_column("Framework")
    table.add_column("Name")
    table.add_column("Synced")

    for n in items:
        synced = "[#95D7E0]Yes[/#95D7E0]" if n.platform_synced else "[dim]No[/dim]"
        table.add_row(
            n.control_id.upper(),
            n.framework_id,
            n.name[:40] + "..." if len(n.name) > 40 else n.name,
            synced,
        )

    console.print(table)
    rprint(f"\n[dim]Total: {len(items)} note(s)[/dim]")


@app.command("push")
def notes_push(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be pushed without pushing"),
) -> None:
    """Push local notes to the Pretorin platform.

    Unsynced notes (without platform_synced) are pushed.
    Notes are append-only on the platform.

    Examples:
        pretorin notes push --dry-run
        pretorin notes push
    """
    asyncio.run(_push_notes(dry_run))


async def _push_notes(dry_run: bool) -> None:
    """Push notes to platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.notes.sync import NotesSync

    async with PretorianClient() as client:
        require_auth(client)

        sync = NotesSync()

        if not is_json_mode():
            mode = "[yellow]DRY RUN[/yellow] " if dry_run else ""
            rprint(f"\n  {ROMEBOT_NOTE}  {mode}Pushing notes to platform...\n")

        try:
            result = await sync.push(client, dry_run=dry_run)
        except PretorianClientError as e:
            rprint(f"[red]Push failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(
                {
                    "pushed": result.pushed,
                    "skipped": result.skipped,
                    "errors": result.errors,
                }
            )
            return

        if result.pushed:
            rprint("[bold]Pushed:[/bold]")
            for item in result.pushed:
                rprint(f"  [#95D7E0]+[/#95D7E0] {item}")

        if result.skipped:
            rprint(f"\n[dim]Skipped {len(result.skipped)} already-synced note(s)[/dim]")

        if result.errors:
            rprint("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                rprint(f"  [red]![/red] {err}")

        if not result.pushed and not result.errors:
            rprint("[dim]Nothing to push — all notes are already synced.[/dim]")


@app.command("add")
def notes_add(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    content: str = typer.Option(..., "--content", "-c", help="Note content"),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Add a note to a control implementation (directly on platform)."""
    asyncio.run(_add_note(normalize_control_id(control_id), framework_id, content, system))


async def _list_notes(
    control_id: str,
    framework_id: str,
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
            notes = await client.list_control_notes(
                system_id=system_id,
                control_id=control_id,
                framework_id=resolved_framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]List failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "control_id": control_id,
            "framework_id": resolved_framework_id,
            "total": len(notes),
            "notes": notes,
        }
        if is_json_mode():
            print_json(payload)
            return

        if not notes:
            rprint("[dim]No notes for this control yet.[/dim]")
            return

        table = Table(title=f"Control Notes ({control_id.upper()})", show_header=True, header_style="bold")
        table.add_column("#", style="cyan", no_wrap=True)
        table.add_column("Content")
        for idx, note in enumerate(notes, start=1):
            table.add_row(str(idx), str(note.get("content", "")))
        rprint(f"[bold]System:[/bold] {system_name}")
        rprint(f"[bold]Framework:[/bold] {resolved_framework_id}\n")
        rprint(table)


async def _add_note(
    control_id: str,
    framework_id: str,
    content: str,
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
            result = await client.add_control_note(
                system_id=system_id,
                control_id=control_id,
                framework_id=resolved_framework_id,
                content=content,
                source="cli",
            )
        except PretorianClientError as e:
            rprint(f"[red]Add failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "control_id": control_id,
            "framework_id": resolved_framework_id,
            "note": result,
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(f"[#95D7E0]Note added for {control_id.upper()} in {system_name}[/#95D7E0]")
