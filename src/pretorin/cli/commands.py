"""Framework commands for Pretorin CLI."""

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.animations import AnimationTheme, animated_status
from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError

app = typer.Typer()
console = Console()


def require_auth(client: PretorianClient) -> None:
    """Check that the client is authenticated."""
    if not client.is_configured:
        rprint("[#EAB536][°~°][/#EAB536] Not logged in yet.")
        rprint("[dim]Run [bold]pretorin login[/bold] to get started.[/dim]")
        raise typer.Exit(1)


# =============================================================================
# Framework Commands
# =============================================================================


@app.command("list")
def frameworks_list() -> None:
    """List all available compliance frameworks."""

    async def fetch_frameworks() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Consulting the compliance archives...", AnimationTheme.SEARCHING):
                    result = await client.list_frameworks()

                if not result.frameworks:
                    rprint("[dim]No frameworks found yet.[/dim]")
                    return

                table = Table(
                    title="Available Compliance Frameworks",
                    show_header=True,
                    header_style="bold",
                )
                table.add_column("ID", style="cyan")
                table.add_column("Title")
                table.add_column("Version")
                table.add_column("Tier")
                table.add_column("Families", justify="right")
                table.add_column("Controls", justify="right")

                tier_colors = {
                    "foundational": "#95D7E0",  # Light Turquoise
                    "operational": "#EAB536",  # Gold
                    "strategic": "#FF9010",  # Warm Orange
                }

                for fw in result.frameworks:
                    tier_color = tier_colors.get(fw.tier or "", "white")
                    table.add_row(
                        fw.external_id,
                        fw.title,
                        fw.version,
                        f"[{tier_color}]{fw.tier or '-'}[/{tier_color}]",
                        str(fw.families_count),
                        str(fw.controls_count),
                    )

                console.print(table)
                rprint(f"\n[dim]Total: {result.total} framework(s)[/dim]")

            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_frameworks())


@app.command("get")
def framework_get(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
) -> None:
    """Get details of a specific framework."""

    async def fetch_framework() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Gathering framework details...", AnimationTheme.MARCHING):
                    framework = await client.get_framework(framework_id)

                rprint(
                    Panel(
                        f"[bold]ID:[/bold] {framework.external_id}\n"
                        f"[bold]Title:[/bold] {framework.title}\n"
                        f"[bold]Version:[/bold] {framework.version}\n"
                        f"[bold]OSCAL Version:[/bold] {framework.oscal_version or '-'}\n"
                        f"[bold]Tier:[/bold] {framework.tier or '-'}\n"
                        f"[bold]Category:[/bold] {framework.category or '-'}\n"
                        f"[bold]Published:[/bold] {framework.published or '-'}\n"
                        f"[bold]Last Modified:[/bold] {framework.last_modified or '-'}\n\n"
                        f"[bold]Description:[/bold]\n{framework.description or 'No description available.'}",
                        title=f"Framework: {framework.title}",
                        border_style="#EAB536",
                    )
                )

            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_framework())


@app.command("families")
def framework_families(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
) -> None:
    """List control families for a framework."""

    async def fetch_families() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Gathering control families...", AnimationTheme.MARCHING):
                    families = await client.list_control_families(framework_id)

                if not families:
                    rprint("[dim]No control families found for this framework.[/dim]")
                    return

                table = Table(
                    title=f"Control Families - {framework_id}",
                    show_header=True,
                    header_style="bold",
                )
                table.add_column("ID", style="cyan")
                table.add_column("Title")
                table.add_column("Class")
                table.add_column("Controls", justify="right")

                for family in families:
                    table.add_row(
                        family.id,
                        family.title,
                        family.class_type,
                        str(family.controls_count),
                    )

                console.print(table)
                rprint(f"\n[dim]Total: {len(families)} family(ies)[/dim]")

            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_families())


@app.command("controls")
def framework_controls(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
    family_id: str | None = typer.Option(None, "--family", "-f", help="Filter by control family ID (e.g., ac, au)"),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number of controls to show"),
) -> None:
    """List controls for a framework."""

    async def fetch_controls() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Searching for controls...", AnimationTheme.SEARCHING):
                    controls = await client.list_controls(framework_id, family_id)

                if not controls:
                    rprint("[dim]No controls found for this selection.[/dim]")
                    return

                # Apply limit
                display_controls = controls[:limit]
                total = len(controls)

                table = Table(
                    title=f"Controls - {framework_id}" + (f" (Family: {family_id})" if family_id else ""),
                    show_header=True,
                    header_style="bold",
                )
                table.add_column("ID", style="cyan")
                table.add_column("Title")
                table.add_column("Family")

                for control in display_controls:
                    table.add_row(
                        control.id,
                        control.title[:60] + "..." if len(control.title) > 60 else control.title,
                        control.family_id.upper(),
                    )

                console.print(table)

                if total > limit:
                    rprint(f"\n[dim]Showing {limit} of {total} controls. Use --limit to see more.[/dim]")
                else:
                    rprint(f"\n[dim]Total: {total} control(s)[/dim]")

            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_controls())


@app.command("control")
def control_get(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-1, ac-2)"),
    references: bool = typer.Option(False, "--references", "-r", help="Include guidance and references"),
) -> None:
    """Get details of a specific control."""

    async def fetch_control() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Looking up control details...", AnimationTheme.SEARCHING):
                    control = await client.get_control(framework_id, control_id)

                    refs = None
                    if references:
                        refs = await client.get_control_references(framework_id, control_id)

                # Build control info
                info_lines = [
                    f"[bold]ID:[/bold] {control.id}",
                    f"[bold]Title:[/bold] {control.title}",
                    f"[bold]Class:[/bold] {control.class_type or '-'}",
                    f"[bold]Type:[/bold] {control.control_type or '-'}",
                ]

                if control.ai_guidance:
                    info_lines.append("\n[bold]AI Guidance:[/bold] Available")

                rprint(
                    Panel(
                        "\n".join(info_lines),
                        title=f"Control: {control.id.upper()}",
                        border_style="#EAB536",
                    )
                )

                # Show references if requested
                if refs:
                    if refs.statement:
                        rprint("\n[bold]Statement:[/bold]")
                        rprint(Panel(refs.statement, border_style="dim"))

                    if refs.guidance:
                        rprint("\n[bold]Guidance:[/bold]")
                        rprint(Panel(refs.guidance, border_style="dim"))

                    if refs.objectives:
                        rprint("\n[bold]Objectives:[/bold]")
                        for i, obj in enumerate(refs.objectives[:5], 1):
                            rprint(f"  {i}. {obj}")
                        if len(refs.objectives) > 5:
                            rprint(f"  [dim]... and {len(refs.objectives) - 5} more[/dim]")

                    if refs.related_controls:
                        rprint("\n[bold]Related Controls:[/bold]")
                        related = ", ".join(rc.id.upper() for rc in refs.related_controls[:10])
                        rprint(f"  {related}")

                # Show parameters if present
                if control.params:
                    rprint("\n[bold]Parameters:[/bold]")
                    for param in control.params[:5]:
                        param_id = param.get("id", "?")
                        param_label = param.get("label", param.get("select", {}).get("how-many", ""))
                        rprint(f"  - {param_id}: {param_label}")

                # Show enhancements if present
                if control.controls:
                    rprint(f"\n[bold]Enhancements:[/bold] {len(control.controls)} available")

            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find control [bold]{control_id}[/bold] in {framework_id}")
                rprint(
                    f"[dim]Try [bold]pretorin frameworks controls {framework_id}[/bold] "
                    "to see available controls.[/dim]"
                )
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_control())


@app.command("documents")
def framework_documents(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
) -> None:
    """Get document requirements for a framework."""

    async def fetch_documents() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with animated_status("Gathering document requirements...", AnimationTheme.MARCHING):
                    docs = await client.get_document_requirements(framework_id)

                rprint(f"\n[bold]Document Requirements for {docs.framework_title}[/bold]\n")

                if docs.explicit_documents:
                    rprint("[bold]Required Documents:[/bold]")
                    table = Table(show_header=True, header_style="bold")
                    table.add_column("Document")
                    table.add_column("Description")
                    table.add_column("Required")

                    for doc in docs.explicit_documents:
                        desc = doc.description or "-"
                        desc_display = f"{desc[:50]}..." if len(desc) > 50 else desc
                        required = "[#95D7E0]Yes[/#95D7E0]" if doc.is_required else "[#EAB536]Optional[/#EAB536]"
                        table.add_row(doc.document_name, desc_display, required)
                    console.print(table)

                if docs.implicit_documents:
                    rprint("\n[bold]Implied Documents (from control requirements):[/bold]")
                    for doc in docs.implicit_documents[:10]:
                        rprint(f"  - {doc.document_name}")
                    if len(docs.implicit_documents) > 10:
                        rprint(f"  [dim]... and {len(docs.implicit_documents) - 10} more[/dim]")

                rprint(f"\n[dim]Total: {docs.total} document requirement(s)[/dim]")

            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find document requirements for: {framework_id}")
                rprint(
                    "[dim]This framework may not have document requirements, "
                    "or check the ID with [bold]pretorin frameworks list[/bold].[/dim]"
                )
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_documents())
