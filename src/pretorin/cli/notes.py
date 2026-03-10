"""Control note commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.utils import normalize_control_id

app = typer.Typer(
    name="notes",
    help="Control note management.",
    no_args_is_help=True,
)


@app.command("list")
def notes_list(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """List notes for a control implementation."""
    asyncio.run(_list_notes(normalize_control_id(control_id), framework_id, system))


@app.command("add")
def notes_add(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    content: str = typer.Option(..., "--content", "-c", help="Note content"),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Add a note to a control implementation."""
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
