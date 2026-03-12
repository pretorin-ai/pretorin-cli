"""Narrative CLI commands for Pretorin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.utils import normalize_control_id

console = Console()

app = typer.Typer(
    name="narrative",
    help="Local narrative management and platform sync.",
    no_args_is_help=True,
)

ROMEBOT_AI = "[#EAB536]\\[°~°][/#EAB536]"


@app.command("create")
def narrative_create(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., fedramp-moderate)"),
    content: str = typer.Option(
        ...,
        "--content",
        "-c",
        help="Narrative content (auditor-ready markdown, no headings)",
    ),
    name: str | None = typer.Option(
        None,
        "--name",
        "-n",
        help="Narrative name (defaults to control-framework slug)",
    ),
    ai_generated: bool = typer.Option(
        False,
        "--ai-generated",
        help="Mark narrative as AI-generated",
    ),
) -> None:
    """Create a local narrative file.

    Creates a markdown file in narratives/<framework>/<control>/<slug>.md
    with YAML frontmatter for tracking.

    Examples:
        pretorin narrative create ac-02 fedramp-moderate -c "- item\\n\\n```code```"
        pretorin narrative create sc-07 nist-800-53-r5 -c "- list item" -n "SC-07 boundary"
    """
    from pretorin.narrative.writer import LocalNarrative, NarrativeWriter
    from pretorin.workflows.markdown_quality import validate_audit_markdown

    control_id = normalize_control_id(control_id)
    narrative_name = name or f"{control_id}-{framework_id}"

    result = validate_audit_markdown(content, "narrative")
    if not result.is_valid:
        rprint(f"[red]Validation failed: {result.error_message()}[/red]")
        raise typer.Exit(1)

    narrative = LocalNarrative(
        control_id=control_id,
        framework_id=framework_id,
        name=narrative_name,
        content=content,
        is_ai_generated=ai_generated,
    )

    writer = NarrativeWriter()
    path = writer.write(narrative)

    if is_json_mode():
        print_json(
            {
                "path": str(path),
                "control_id": control_id,
                "framework_id": framework_id,
                "name": narrative_name,
                "is_ai_generated": ai_generated,
            }
        )
        return

    rprint(
        f"\n  {ROMEBOT_AI}  [bold]Narrative Created[/bold]\n"
        f"  [bold]File:[/bold]      {path}\n"
        f"  [bold]Control:[/bold]   {control_id.upper()}\n"
        f"  [bold]Framework:[/bold] {framework_id}\n"
        f"  [bold]AI Gen:[/bold]    {ai_generated}"
    )
    rprint("[dim]Edit the file to refine, then push with: pretorin narrative push[/dim]")


@app.command("list")
def narrative_list(
    framework: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help="Filter by framework ID",
    ),
) -> None:
    """List local narrative files.

    Examples:
        pretorin narrative list
        pretorin narrative list --framework fedramp-moderate
    """
    from pretorin.narrative.writer import NarrativeWriter

    writer = NarrativeWriter()
    items = writer.list_local(framework)

    if is_json_mode():
        print_json(
            [
                {
                    "control_id": n.control_id,
                    "framework_id": n.framework_id,
                    "name": n.name,
                    "is_ai_generated": n.is_ai_generated,
                    "platform_synced": n.platform_synced,
                    "path": str(n.path),
                }
                for n in items
            ]
        )
        return

    if not items:
        rprint("[dim]No local narratives found.[/dim]")
        rprint('[dim]Create one with: [bold]pretorin narrative create ac-02 fedramp-moderate -c "content"[/bold][/dim]')
        return

    table = Table(title="Local Narratives", show_header=True, header_style="bold")
    table.add_column("Control", style="cyan")
    table.add_column("Framework")
    table.add_column("Name")
    table.add_column("AI Generated")
    table.add_column("Synced")

    for n in items:
        ai_gen = "[#EAB536]Yes[/#EAB536]" if n.is_ai_generated else "[dim]No[/dim]"
        synced = "[#95D7E0]Yes[/#95D7E0]" if n.platform_synced else "[dim]No[/dim]"
        table.add_row(
            n.control_id.upper(),
            n.framework_id,
            n.name[:40] + "..." if len(n.name) > 40 else n.name,
            ai_gen,
            synced,
        )

    console.print(table)
    rprint(f"\n[dim]Total: {len(items)} narrative(s)[/dim]")


@app.command("push")
def narrative_push(
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be pushed without pushing"),
) -> None:
    """Push local narratives to the Pretorin platform.

    Unsynced narratives (without platform_synced) are pushed.
    Already-synced narratives are skipped.

    Examples:
        pretorin narrative push --dry-run
        pretorin narrative push
    """
    asyncio.run(_push_narratives(dry_run))


async def _push_narratives(dry_run: bool) -> None:
    """Push narratives to platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.narrative.sync import NarrativeSync

    async with PretorianClient() as client:
        require_auth(client)

        sync = NarrativeSync()

        if not is_json_mode():
            mode = "[yellow]DRY RUN[/yellow] " if dry_run else ""
            rprint(f"\n  {ROMEBOT_AI}  {mode}Pushing narratives to platform...\n")

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
            rprint(f"\n[dim]Skipped {len(result.skipped)} already-synced narrative(s)[/dim]")

        if result.errors:
            rprint("\n[bold red]Errors:[/bold red]")
            for err in result.errors:
                rprint(f"  [red]![/red] {err}")

        if not result.pushed and not result.errors:
            rprint("[dim]Nothing to push — all narratives are already synced.[/dim]")


@app.command("push-file")
def narrative_push_file(
    control_id: str = typer.Argument(..., help="Control ID"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    system: str = typer.Argument(..., help="System name or ID"),
    file: Path = typer.Argument(..., help="Narrative file to push", exists=True, readable=True),
) -> None:
    """Push a single narrative file to the platform.

    Reads a markdown/text file and submits it as the implementation
    narrative for a control in a system.
    The narrative must not include markdown headings and should include
    rich markdown elements for auditor readability.

    To generate narratives with AI, use the agent:
        pretorin agent run --skill narrative-generation "Generate narrative for AC-02"

    Examples:
        pretorin narrative push-file ac-02 fedramp-moderate "My System" narrative-ac2.md
    """
    content = file.read_text().strip()
    if not content:
        rprint("[red]File is empty.[/red]")
        raise typer.Exit(1)

    control_id = normalize_control_id(control_id)
    asyncio.run(_push_narrative_file(control_id, framework_id, system, content))


async def _push_narrative_file(
    control_id: str,
    framework_id: str,
    system: str,
    content: str,
) -> None:
    """Push narrative content to the platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.cli.context import resolve_execution_context
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.workflows.markdown_quality import ensure_audit_markdown

    try:
        ensure_audit_markdown(content, artifact_type="narrative")
    except ValueError as e:
        rprint(f"[red]Push failed: {e}[/red]")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        require_auth(client)

        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            system_name = (await client.get_system(system_id)).name
        except PretorianClientError as e:
            rprint(f"[red]Failed to resolve system: {e.message}[/red]")
            raise typer.Exit(1)

        try:
            result = await client.update_narrative(
                system_id=system_id,
                control_id=control_id,
                framework_id=resolved_framework_id,
                narrative=content,
                is_ai_generated=False,
            )
        except PretorianClientError as e:
            rprint(f"[red]Push failed: {e.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(result)
            return

        rprint(f"[#95D7E0]Narrative pushed for {control_id.upper()} in {system_name}[/#95D7E0]")


@app.command("get")
def narrative_get(
    control_id: str = typer.Argument(..., help="Control ID"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Get the current narrative for a control."""
    asyncio.run(_get_narrative(normalize_control_id(control_id), framework_id, system))


async def _get_narrative(
    control_id: str,
    framework_id: str,
    system: str | None,
) -> None:
    """Get current narrative content from the platform."""
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
            narrative = await client.get_narrative(
                system_id=system_id,
                control_id=control_id,
                framework_id=resolved_framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]Fetch failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "control_id": narrative.control_id,
            "framework_id": narrative.framework_id or resolved_framework_id,
            "narrative": narrative.narrative or "",
            "ai_confidence_score": narrative.ai_confidence_score,
            "status": narrative.status,
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(f"\n[bold]System:[/bold] {system_name}")
        rprint(f"[bold]Control:[/bold] {control_id.upper()}")
        rprint(f"[bold]Framework:[/bold] {resolved_framework_id}\n")
        narrative_text = payload["narrative"]
        if narrative_text:
            # Print raw narrative without Rich markup parsing to avoid
            # MarkupError on content like [[/PRETORIN_TODO]] brackets.
            console.print(narrative_text, markup=False)
        else:
            rprint("[dim]No narrative set yet.[/dim]")
