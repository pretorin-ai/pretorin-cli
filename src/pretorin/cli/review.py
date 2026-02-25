"""Review commands for the Pretorin CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from pretorin.cli.context import resolve_context
from pretorin.cli.output import is_json_mode, print_json

console = Console()

app = typer.Typer(
    name="review",
    help="Review local artifacts against compliance controls.",
    no_args_is_help=True,
)

ROMEBOT_WORKING = "[#EAB536][°~°][/#EAB536]"
ROMEBOT_DONE = "[#EAB536]\\[°◡°]/[/#EAB536]"

EARLY_ACCESS_MSG = (
    "\n[dim]Your artifacts were saved locally. Want centralized tracking, "
    "AI analysis, and audit trails?[/dim]\n"
    "[dim]Sign up for early access: [link=https://pretorin.com/early-access/]"
    "https://pretorin.com/early-access/[/link][/dim]"
)

# Common code file extensions to discover for review
CODE_EXTENSIONS = (
    "*.py", "*.js", "*.ts", "*.tsx", "*.jsx",
    "*.go", "*.rs", "*.java", "*.rb", "*.php",
    "*.yaml", "*.yml", "*.json", "*.toml",
    "*.tf", "*.hcl",
    "*.sh", "*.bash",
    "*.md", "*.txt",
    "Dockerfile", "Makefile",
)


def _discover_files(path: Path) -> list[Path]:
    """Discover relevant code files at the given path."""
    files: list[Path] = []
    if path.is_file():
        return [path]

    for ext in CODE_EXTENSIONS:
        files.extend(path.glob(f"**/{ext}"))

    # Deduplicate and sort
    seen: set[Path] = set()
    unique: list[Path] = []
    for f in sorted(files):
        resolved = f.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(f)
    return unique


@app.command("run")
def run(
    control_id: str = typer.Option(
        ...,
        "--control-id", "-c",
        help="Control ID to review against (e.g., ac-2, sc-7).",
    ),
    framework_id: str | None = typer.Option(
        None,
        "--framework-id", "-f",
        help="Framework ID (uses active context if not set).",
    ),
    system: str | None = typer.Option(
        None,
        "--system", "-s",
        help="System name or ID (uses active context if not set).",
    ),
    path: str = typer.Option(
        ".",
        "--path", "-p",
        help="Path to files to review.",
    ),
    local: bool = typer.Option(
        False,
        "--local",
        help="Force local-only output (no API calls for implementation data).",
    ),
    output_dir: str = typer.Option(
        ".pretorin/reviews",
        "--output-dir", "-o",
        help="Output directory for local review artifacts.",
    ),
) -> None:
    """Review local artifacts against a compliance control.

    Fetches control requirements and displays them alongside your
    local codebase context. Use --local to save control context
    as markdown files without requiring a system.

    Examples:
        pretorin review run -c ac-2
        pretorin review run -c sc-7 -f fedramp-moderate --path ./src
        pretorin review run -c ac-2 --local -o ./compliance-notes
    """
    asyncio.run(_run_review(
        control_id=control_id,
        framework_id=framework_id,
        system=system,
        path=path,
        local=local,
        output_dir=output_dir,
    ))


async def _run_review(
    control_id: str,
    framework_id: str | None,
    system: str | None,
    path: str,
    local: bool,
    output_dir: str,
) -> None:
    """Run the review workflow."""
    from pretorin.client.api import PretorianClient, PretorianClientError

    # --- Resolve context ---
    system_id: str | None = None
    resolved_framework_id: str | None = framework_id

    if not local:
        try:
            system_id, resolved_framework_id = resolve_context(
                system=system, framework=framework_id,
            )
        except SystemExit:
            # Context resolution failed — fall back to local mode
            if framework_id:
                resolved_framework_id = framework_id
                local = True
                if not is_json_mode():
                    rprint(
                        f"\n  {ROMEBOT_WORKING}  No system context — falling back to local mode.\n"
                    )
            else:
                # No framework at all — re-raise
                rprint("[red]No framework specified and no active context.[/red]")
                rprint("Use [bold]--framework-id[/bold] or run [bold]pretorin context set[/bold] first.")
                raise typer.Exit(1)
    else:
        # Local mode: framework is required
        if not resolved_framework_id:
            rprint("[red]--framework-id is required in --local mode.[/red]")
            raise typer.Exit(1)

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' or 'pretorin config set api-key <key>' first.[/red]")
            raise typer.Exit(1)

        # --- Fetch control details ---
        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_WORKING}  Fetching control {control_id.upper()} from {resolved_framework_id}...\n")

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("Loading control requirements...", total=None)
                control_detail = await client.get_control(resolved_framework_id, control_id)
                control_refs = await client.get_control_references(resolved_framework_id, control_id)
        except PretorianClientError as e:
            rprint(f"[red]Failed to fetch control: {e.message}[/red]")
            raise typer.Exit(1)

        control_title = getattr(control_detail, "title", control_id.upper())
        statement = getattr(control_refs, "statement", None) or getattr(control_detail, "statement", "N/A")
        guidance = getattr(control_refs, "guidance", None) or getattr(control_detail, "guidance", "N/A")

        # --- Discover local files ---
        review_path = Path(path)
        files = _discover_files(review_path)

        # --- Display control info ---
        if not is_json_mode():
            # Truncate guidance for display
            guidance_display = str(guidance)
            if len(guidance_display) > 500:
                guidance_display = guidance_display[:500] + "..."

            rprint(Panel(
                f"  [bold]Control:[/bold]   {control_id.upper()}: {control_title}\n\n"
                f"  [bold]Statement:[/bold]\n  {statement}\n\n"
                f"  [bold]Guidance:[/bold]\n  {guidance_display}",
                title=f"{ROMEBOT_DONE}  Control Requirements",
                border_style="#FF9010",
                padding=(1, 2),
            ))

            rprint(f"\n  [dim]Found {len(files)} file(s) at {review_path.resolve()}[/dim]\n")

        # --- Fetch implementation status if system context available ---
        implementation = None
        if system_id and not local:
            try:
                with Progress(
                    SpinnerColumn(style="#EAB536"),
                    TextColumn("[progress.description]{task.description}"),
                    console=console,
                    disable=is_json_mode(),
                ) as progress:
                    progress.add_task("Fetching current implementation status...", total=None)
                    implementation = await client.get_control_implementation(
                        system_id, control_id, resolved_framework_id,
                    )
            except PretorianClientError:
                # Not found or no implementation yet — that's fine
                pass

            if implementation and not is_json_mode():
                impl_status = getattr(implementation, "status", "not_started")
                impl_narrative = getattr(implementation, "narrative", None) or ""
                evidence_count = getattr(implementation, "evidence_count", 0)

                # Truncate narrative for display
                narrative_display = impl_narrative
                if len(narrative_display) > 300:
                    narrative_display = narrative_display[:300] + "..."

                rprint(Panel(
                    f"  [bold]Status:[/bold]         {impl_status}\n"
                    f"  [bold]Evidence items:[/bold] {evidence_count}\n"
                    f"  [bold]Narrative:[/bold]      "
                    f"{narrative_display if narrative_display else '[dim]not yet generated[/dim]'}",
                    title="Current Implementation",
                    border_style="#95D7E0",
                    padding=(1, 2),
                ))

        # --- AI review hint ---
        if not is_json_mode():
            rprint(
                "  [dim]For full AI-powered security review, run:[/dim]\n"
                f"  [bold]pretorin agent run --skill security-review --control {control_id}[/bold]\n"
                "  [dim]Or use MCP tools in your editor for inline analysis.[/dim]\n"
            )

        # --- Local-only: save control context to file ---
        if local:
            output_path = Path(output_dir) / resolved_framework_id / f"{control_id}.md"
            output_path.parent.mkdir(parents=True, exist_ok=True)

            content = (
                f"# {control_id.upper()}: {control_title}\n\n"
                f"## Statement\n{statement}\n\n"
                f"## Guidance\n{guidance}\n"
            )
            output_path.write_text(content)

            if is_json_mode():
                print_json({
                    "control_id": control_id,
                    "framework_id": resolved_framework_id,
                    "output_path": str(output_path),
                    "files_found": len(files),
                })
            else:
                rprint(Panel(
                    f"  [bold]Saved:[/bold] {output_path}",
                    title=f"{ROMEBOT_DONE}  Local Review Artifact",
                    border_style="#95D7E0",
                    padding=(1, 2),
                ))
                rprint(EARLY_ACCESS_MSG)
        else:
            if is_json_mode():
                result: dict = {
                    "control_id": control_id,
                    "framework_id": resolved_framework_id,
                    "system_id": system_id,
                    "control_title": control_title,
                    "statement": str(statement),
                    "files_found": len(files),
                }
                if implementation:
                    result["implementation_status"] = getattr(implementation, "status", None)
                    result["evidence_count"] = getattr(implementation, "evidence_count", 0)
                print_json(result)


@app.command("status")
def status(
    control_id: str = typer.Option(
        ...,
        "--control-id", "-c",
        help="Control ID (e.g., ac-2, sc-7).",
    ),
    system: str | None = typer.Option(
        None,
        "--system", "-s",
        help="System name or ID (uses active context if not set).",
    ),
    framework_id: str | None = typer.Option(
        None,
        "--framework-id", "-f",
        help="Framework ID (uses active context if not set).",
    ),
) -> None:
    """Show the implementation status for a specific control.

    Examples:
        pretorin review status -c ac-2
        pretorin review status -c sc-7 -f fedramp-moderate -s my-system
    """
    asyncio.run(_review_status(
        control_id=control_id,
        system=system,
        framework_id=framework_id,
    ))


async def _review_status(
    control_id: str,
    system: str | None,
    framework_id: str | None,
) -> None:
    """Fetch and display implementation status for a control."""
    from pretorin.client.api import PretorianClient, PretorianClientError

    system_id, resolved_framework_id = resolve_context(
        system=system, framework=framework_id,
    )

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint("[red]Not configured. Run 'pretorin login' or 'pretorin config set api-key <key>' first.[/red]")
            raise typer.Exit(1)

        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_WORKING}  Fetching implementation for {control_id.upper()}...\n")

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("Loading implementation status...", total=None)
                implementation = await client.get_control_implementation(
                    system_id, control_id, resolved_framework_id,
                )
        except PretorianClientError as e:
            if is_json_mode():
                print_json({"error": e.message, "control_id": control_id})
            else:
                rprint(f"[red]Failed to fetch implementation: {e.message}[/red]")
            raise typer.Exit(1)

        impl_status = getattr(implementation, "status", "not_started")
        narrative = getattr(implementation, "narrative", None) or ""
        evidence_count = getattr(implementation, "evidence_count", 0)
        last_reviewed = getattr(implementation, "last_reviewed", None)

        if is_json_mode():
            print_json({
                "control_id": control_id,
                "framework_id": resolved_framework_id,
                "system_id": system_id,
                "status": impl_status,
                "narrative": narrative,
                "evidence_count": evidence_count,
                "last_reviewed": str(last_reviewed) if last_reviewed else None,
            })
            return

        # Truncate narrative for display
        narrative_display = narrative
        if len(narrative_display) > 500:
            narrative_display = narrative_display[:500] + "..."

        status_colors = {
            "not_started": "#888888",
            "in_progress": "#EAB536",
            "implemented": "#95D7E0",
            "complete": "#4CAF50",
        }
        status_color = status_colors.get(impl_status, "#888888")

        panel_content = (
            f"  [bold]Control:[/bold]        {control_id.upper()}\n"
            f"  [bold]Framework:[/bold]      {resolved_framework_id}\n"
            f"  [bold]Status:[/bold]         [{status_color}]{impl_status}[/{status_color}]\n"
            f"  [bold]Evidence items:[/bold] {evidence_count}\n"
            f"  [bold]Last reviewed:[/bold]  {last_reviewed or '[dim]never[/dim]'}\n\n"
            f"  [bold]Narrative:[/bold]\n"
            f"  {narrative_display if narrative_display else '[dim]No narrative generated yet.[/dim]'}"
        )

        rprint(Panel(
            panel_content,
            title=f"{ROMEBOT_DONE}  Implementation Status",
            border_style="#95D7E0",
            padding=(1, 2),
        ))
