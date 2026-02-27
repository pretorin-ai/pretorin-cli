"""Authentication CLI commands for Pretorin."""

import asyncio

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel

from pretorin.cli.animations import AnimationTheme, animated_status
from pretorin.cli.output import is_json_mode, print_json
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

    Get your API key from the Pretorin platform at https://platform.pretorin.com/
    """
    # If already authenticated and no explicit key provided, skip login
    if api_key is None and Config().is_configured:
        async def _check_existing() -> bool:
            async with PretorianClient() as client:
                try:
                    await client.validate_api_key()
                    return True
                except (AuthenticationError, PretorianClientError):
                    return False

        if asyncio.run(_check_existing()):
            rprint("\n[#EAB536]\\[°◡°]/[/#EAB536] Already authenticated. Run [bold]pretorin whoami[/bold] to see your session.")
            rprint("[dim]To re-authenticate, run: pretorin login --api-key <new-key>[/dim]")
            return

    if api_key is None:
        rprint("\n[bold #FF9010]Welcome to Pretorin[/bold #FF9010] [dim]\\[BETA][/dim]")
        rprint("[dim]Making compliance the best part of your day.[/dim]\n")
        rprint("Get your API key from: [link=https://platform.pretorin.com/]https://platform.pretorin.com/[/link]")
        rprint("[dim]A beta code is required for platform features (evidence, narratives, monitoring).[/dim]")
        rprint("No beta code? You can still browse frameworks and controls freely.")
        rprint(
            "[dim]Sign up for early access:[/dim] [link=https://pretorin.com/early-access/]https://pretorin.com/early-access/[/link]\n"
        )
        api_key = typer.prompt("Enter your API key", hide_input=True)

    if not api_key:
        rprint("[#FF9010]→[/#FF9010] API key is required to continue.")
        raise typer.Exit(1)

    async def validate_and_store() -> None:
        client = PretorianClient(api_key=api_key, api_base_url=api_base_url)
        try:
            with animated_status("Verifying your credentials...", AnimationTheme.MARCHING):
                await client.validate_api_key()

            # Store credentials after successful validation
            store_credentials(api_key, api_base_url)

            rprint(
                "\n[#EAB536]\\[°◡°]/[/#EAB536] [bold]You're in![/bold] Let's make compliance the best part of your day."
            )
            rprint(
                Panel(
                    f"[bold]Status:[/bold] [#95D7E0]Connected[/#95D7E0]\n[bold]API URL:[/bold] {client._api_base_url}",
                    title="Ready to go",
                    border_style="#95D7E0",
                )
            )

        except AuthenticationError as e:
            rprint(f"\n[#EAB536]\\[°︵°][/#EAB536] Authentication failed: {e.message}")
            rprint("[dim]Double-check your API key and try again.[/dim]")
            raise typer.Exit(1)
        except PretorianClientError as e:
            rprint(f"\n[#FF9010]→[/#FF9010] {e.message}")
            raise typer.Exit(1)
        finally:
            await client.close()

    asyncio.run(validate_and_store())


@app.command()
def logout() -> None:
    """Clear stored credentials and log out."""
    config = Config()

    if not config.is_configured:
        rprint("[dim]You're not currently logged in.[/dim]")
        return

    clear_credentials()
    rprint("[#EAB536]\\[°◡°][/#EAB536] Logged out. See you next time!")


@app.command()
def whoami() -> None:
    """Display current authentication status and configuration.

    Examples:
        pretorin whoami
        pretorin --json whoami
    """
    config = Config()

    if not config.is_configured:
        if is_json_mode():
            print_json({"authenticated": False})
            raise typer.Exit(1)
        rprint("[#FF9010]→[/#FF9010] Not logged in yet.")
        rprint("[dim]Run [bold]pretorin login[/bold] to get started.[/dim]")
        raise typer.Exit(1)

    async def check_auth() -> None:
        async with PretorianClient() as client:
            try:
                if is_json_mode():
                    await client.validate_api_key()
                    frameworks = await client.list_frameworks()
                    api_key = config.api_key or ""
                    masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"
                    print_json(
                        {
                            "authenticated": True,
                            "api_key": masked_key,
                            "api_url": client._api_base_url,
                            "frameworks_available": frameworks.total,
                        }
                    )
                    return

                with animated_status("Checking your session...", AnimationTheme.THINKING):
                    await client.validate_api_key()
                    frameworks = await client.list_frameworks()

                # Mask the API key for display
                api_key = config.api_key or ""
                masked_key = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else "***"

                rprint(
                    Panel(
                        f"[bold]Status:[/bold] [#95D7E0]Authenticated[/#95D7E0]\n"
                        f"[bold]API Key:[/bold] {masked_key}\n"
                        f"[bold]API URL:[/bold] {client._api_base_url}\n"
                        f"[bold]Frameworks Available:[/bold] {frameworks.total}",
                        title="Your Session",
                        border_style="#EAB536",
                    )
                )

            except AuthenticationError as e:
                rprint(f"[#FF9010]→[/#FF9010] Authentication issue: {e.message}")
                rprint(
                    "[dim]Your API key may have been revoked. Run [bold]pretorin login[/bold] to re-authenticate.[/dim]"
                )
                raise typer.Exit(1)
            except PretorianClientError as e:
                rprint(f"[#FF9010]→[/#FF9010] {e.message}")
                raise typer.Exit(1)

    asyncio.run(check_auth())
