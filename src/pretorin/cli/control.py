"""Control implementation commands for Pretorin."""

from __future__ import annotations

import asyncio

import typer
from rich import print as rprint
from rich.panel import Panel

from pretorin.cli.output import is_json_mode, print_json
from pretorin.mcp.helpers import VALID_CONTROL_STATUSES
from pretorin.utils import normalize_control_id

app = typer.Typer(
    name="control",
    help="Control implementation management.",
    no_args_is_help=True,
)

ROMEBOT_CONTROL = "[#EAB536]\\[°□°][/#EAB536]"

_VALID_STATUSES = VALID_CONTROL_STATUSES


@app.command("status")
def control_status(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    status: str = typer.Argument(
        ...,
        help=(
            "New status: implemented, partially_implemented, planned, in_progress, "
            "ready_to_approve, not_started, not_applicable, inherited"
        ),
    ),
    framework_id: str | None = typer.Option(None, "--framework-id", "-f", help="Framework ID."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Update the implementation status of a control."""
    if status not in _VALID_STATUSES:
        rprint(f"[red]Invalid status: {status}. Choose one of: {', '.join(sorted(_VALID_STATUSES))}[/red]")
        raise typer.Exit(1)

    asyncio.run(_update_status(normalize_control_id(control_id), status, framework_id, system))


@app.command("context")
def control_context(
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02)"),
    framework_id: str | None = typer.Option(None, "--framework-id", "-f", help="Framework ID."),
    system: str | None = typer.Option(None, "--system", "-s", help="System name or ID."),
) -> None:
    """Get rich control context with AI guidance."""
    asyncio.run(_get_context(normalize_control_id(control_id), framework_id, system))


async def _update_status(
    control_id: str,
    status: str,
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
            result = await client.update_control_status(
                system_id=system_id,
                control_id=control_id,
                status=status,
                framework_id=resolved_framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]Status update failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "control_id": control_id,
            "framework_id": resolved_framework_id,
            "status": status,
            "result": result,
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(
            Panel(
                f"  [bold]System:[/bold]    {system_name}\n"
                f"  [bold]Control:[/bold]   {control_id.upper()}\n"
                f"  [bold]Framework:[/bold] {resolved_framework_id}\n"
                f"  [bold]Status:[/bold]    {status}",
                title=f"{ROMEBOT_CONTROL}  Control Status Updated",
                border_style="#95D7E0",
                padding=(1, 2),
            )
        )


async def _get_context(
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
            ctx = await client.get_control_context(
                system_id=system_id,
                control_id=control_id,
                framework_id=resolved_framework_id,
            )
        except PretorianClientError as e:
            rprint(f"[red]Context fetch failed: {e.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "system_name": system_name,
            "framework_id": resolved_framework_id,
            **ctx.model_dump(),
        }
        if is_json_mode():
            print_json(payload)
            return

        rprint(f"\n[bold]System:[/bold] {system_name}")
        rprint(f"[bold]Control:[/bold] {ctx.control_id.upper()}")
        if ctx.title:
            rprint(f"[bold]Title:[/bold] {ctx.title}")
        rprint(f"[bold]Framework:[/bold] {resolved_framework_id}")
        if ctx.status:
            rprint(f"[bold]Status:[/bold] {ctx.status}")

        if ctx.statement:
            rprint(f"\n[bold]Statement:[/bold]\n{ctx.statement}")

        if ctx.objectives:
            rprint("\n[bold]Objectives:[/bold]")
            for obj in ctx.objectives:
                rprint(f"  - {obj}")

        if ctx.guidance:
            rprint(f"\n[bold]Guidance:[/bold]\n{ctx.guidance}")

        if ctx.ai_guidance:
            rprint("\n[bold]AI Guidance:[/bold]")
            for key, value in ctx.ai_guidance.items():
                rprint(f"  [bold]{key}:[/bold] {value}")

        if ctx.implementation_narrative:
            rprint(f"\n[bold]Implementation Narrative:[/bold]\n{ctx.implementation_narrative}")
