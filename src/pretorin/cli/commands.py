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
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Title", max_width=60)
                table.add_column("Version", no_wrap=True)
                table.add_column("Tier", no_wrap=True)
                table.add_column("Families", justify="right", no_wrap=True)
                table.add_column("Controls", justify="right", no_wrap=True)

                tier_colors = {
                    "foundational": "#95D7E0",  # Light Turquoise
                    "operational": "#EAB536",  # Gold
                    "strategic": "#FF9010",  # Warm Orange
                }

                for fw in result.frameworks:
                    tier_color = tier_colors.get(fw.tier or "", "white")
                    title = fw.title
                    if len(title) > 60:
                        title = title[:57] + "..."
                    table.add_row(
                        fw.external_id,
                        title,
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
                table.add_column("ID", style="cyan", no_wrap=True)
                table.add_column("Title", max_width=50)
                table.add_column("Class", no_wrap=True)
                table.add_column("Controls", justify="right", no_wrap=True)

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
    control_id: str = typer.Argument(..., help="Control ID (e.g., ac-02, ia-02)"),
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
        pretorin frameworks control nist-800-53-r5 ac-02
        pretorin frameworks control fedramp-low ia-02 --brief
        pretorin --json frameworks control fedramp-moderate ac-02
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
                rprint(f"[dim]Example: [bold]pretorin frameworks control {framework_id} ac-02[/bold][/dim]")
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


# =============================================================================
# Custom Framework Authoring (RFC: GH #90)
#
# The canonical upload artifact is `unified.json`. `_index.json` is NOT an
# upload format — the platform's revision lifecycle expects the full unified
# artifact. These commands build, validate, and ship that artifact.
# =============================================================================


@app.command("init-custom")
def init_custom(
    framework_id: str = typer.Argument(..., help="New framework ID (e.g., acme-soc2-tailored)"),
    title: str | None = typer.Option(None, "--title", "-t", help="Human-readable title"),
    output: Path = typer.Option(
        Path("unified.json"),
        "--output",
        "-o",
        help="Output path for the scaffolded unified.json",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite output if it exists"),
) -> None:
    """Scaffold a minimal valid unified.json for a new custom framework.

    Writes a small, schema-valid template with one sample family and one
    sample control. Edit the output, run `validate-custom` to verify, then
    `upload-custom` to push to the platform.

    Examples:
        pretorin frameworks init-custom acme-soc2-tailored
        pretorin frameworks init-custom acme-iso27001 -t "Acme ISO 27001" -o acme.json
    """
    from pretorin.frameworks.templates import minimal_unified

    if output.exists() and not force:
        rprint(f"[#EAB536]\\[°︵°][/#EAB536] {output} already exists. Use --force to overwrite.")
        raise typer.Exit(1)

    artifact = minimal_unified(framework_id, title)
    output.write_text(json.dumps(artifact, indent=2) + "\n")

    if is_json_mode():
        print_json({"output": str(output), "framework_id": framework_id})
        return

    rprint(
        Panel(
            f"[bold]Output:[/bold] {output}\n"
            f"[bold]Framework ID:[/bold] {framework_id}\n"
            f"[bold]Format:[/bold] unified.json\n\n"
            "[dim]Next steps:[/dim]\n"
            f"  [dim]1. Edit {output} — fill in metadata, families, and controls[/dim]\n"
            f"  [dim]2. [bold]pretorin frameworks validate-custom {output}[/bold][/dim]\n"
            f"  [dim]3. [bold]pretorin frameworks upload-custom {output}[/bold][/dim]",
            title="[#95D7E0]Scaffolded custom framework[/#95D7E0]",
            border_style="#95D7E0",
        )
    )


@app.command("validate-custom")
def validate_custom(
    file_path: Path = typer.Argument(
        ...,
        help="Path to a unified.json artifact",
        exists=True,
        readable=True,
    ),
) -> None:
    """Validate a unified.json artifact against the bundled JSON Schema.

    Local pre-flight check — the platform runs the authoritative validator
    on upload. Use this to catch structural issues fast before paying the
    network round-trip.

    Examples:
        pretorin frameworks validate-custom unified.json
        pretorin --json frameworks validate-custom unified.json
    """
    from pretorin.frameworks.validate import validate_unified_file

    result = validate_unified_file(file_path)

    if is_json_mode():
        print_json(
            {
                "valid": result.valid,
                "errors": [{"path": e.path, "message": e.message} for e in result.errors],
            }
        )
        if not result.valid:
            raise typer.Exit(1)
        return

    if result.valid:
        rprint(
            Panel(
                f"[bold]File:[/bold] {file_path}\n"
                "[#95D7E0]✓[/#95D7E0] Schema validation passed.\n\n"
                "[dim]Note: this is a local pre-flight check. The platform runs the[/dim]\n"
                "[dim]authoritative validator on upload — additional issues may surface there.[/dim]",
                title="[#95D7E0]Valid unified.json[/#95D7E0]",
                border_style="#95D7E0",
            )
        )
        return

    rprint(f"[#FF9010]✗[/#FF9010] Schema validation failed: [bold]{file_path}[/bold]\n")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Path", style="cyan", max_width=40)
    table.add_column("Issue")
    for err in result.errors[:50]:
        table.add_row(err.path or "(root)", err.message)
    console.print(table)
    if len(result.errors) > 50:
        rprint(f"\n[dim]... and {len(result.errors) - 50} more[/dim]")
    raise typer.Exit(1)


@app.command("build-custom")
def build_custom(
    input_path: Path = typer.Argument(
        ...,
        help="Path to source catalog (unified.json, OSCAL, or known custom format)",
        exists=True,
        readable=True,
    ),
    framework_id: str = typer.Option(
        ...,
        "--framework-id",
        "-f",
        help="Framework ID for the resulting unified.json",
    ),
    output: Path = typer.Option(
        Path("unified.json"),
        "--output",
        "-o",
        help="Output path for the resulting unified.json",
    ),
    force: bool = typer.Option(False, "--force", help="Overwrite output if it exists"),
) -> None:
    """Normalize a source catalog into uploadable unified.json.

    Auto-detects the input shape:

    \b
    - Already a unified.json → passthrough (re-tagged with --framework-id)
    - OSCAL catalog → converted via oscal_to_unified
    - Known custom catalog → converted via custom_to_unified

    Examples:
        pretorin frameworks build-custom catalog.json -f acme-soc2 -o unified.json
        pretorin frameworks build-custom oscal-catalog.json -f acme-iso27001
    """
    from pretorin.frameworks import custom_to_unified, oscal_to_unified
    from pretorin.frameworks.validate import validate_unified

    if output.exists() and not force:
        rprint(f"[#EAB536]\\[°︵°][/#EAB536] {output} already exists. Use --force to overwrite.")
        raise typer.Exit(1)

    try:
        raw = json.loads(input_path.read_text())
    except json.JSONDecodeError as e:
        rprint(f"[#EAB536]\\[°︵°][/#EAB536] Invalid JSON in {input_path}: {e}")
        raise typer.Exit(1)

    # Detect input shape
    if oscal_to_unified.is_oscal_format(raw):
        unified = oscal_to_unified.convert(raw, framework_id)
        source = "OSCAL catalog"
    elif raw.get("source_format") in ("oscal", "custom") and "framework_id" in raw and "families" in raw:
        # Already unified — passthrough but re-tag with the requested framework_id
        unified = dict(raw)
        unified["framework_id"] = framework_id
        source = "unified.json (passthrough)"
    else:
        try:
            unified = custom_to_unified.convert(raw, framework_id)
        except custom_to_unified.UnknownCustomFormatError as e:
            rprint(f"[#FF9010]→[/#FF9010] {e}")
            rprint("[dim]Supported sources: unified.json, OSCAL catalog, or a known custom catalog shape.[/dim]")
            raise typer.Exit(1)
        source = f"custom catalog ({unified.get('custom_format_type', 'unknown')})"

    # Local validate before writing — surface issues early
    result = validate_unified(unified)
    output.write_text(json.dumps(unified, indent=2) + "\n")

    if is_json_mode():
        print_json(
            {
                "output": str(output),
                "framework_id": framework_id,
                "source": source,
                "valid": result.valid,
                "errors": [{"path": e.path, "message": e.message} for e in result.errors],
            }
        )
        if not result.valid:
            raise typer.Exit(1)
        return

    family_count = len(unified.get("families", []))
    control_count = sum(len(fam.get("controls", [])) for fam in unified.get("families", []))

    border = "#95D7E0" if result.valid else "#FF9010"
    status = "[#95D7E0]✓ valid[/#95D7E0]" if result.valid else "[#FF9010]✗ invalid (see below)[/#FF9010]"

    rprint(
        Panel(
            f"[bold]Output:[/bold] {output}\n"
            f"[bold]Framework ID:[/bold] {framework_id}\n"
            f"[bold]Source:[/bold] {source}\n"
            f"[bold]Families:[/bold] {family_count}\n"
            f"[bold]Controls:[/bold] {control_count}\n"
            f"[bold]Schema:[/bold] {status}",
            title="[#95D7E0]Built unified.json[/#95D7E0]",
            border_style=border,
        )
    )

    if not result.valid:
        for err in result.errors[:20]:
            rprint(f"  [#FF9010]•[/#FF9010] {err}")
        if len(result.errors) > 20:
            rprint(f"  [dim]... and {len(result.errors) - 20} more[/dim]")
        raise typer.Exit(1)
