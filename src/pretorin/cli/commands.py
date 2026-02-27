"""Framework commands for Pretorin CLI."""

import asyncio
import json
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pretorin.cli.animations import AnimationTheme, animated_status
from pretorin.cli.output import is_json_mode, print_json
from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError
from pretorin.client.models import ComplianceArtifact

app = typer.Typer()
console = Console()


def require_auth(client: PretorianClient) -> None:
    """Check that the client is authenticated."""
    if not client.is_configured:
        rprint("[#EAB536]\\[°~°][/#EAB536] Not logged in yet.")
        rprint("[dim]Run [bold]pretorin login[/bold] to get started.[/dim]")
        raise typer.Exit(1)


# =============================================================================
# Framework Commands
# =============================================================================


@app.command("list")
def frameworks_list() -> None:
    """List all available compliance frameworks.

    Examples:
        pretorin frameworks list
        pretorin --json frameworks list
    """

    async def fetch_frameworks() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    result = await client.list_frameworks()
                    print_json(result)
                    return

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
    """Get details of a specific framework.

    Examples:
        pretorin frameworks get nist-800-53-r5
        pretorin frameworks get fedramp-moderate
        pretorin --json frameworks get nist-800-53-r5
    """

    async def fetch_framework() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    framework = await client.get_framework(framework_id)
                    print_json(framework)
                    return

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
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                rprint("[dim]Example: [bold]pretorin frameworks get fedramp-moderate[/bold][/dim]")
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
    """List control families for a framework.

    Examples:
        pretorin frameworks families nist-800-53-r5
        pretorin frameworks families fedramp-low
        pretorin --json frameworks families fedramp-moderate
    """

    async def fetch_families() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    families = await client.list_control_families(framework_id)
                    print_json(families)
                    return

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
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                rprint("[dim]Example: [bold]pretorin frameworks families fedramp-moderate[/bold][/dim]")
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
    family_id_arg: str | None = typer.Argument(
        None, help="Filter by control family ID (e.g., access-control)", metavar="FAMILY_ID"
    ),
    family_id_opt: str | None = typer.Option(None, "--family", "-f", help="Filter by control family ID"),
    limit: int = typer.Option(0, "--limit", "-n", help="Maximum number of controls to show (0 = all)"),
) -> None:
    """List controls for a framework.

    The family filter can be passed as a positional argument or with --family/-f.

    Examples:
        pretorin frameworks controls fedramp-low
        pretorin frameworks controls fedramp-low access-control
        pretorin frameworks controls fedramp-low -f access-control
        pretorin frameworks controls nist-800-53-r5 --limit 20
        pretorin --json frameworks controls fedramp-moderate
    """
    family_id = family_id_arg or family_id_opt

    async def fetch_controls() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    controls = await client.list_controls(framework_id, family_id)
                    if limit > 0:
                        controls = controls[:limit]
                    print_json(controls)
                    return

                with animated_status("Searching for controls...", AnimationTheme.SEARCHING):
                    controls = await client.list_controls(framework_id, family_id)

                if not controls:
                    rprint("[dim]No controls found for this selection.[/dim]")
                    return

                total = len(controls)
                display_controls = controls[:limit] if limit > 0 else controls

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

                if limit > 0 and total > limit:
                    rprint(f"\n[dim]Showing {limit} of {total} controls. Use --limit 0 to see all.[/dim]")
                else:
                    rprint(f"\n[dim]Total: {total} control(s)[/dim]")

            except NotFoundError:
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                rprint("[dim]Example: [bold]pretorin frameworks controls fedramp-low access-control[/bold][/dim]")
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
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-2, ia-02)"),
    brief: bool = typer.Option(
        False,
        "--brief",
        "-b",
        help="Show only basic control info (skip references and guidance)",
    ),
    _references: bool = typer.Option(
        False,
        "--references",
        "-r",
        hidden=True,
        help="Deprecated: references are now shown by default",
    ),
) -> None:
    """Get details of a specific control.

    By default, shows the full control including statement, guidance, AI guidance,
    and references. Use --brief to show only the basic info panel.

    Examples:
        pretorin frameworks control fedramp-low ia-02
        pretorin frameworks control nist-800-53-r5 ac-2
        pretorin frameworks control fedramp-low ia-02 --brief
        pretorin --json frameworks control fedramp-moderate ac-2
    """

    async def fetch_control() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    control = await client.get_control(framework_id, control_id)
                    refs = await client.get_control_references(framework_id, control_id) if not brief else None
                    data: dict[str, Any] = control.model_dump(mode="json")
                    if refs:
                        data["references"] = refs.model_dump(mode="json")
                    print_json(data)
                    return

                with animated_status("Looking up control details...", AnimationTheme.SEARCHING):
                    control = await client.get_control(framework_id, control_id)
                    refs = None
                    if not brief:
                        refs = await client.get_control_references(framework_id, control_id)

                # Build control info
                info_lines = [
                    f"[bold]ID:[/bold] {control.id}",
                    f"[bold]Title:[/bold] {control.title}",
                    f"[bold]Class:[/bold] {control.class_type or '-'}",
                    f"[bold]Type:[/bold] {control.control_type or '-'}",
                ]

                rprint(
                    Panel(
                        "\n".join(info_lines),
                        title=f"Control: {control.id.upper()}",
                        border_style="#EAB536",
                    )
                )

                # Show references (now default unless --brief)
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

                # Show AI Guidance content if available
                if not brief and control.ai_guidance:
                    rprint("\n[bold #FF9010]AI Guidance:[/bold #FF9010]")
                    _render_ai_guidance(control.ai_guidance)

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
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find control [bold]{control_id}[/bold] in {framework_id}")
                rprint(
                    f"[dim]Try [bold]pretorin frameworks controls {framework_id}[/bold] "
                    "to see available controls.[/dim]"
                )
                rprint(f"[dim]Example: [bold]pretorin frameworks control {framework_id} ac-2[/bold][/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_control())


def _render_ai_guidance(guidance: dict[str, Any]) -> None:
    """Render AI guidance content with appropriate formatting."""
    for key, value in guidance.items():
        heading = key.replace("_", " ").title()
        if isinstance(value, str):
            rprint(Panel(value, title=heading, border_style="#FF9010"))
        elif isinstance(value, list):
            rprint(f"\n  [bold]{heading}:[/bold]")
            for i, item in enumerate(value, 1):
                rprint(f"    {i}. {item}")
        elif isinstance(value, dict):
            rprint(f"\n  [bold]{heading}:[/bold]")
            for k, v in value.items():
                rprint(f"    [bold]{k}:[/bold] {v}")
        else:
            rprint(f"  [bold]{heading}:[/bold] {value}")


@app.command("documents")
def framework_documents(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
) -> None:
    """Get document requirements for a framework.

    Examples:
        pretorin frameworks documents fedramp-moderate
        pretorin --json frameworks documents fedramp-moderate
    """

    async def fetch_documents() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    docs = await client.get_document_requirements(framework_id)
                    print_json(docs)
                    return

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
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find document requirements for: {framework_id}")
                rprint(
                    "[dim]This framework may not have document requirements, "
                    "or check the ID with [bold]pretorin frameworks list[/bold].[/dim]"
                )
                rprint("[dim]Example: [bold]pretorin frameworks documents fedramp-moderate[/bold][/dim]")
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
# New Commands: family, metadata, submit-artifact
# =============================================================================


@app.command("family")
def family_get(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
    family_id: str = typer.Argument(..., help="Family ID (e.g., access-control)"),
) -> None:
    """Get details of a specific control family, including its controls.

    Examples:
        pretorin frameworks family fedramp-low access-control
        pretorin frameworks family nist-800-53-r5 audit-and-accountability
        pretorin --json frameworks family fedramp-moderate access-control
    """

    async def fetch_family() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    family = await client.get_control_family(framework_id, family_id)
                    print_json(family)
                    return

                with animated_status("Gathering family details...", AnimationTheme.MARCHING):
                    family = await client.get_control_family(framework_id, family_id)

                rprint(
                    Panel(
                        f"[bold]ID:[/bold] {family.id}\n"
                        f"[bold]Title:[/bold] {family.title}\n"
                        f"[bold]Class:[/bold] {family.class_type}\n"
                        f"[bold]Controls:[/bold] {len(family.controls)}",
                        title=f"Family: {family.title}",
                        border_style="#EAB536",
                    )
                )

                if family.controls:
                    table = Table(
                        title=f"Controls in {family.title}",
                        show_header=True,
                        header_style="bold",
                    )
                    table.add_column("ID", style="cyan")
                    table.add_column("Title")
                    table.add_column("Class")

                    for ctrl in family.controls:
                        table.add_row(
                            ctrl.id,
                            ctrl.title[:60] + "..." if len(ctrl.title) > 60 else ctrl.title,
                            ctrl.class_type or "-",
                        )

                    console.print(table)

            except NotFoundError:
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find family [bold]{family_id}[/bold] in {framework_id}")
                rprint(
                    f"[dim]Try [bold]pretorin frameworks families {framework_id}[/bold] "
                    "to see available families.[/dim]"
                )
                rprint(f"[dim]Example: [bold]pretorin frameworks family {framework_id} access-control[/bold][/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_family())


@app.command("metadata")
def framework_metadata(
    framework_id: str = typer.Argument(..., help="Framework ID (e.g., nist-800-53-r5)"),
) -> None:
    """Get metadata for all controls in a framework.

    Shows control ID, title, family, and type for every control in the framework.

    Examples:
        pretorin frameworks metadata fedramp-low
        pretorin frameworks metadata nist-800-53-r5
        pretorin --json frameworks metadata fedramp-moderate
    """

    async def fetch_metadata() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    metadata = await client.get_controls_metadata(framework_id)
                    print_json(metadata)
                    return

                with animated_status("Gathering control metadata...", AnimationTheme.SEARCHING):
                    metadata = await client.get_controls_metadata(framework_id)

                if not metadata:
                    rprint("[dim]No control metadata found for this framework.[/dim]")
                    return

                table = Table(
                    title=f"Control Metadata - {framework_id}",
                    show_header=True,
                    header_style="bold",
                )
                table.add_column("Control ID", style="cyan")
                table.add_column("Title")
                table.add_column("Family")
                table.add_column("Type")

                for control_id, meta in sorted(metadata.items()):
                    table.add_row(
                        control_id,
                        meta.title[:60] + "..." if len(meta.title) > 60 else meta.title,
                        meta.family.upper(),
                        meta.type,
                    )

                console.print(table)
                rprint(f"\n[dim]Total: {len(metadata)} control(s)[/dim]")

            except NotFoundError:
                rprint(f"[#EAB536]\\[°︵°][/#EAB536] Couldn't find framework: {framework_id}")
                rprint("[dim]Try [bold]pretorin frameworks list[/bold] to see what's available.[/dim]")
                rprint("[dim]Example: [bold]pretorin frameworks metadata fedramp-low[/bold][/dim]")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_metadata())


@app.command("submit-artifact")
def submit_artifact(
    file_path: Path = typer.Argument(
        ...,
        help="Path to a JSON file containing the compliance artifact",
        exists=True,
        readable=True,
    ),
) -> None:
    """Submit a compliance artifact from a JSON file.

    The JSON file should contain a ComplianceArtifact with framework_id, control_id,
    component definition, and confidence level.

    Examples:
        pretorin frameworks submit-artifact artifact.json
        pretorin --json frameworks submit-artifact artifact.json
    """

    try:
        raw = json.loads(file_path.read_text())
        artifact = ComplianceArtifact(**raw)
    except json.JSONDecodeError as e:
        rprint(f"[#EAB536]\\[°︵°][/#EAB536] Invalid JSON in {file_path}: {e}")
        raise typer.Exit(1)
    except Exception as e:
        rprint(f"[#EAB536]\\[°︵°][/#EAB536] Failed to parse artifact: {e}")
        rprint("[dim]Ensure the file matches the ComplianceArtifact schema.[/dim]")
        raise typer.Exit(1)

    async def do_submit() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                if is_json_mode():
                    result = await client.submit_artifact(artifact)
                    print_json(result)
                    return

                with animated_status("Submitting compliance artifact...", AnimationTheme.MARCHING):
                    result = await client.submit_artifact(artifact)

                artifact_id = result.get("artifact_id", "unknown")
                url = result.get("url")

                info = f"[bold]Artifact ID:[/bold] {artifact_id}"
                if url:
                    info += f"\n[bold]URL:[/bold] {url}"
                info += f"\n[bold]Framework:[/bold] {artifact.framework_id}"
                info += f"\n[bold]Control:[/bold] {artifact.control_id}"

                rprint(
                    Panel(
                        info,
                        title="[#95D7E0]Artifact Submitted[/#95D7E0]",
                        border_style="#95D7E0",
                    )
                )

            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint("[dim]Try running [bold]pretorin login[/bold] again.[/dim]")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(do_submit())
