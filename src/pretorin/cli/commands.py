"""Framework commands for Pretorin CLI."""

import asyncio
import json
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError
from pretorin.mcp.analysis_prompts import get_available_controls, get_control_summary

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
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Consulting the compliance archives...[/dim]"):
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
                    "operational": "#EAB536",    # Gold
                    "strategic": "#FF9010",      # Warm Orange
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
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Gathering framework details...[/dim]"):
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
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Gathering control families...[/dim]"):
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
    family_id: str | None = typer.Option(
        None, "--family", "-f", help="Filter by control family ID (e.g., ac, au)"
    ),
    limit: int = typer.Option(50, "--limit", "-n", help="Maximum number of controls to show"),
) -> None:
    """List controls for a framework."""

    async def fetch_controls() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Gathering controls...[/dim]"):
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
    references: bool = typer.Option(
        False, "--references", "-r", help="Include guidance and references"
    ),
) -> None:
    """Get details of a specific control."""

    async def fetch_control() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Looking up control details...[/dim]"):
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
                    info_lines.append(f"\n[bold]AI Guidance:[/bold] Available")

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
                rprint(f"[dim]Try [bold]pretorin frameworks controls {framework_id}[/bold] to see available controls.[/dim]")
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
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Gathering document requirements...[/dim]"):
                    docs = await client.get_document_requirements(framework_id)

                rprint(f"\n[bold]Document Requirements for {docs.framework_title}[/bold]\n")

                if docs.explicit_documents:
                    rprint("[bold]Required Documents:[/bold]")
                    table = Table(show_header=True, header_style="bold")
                    table.add_column("Document")
                    table.add_column("Description")
                    table.add_column("Required")

                    for doc in docs.explicit_documents:
                        table.add_row(
                            doc.document_name,
                            (doc.description or "-")[:50] + "..." if doc.description and len(doc.description) > 50 else (doc.description or "-"),
                            "[#95D7E0]Yes[/#95D7E0]" if doc.is_required else "[#EAB536]Optional[/#EAB536]",
                        )
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
                rprint("[dim]This framework may not have document requirements, or check the ID with [bold]pretorin frameworks list[/bold].[/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_documents())


# =============================================================================
# Analyze Command
# =============================================================================


@app.command("analyze")
def analyze(
    framework_id: str = typer.Option(
        "fedramp-moderate",
        "--framework",
        "-f",
        help="Framework ID (e.g., fedramp-moderate, nist-800-53-r5)",
    ),
    controls: str = typer.Option(
        None,
        "--controls",
        "-c",
        help="Comma-separated control IDs (e.g., ac-2,au-2,ia-2). Defaults to all available.",
    ),
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to code directory to analyze",
    ),
    output: str = typer.Option(
        None,
        "--output",
        "-o",
        help="Save artifacts to local JSON file instead of API",
    ),
) -> None:
    """Start a compliance analysis session.

    This command prepares your environment for AI-assisted compliance analysis.
    It validates the framework and controls, then prints instructions for
    using the Pretorin MCP tools to analyze your code.
    """

    async def run_analyze() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            # Parse controls
            if controls:
                control_list = [c.strip().lower() for c in controls.split(",")]
            else:
                control_list = get_available_controls()

            # Validate framework exists
            try:
                with console.status("[#EAB536][°~°][/#EAB536] [dim]Validating framework...[/dim]"):
                    framework = await client.get_framework(framework_id)
            except NotFoundError:
                rprint(f"[#EAB536][°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                raise typer.Exit(1)

            # Resolve path
            code_path = Path(path).resolve()
            if not code_path.exists():
                rprint(f"[#EAB536][°︵°][/#EAB536] Path not found: {path}")
                raise typer.Exit(1)

            # Show analysis session info
            rprint()
            rprint(
                Panel(
                    f"[bold]Framework:[/bold] {framework.title} ({framework_id})\n"
                    f"[bold]Controls:[/bold] {', '.join(c.upper() for c in control_list)}\n"
                    f"[bold]Code Path:[/bold] {code_path}\n"
                    f"[bold]Output:[/bold] {'Local file: ' + output if output else 'Pretorin API'}",
                    title="[#EAB536]Compliance Analysis Session[/#EAB536]",
                    border_style="#EAB536",
                )
            )

            # Show controls with available guidance
            rprint("\n[bold]Controls to Analyze:[/bold]")
            available = get_available_controls()

            table = Table(show_header=True, header_style="bold")
            table.add_column("Control", style="cyan")
            table.add_column("Description")
            table.add_column("Guidance")

            for control_id in control_list:
                summary = get_control_summary(control_id)
                has_guidance = control_id.lower() in available
                table.add_row(
                    control_id.upper(),
                    summary or "Unknown control",
                    "[#95D7E0]Available[/#95D7E0]" if has_guidance else "[dim]Generic[/dim]",
                )

            console.print(table)

            # Print instructions
            rprint()
            rprint(
                Panel(
                    """[bold]How to use with your AI assistant:[/bold]

1. [#FF9010]Read the schema:[/#FF9010]
   Ask your AI to read the MCP resource: [cyan]analysis://schema[/cyan]

2. [#FF9010]Read control guidance:[/#FF9010]
   For each control, read: [cyan]analysis://control/{framework_id}/{control_id}[/cyan]
   Example: [cyan]analysis://control/fedramp-moderate/ac-2[/cyan]

3. [#FF9010]Analyze your code:[/#FF9010]
   Have your AI search and read relevant files in your codebase

4. [#FF9010]Validate artifact:[/#FF9010]
   Use [cyan]pretorin_validate_artifact[/cyan] to check your artifact

5. [#FF9010]Submit artifact:[/#FF9010]
   Use [cyan]pretorin_submit_artifact[/cyan] to submit for review

[bold]Example prompt for your AI:[/bold]
"Analyze my code at {path} for {framework} compliance, focusing on
control {control}. Read the analysis guidance from the Pretorin MCP
resources, then examine my code and create a compliance artifact."
""".format(
                        path=code_path,
                        framework=framework_id,
                        control=control_list[0].upper() if control_list else "AC-2",
                    ),
                    title="[#95D7E0]Next Steps[/#95D7E0]",
                    border_style="#95D7E0",
                )
            )

            # If output file specified, create a session file
            if output:
                session_data = {
                    "framework_id": framework_id,
                    "framework_title": framework.title,
                    "controls": control_list,
                    "code_path": str(code_path),
                    "output_file": output,
                    "artifacts": [],
                }
                output_path = Path(output)
                output_path.write_text(json.dumps(session_data, indent=2))
                rprint(f"\n[#95D7E0]✓[/#95D7E0] Session file created: {output}")
                rprint("[dim]Your AI can append artifacts to this file instead of calling the API.[/dim]")

            rprint()
            rprint("[#EAB536][°◡°][/#EAB536] Ready for analysis! Ask your AI assistant to get started.")

    asyncio.run(run_analyze())
