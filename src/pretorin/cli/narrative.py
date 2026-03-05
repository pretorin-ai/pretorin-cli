"""Narrative CLI commands for Pretorin."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint

from pretorin.cli.output import is_json_mode, print_json
from pretorin.utils import normalize_control_id

app = typer.Typer(
    name="narrative",
    help="Narrative management. Use 'pretorin agent run --skill narrative-generation' to generate narratives.",
    no_args_is_help=True,
)

ROMEBOT_AI = "[#EAB536]\\[°~°][/#EAB536]"


@app.command("get")
def narrative_get(
    control_id: str = typer.Argument(..., help="Control ID"),
    framework_id: str = typer.Argument(..., help="Framework ID"),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Get the current narrative for a control."""
    asyncio.run(_get_narrative(normalize_control_id(control_id), framework_id, system))


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
    The narrative must not include markdown headings and should include
    rich markdown elements for auditor readability.

    To generate narratives with AI, use the agent:
        pretorin agent run --skill narrative-generation "Generate narrative for AC-02"

    Examples:
        pretorin narrative push ac-02 fedramp-moderate "My System" narrative-ac2.md
    """
    content = file.read_text().strip()
    if not content:
        rprint("[red]File is empty.[/red]")
        raise typer.Exit(1)

    control_id = normalize_control_id(control_id)
    asyncio.run(_push_narrative(control_id, framework_id, system, content))


async def _push_narrative(
    control_id: str,
    framework_id: str,
    system: str,
    content: str,
) -> None:
    """Push narrative content to the platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.workflows.compliance_updates import resolve_system
    from pretorin.workflows.markdown_quality import ensure_audit_markdown

    try:
        ensure_audit_markdown(content, artifact_type="narrative")
    except ValueError as e:
        rprint(f"[red]Push failed: {e}[/red]")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        require_auth(client)

        try:
            system_id, system_name = await resolve_system(client, system)
        except PretorianClientError as e:
            rprint(f"[red]Failed to resolve system: {e.message}[/red]")
            raise typer.Exit(1)

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

        rprint(f"[#95D7E0]Narrative pushed for {control_id.upper()} in {system_name}[/#95D7E0]")


async def _get_narrative(
    control_id: str,
    framework_id: str,
    system: str | None,
) -> None:
    """Get current narrative content from the platform."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.workflows.compliance_updates import resolve_system

    async with PretorianClient() as client:
        require_auth(client)

        try:
            system_id, system_name = await resolve_system(client, system)
            narrative = await client.get_narrative(
                system_id=system_id,
                control_id=control_id,
                framework_id=framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]Fetch failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "control_id": narrative.control_id,
            "framework_id": narrative.framework_id or framework_id,
            "narrative": narrative.narrative or "",
            "ai_confidence_score": narrative.ai_confidence_score,
            "status": narrative.status,
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(f"\n[bold]System:[/bold] {system_name}")
        rprint(f"[bold]Control:[/bold] {control_id.upper()}")
        rprint(f"[bold]Framework:[/bold] {framework_id}\n")
        rprint(payload["narrative"] or "[dim]No narrative set yet.[/dim]")
