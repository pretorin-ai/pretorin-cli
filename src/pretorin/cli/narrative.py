"""Narrative CLI commands for Pretorin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint

from pretorin.cli.output import is_json_mode, print_json

app = typer.Typer(
    name="narrative",
    help="Narrative management. Use 'pretorin agent run --skill narrative-generation' to generate narratives.",
    no_args_is_help=True,
)

ROMEBOT_AI = "[#EAB536][°~°][/#EAB536]"


@app.command("push")
def narrative_push(
    control_id: str = typer.Argument(..., help="Control ID"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    system: str = typer.Argument(..., help="System name or ID"),
    file: Path = typer.Argument(..., help="Narrative file to push", exists=True, readable=True),
) -> None:
    """Push a narrative file to the platform.

    Reads a markdown/text file and submits it as the implementation
    narrative for a control in a system.

    To generate narratives with AI, use the agent:
        pretorin agent run --skill narrative-generation "Generate narrative for AC-02"

    Examples:
        pretorin narrative push ac-2 fedramp-moderate "My System" narrative-ac2.md
    """
    content = file.read_text().strip()
    if not content:
        rprint("[red]File is empty.[/red]")
        raise typer.Exit(1)

    asyncio.run(_push_narrative(control_id, framework_id, system, content))


async def _push_narrative(
    control_id: str,
    framework_id: str,
    system: str,
    content: str,
) -> None:
    """Push narrative content to the platform."""
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' first.[/red]")
            raise typer.Exit(1)

        # Resolve system
        try:
            systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        target = None
        system_lower = system.lower()
        for s in systems:
            if s["id"] == system or s["name"].lower().startswith(system_lower):
                target = s
                break

        if target is None:
            rprint(f"[red]System not found: {system}[/red]")
            raise typer.Exit(1)

        system_id = target["id"]

        try:
            result = await client.update_narrative(
                system_id=system_id,
                control_id=control_id,
                framework_id=framework_id,
                narrative=content,
                is_ai_generated=False,
            )
        except PretorianClientError as e:
            rprint(f"[red]Push failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(result)
            return

        rprint(f"[#95D7E0]Narrative pushed for {control_id.upper()} in {target['name']}[/#95D7E0]")
