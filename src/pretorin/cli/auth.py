"""Authentication CLI commands for Pretorin."""

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

from pretorin.client import PretorianClient, clear_credentials, store_credentials
from pretorin.client.api import AuthenticationError, PretorianClientError
from pretorin.client.config import Config

app = typer.Typer()
console = Console()


@app.command()
def login(
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key (will prompt if not provided)",
        hide_input=True,
    ),
    api_base_url: str | None = typer.Option(
        None,
        "--api-url",
        help="Custom API base URL (for self-hosted instances)",
    ),
) -> None:
    """Authenticate with the Pretorin API.

    Get your API key from the Pretorin platform at https://platform.pretorin.com/settings/developer
    """
    if api_key is None:
        rprint("\n[bold]Pretorin CLI Login[/bold]")
        rprint(
            "Get your API key from: [link=https://platform.pretorin.com/settings/developer]https://platform.pretorin.com/settings/developer[/link]\n"
        )
        api_key = typer.prompt("Enter your API key", hide_input=True)

    if not api_key:
        rprint("[red]Error:[/red] API key is required")
        raise typer.Exit(1)

    async def validate_and_store() -> None:
        client = PretorianClient(api_key=api_key, api_base_url=api_base_url)
        try:
            with console.status("Validating API key..."):
                await client.validate_api_key()

            # Store credentials after successful validation
            store_credentials(api_key, api_base_url)

            rprint("\n[green]Successfully authenticated![/green]")
            rprint(
                Panel(
                    "[bold]Status:[/bold] Connected\n"
                    f"[bold]API URL:[/bold] {client._api_base_url}",
                    title="Logged in",
                    border_style="green",
                )
            )

        except AuthenticationError as e:
            rprint(f"\n[red]Authentication failed:[/red] {e.message}")
            raise typer.Exit(1)
        except PretorianClientError as e:
            rprint(f"\n[red]Error:[/red] {e.message}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(validate_and_store())


@app.command()
def logout() -> None:
    """Clear stored credentials and log out."""
    config = Config()

    if not config.is_configured:
        rprint("[yellow]You are not currently logged in.[/yellow]")
        return

    clear_credentials()
    rprint("[green]Successfully logged out.[/green]")


@app.command()
def whoami() -> None:
    """Display current authentication status and configuration."""
    config = Config()

    if not config.is_configured:
        rprint("[yellow]Not logged in.[/yellow] Run 'pretorin login' to authenticate.")
        raise typer.Exit(1)

    async def check_auth() -> None:
        async with PretorianClient() as client:
            try:
                with console.status("Checking authentication..."):
                    await client.validate_api_key()
                    frameworks = await client.list_frameworks()

                # Mask the API key for display
                api_key = config.api_key or ""
                masked_key = (
                    f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                )

                rprint(
                    Panel(
                        f"[bold]Status:[/bold] [green]Authenticated[/green]\n"
                        f"[bold]API Key:[/bold] {masked_key}\n"
                        f"[bold]API URL:[/bold] {client._api_base_url}\n"
                        f"[bold]Frameworks Available:[/bold] {frameworks.total}",
                        title="Current Session",
                        border_style="blue",
                    )
                )

            except AuthenticationError as e:
                rprint(f"[red]Authentication error:[/red] {e.message}")
                rprint(
                    "[dim]Your API key may have been revoked. Run 'pretorin login' to re-authenticate.[/dim]"
                )
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[red]Error:[/red] {e.message}")
                raise typer.Exit(1)

    asyncio.run(check_auth())
