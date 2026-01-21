"""API commands for Pretorin CLI."""

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.client import PretorianClient
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError

app = typer.Typer()
console = Console()


def require_auth(client: PretorianClient) -> None:
    """Check that the client is authenticated."""
    if not client.is_configured:
        rprint("[red]Error:[/red] Not logged in. Run 'pretorin login' first.")
        raise typer.Exit(1)


@app.command("list")
def reports_list(
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of reports to show"),
    offset: int = typer.Option(0, "--offset", help="Number of reports to skip"),
) -> None:
    """List compliance reports."""

    async def fetch_reports() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with console.status("Fetching reports..."):
                    reports = await client.list_reports(limit=limit, offset=offset)

                if not reports:
                    rprint("[yellow]No reports found.[/yellow]")
                    return

                table = Table(title="Compliance Reports", show_header=True, header_style="bold")
                table.add_column("ID", style="dim")
                table.add_column("Name")
                table.add_column("Status")
                table.add_column("Issues")
                table.add_column("Created")

                status_colors = {
                    "completed": "green",
                    "running": "yellow",
                    "pending": "blue",
                    "failed": "red",
                }

                for report in reports:
                    color = status_colors.get(report.status.value, "white")
                    table.add_row(
                        report.id[:8] + "...",
                        report.name,
                        f"[{color}]{report.status.value}[/{color}]",
                        str(report.total_issues),
                        report.created_at.strftime("%Y-%m-%d %H:%M"),
                    )

                console.print(table)

            except AuthenticationError as e:
                rprint(f"[red]Authentication error:[/red] {e.message}")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[red]Error:[/red] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_reports())


@app.command("get")
def reports_get(
    report_id: str = typer.Argument(..., help="Report ID"),
) -> None:
    """Get details of a specific compliance report."""

    async def fetch_report() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with console.status("Fetching report..."):
                    report = await client.get_report(report_id)

                rprint(f"\n[bold]Report: {report.name}[/bold]")
                rprint(f"ID: {report.id}")
                rprint(f"Status: {report.status.value}")
                rprint(f"Created: {report.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

                if report.completed_at:
                    rprint(f"Completed: {report.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

                rprint(f"\n[bold]Total Issues: {report.total_issues}[/bold]")

                if report.issues_by_severity:
                    rprint("\nIssues by Severity:")
                    for severity, count in report.issues_by_severity.items():
                        rprint(f"  {severity}: {count}")

                if report.checks:
                    rprint(f"\n[bold]Checks ({len(report.checks)}):[/bold]")

                    table = Table(show_header=True, header_style="bold")
                    table.add_column("File")
                    table.add_column("Status")
                    table.add_column("Issues")

                    for check in report.checks:
                        status_color = "green" if check.status.value == "completed" else "yellow"
                        table.add_row(
                            check.file_name or check.id[:8],
                            f"[{status_color}]{check.status.value}[/{status_color}]",
                            str(len(check.issues)),
                        )

                    console.print(table)

            except NotFoundError:
                rprint(f"[red]Error:[/red] Report not found: {report_id}")
                raise typer.Exit(1)
            except AuthenticationError as e:
                rprint(f"[red]Authentication error:[/red] {e.message}")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[red]Error:[/red] {e.message}")
                raise typer.Exit(1)

    asyncio.run(fetch_report())


@app.command("create")
def reports_create(
    name: str = typer.Option(..., "--name", "-n", help="Name for the report"),
    files: list[str] = typer.Argument(..., help="Files to include in the report"),
) -> None:
    """Create a new compliance report from files."""
    from pathlib import Path

    # Validate files exist
    for file in files:
        if not Path(file).exists():
            rprint(f"[red]Error:[/red] File not found: {file}")
            raise typer.Exit(1)

    async def create_report() -> None:
        async with PretorianClient() as client:
            require_auth(client)

            try:
                with console.status(f"Creating report with {len(files)} file(s)..."):
                    report = await client.create_report(name, files)

                rprint(f"\n[green]Report created successfully![/green]")
                rprint(f"ID: {report.id}")
                rprint(f"Name: {report.name}")
                rprint(f"Status: {report.status.value}")

            except AuthenticationError as e:
                rprint(f"[red]Authentication error:[/red] {e.message}")
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[red]Error:[/red] {e.message}")
                raise typer.Exit(1)

    asyncio.run(create_report())
