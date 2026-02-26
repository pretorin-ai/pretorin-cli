"""Narrative CLI commands for Pretorin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="narrative",
    help="AI narrative generation and management.",
    no_args_is_help=True,
)

ROMEBOT_AI = "[#EAB536][°~°][/#EAB536]"


@app.command("generate")
def narrative_generate(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-2)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    system: str | None = typer.Option(
        None,
        "--system",
        "-s",
        help="System name or ID. Auto-selects if only one.",
    ),
    context: str | None = typer.Option(
        None,
        "--context",
        "-c",
        help="Additional context for narrative generation.",
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Write narrative to a file.",
    ),
) -> None:
    """Generate an AI implementation narrative for a control.

    This calls the Pretorin AI to generate a narrative describing how
    a specific control is implemented in your system.

    Examples:
        pretorin narrative generate ac-2 fedramp-moderate
        pretorin narrative generate sc-7 nist-800-53-r5 --system "My System"
        pretorin narrative generate ac-2 fedramp-moderate -o narrative-ac2.md
    """
    asyncio.run(_generate_narrative(control_id, framework_id, system, context, output))


async def _generate_narrative(
    control_id: str,
    framework_id: str,
    system: str | None,
    context: str | None,
    output: Path | None,
) -> None:
    """Generate narrative via the API."""
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

        if not systems:
            rprint("[red]No systems found. Create a system on the platform first.[/red]")
            raise typer.Exit(1)

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
            rprint(
                f"\n  {ROMEBOT_AI}  Generating narrative for"
                f" [bold]{control_id.upper()}[/bold] in [bold]{system_name}[/bold]"
            )
            rprint("[dim]  This may take 30-60 seconds...[/dim]\n")

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("AI is analyzing your system...", total=None)
                result = await client.generate_narrative(
                    system_id=system_id,
                    control_id=control_id,
                    framework_id=framework_id,
                    context=context,
                )
        except PretorianClientError as e:
            rprint(f"[red]Narrative generation failed: {e.message}[/red]")
            raise typer.Exit(1)

        narrative_text = result.get("narrative", "")
        confidence = result.get("ai_confidence_score")

        if output:
            output.write_text(narrative_text)
            if not is_json_mode():
                rprint(f"[#95D7E0]Written to {output}[/#95D7E0]")

        if is_json_mode():
            print_json(
                {
                    "system_id": system_id,
                    "control_id": control_id,
                    "framework_id": framework_id,
                    "narrative": narrative_text,
                    "ai_confidence_score": confidence,
                }
            )
            return

        rprint(
            Panel(
                narrative_text or "[dim]No narrative generated.[/dim]",
                title=f"{control_id.upper()} Implementation Narrative",
                border_style="#EAB536",
                padding=(1, 2),
            )
        )
        if confidence:
            rprint(f"[dim]AI Confidence: {confidence:.0%}[/dim]")


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
            result = await client.generate_narrative(
                system_id=system_id,
                control_id=control_id,
                framework_id=framework_id,
                context=f"Use this exact narrative text:\n\n{content}",
            )
        except PretorianClientError as e:
            rprint(f"[red]Push failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(result)
            return

        rprint(f"[#95D7E0]Narrative pushed for {control_id.upper()} in {target['name']}[/#95D7E0]")
