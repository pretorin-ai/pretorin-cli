"""Configuration CLI commands for Pretorin."""

import asyncio

import typer
from rich import print as rprint
from rich.table import Table

from pretorin.client.api import AuthenticationError, PretorianClient, PretorianClientError
from pretorin.client.auth import _derive_model_api_base_url, store_credentials
from pretorin.client.config import (
    CONFIG_FILE,
    ENV_API_BASE_URL,
    ENV_API_KEY,
    ENV_DISABLE_UPDATE_CHECK,
    ENV_MODEL_API_BASE_URL,
    ENV_PLATFORM_API_BASE_URL,
    Config,
)

app = typer.Typer()


@app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Configuration key to read"),
) -> None:
    """Read a configuration value."""
    config = Config()
    value = config.get(key)

    if value is None:
        rprint(f"[dim]Key '{key}' is not set.[/dim]")
        raise typer.Exit(1)

    # Mask API key for display
    if key == "api_key" and value:
        display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "****"
        rprint(f"{key}: {display_value}")
    else:
        rprint(f"{key}: {value}")


@app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Value to set"),
) -> None:
    """Set a configuration value."""
    # Prevent setting reserved keys that should use login command
    if key == "api_key":
        rprint("[#FF9010]→[/#FF9010] Use [bold]pretorin login[/bold] to set your API key.")
        raise typer.Exit(1)

    config = Config()

    # Platform URL changes require re-authentication
    if key in {"api_base_url", "platform_api_base_url"}:
        previous = config.platform_api_base_url
        if value.rstrip("/") != previous.rstrip("/"):
            rprint(f"[#FF9010]→[/#FF9010] Changing API endpoint to: {value}")
            rprint("[dim]A new API key is required for this endpoint.[/dim]\n")
            api_key = typer.prompt("Enter your API key for the new endpoint", hide_input=True, default="")
            if not api_key:
                rprint("[#FF9010]→[/#FF9010] API key is required. Aborting.")
                raise typer.Exit(1)

            async def _validate_and_store() -> None:
                client = PretorianClient(api_key=api_key, api_base_url=value)
                try:
                    await client.validate_api_key()
                    store_credentials(api_key, value)
                    rprint(f"\n[#95D7E0]✓[/#95D7E0] Authenticated and switched to {value}")
                    model_url = _derive_model_api_base_url(value)
                    rprint(f"[#95D7E0]✓[/#95D7E0] Model API URL set to {model_url}")
                except AuthenticationError as e:
                    rprint(f"\n[#FF9010]→[/#FF9010] Authentication failed: {e.message}")
                    rprint("[dim]Endpoint not changed.[/dim]")
                    raise typer.Exit(1)
                except PretorianClientError as e:
                    rprint(f"\n[#FF9010]→[/#FF9010] {e.message}")
                    rprint("[dim]Endpoint not changed.[/dim]")
                    raise typer.Exit(1)
                finally:
                    await client.close()

            asyncio.run(_validate_and_store())
            return

    # Use property setters for known URL keys to keep config consistent
    if key == "model_api_base_url":
        config.model_api_base_url = value
    else:
        config.set(key, value)
    rprint(f"[#95D7E0]✓[/#95D7E0] Set {key} = {value}")


@app.command("list")
def config_list() -> None:
    """List all configuration values."""
    config = Config()
    stored = config.to_dict()

    table = Table(title="Pretorin Configuration", show_header=True, header_style="bold")
    table.add_column("Key")
    table.add_column("Value")
    table.add_column("Source")

    # Show stored config
    for key, value in stored.items():
        if key == "api_key" and value:
            display_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "****"
        else:
            display_value = str(value)
        table.add_row(key, display_value, "config file")

    # Show environment overrides
    import os

    if os.environ.get(ENV_API_KEY):
        table.add_row("api_key", "****", f"env ({ENV_API_KEY})")
    if os.environ.get(ENV_API_BASE_URL):
        table.add_row("api_base_url", os.environ[ENV_API_BASE_URL], f"env ({ENV_API_BASE_URL})")
    if os.environ.get(ENV_PLATFORM_API_BASE_URL):
        table.add_row(
            "platform_api_base_url",
            os.environ[ENV_PLATFORM_API_BASE_URL],
            f"env ({ENV_PLATFORM_API_BASE_URL})",
        )
    if os.environ.get(ENV_MODEL_API_BASE_URL):
        table.add_row(
            "model_api_base_url",
            os.environ[ENV_MODEL_API_BASE_URL],
            f"env ({ENV_MODEL_API_BASE_URL})",
        )
    if os.environ.get(ENV_DISABLE_UPDATE_CHECK):
        table.add_row(
            "disable_update_check",
            os.environ[ENV_DISABLE_UPDATE_CHECK],
            f"env ({ENV_DISABLE_UPDATE_CHECK})",
        )

    has_env_config = any(
        os.environ.get(env_key)
        for env_key in (
            ENV_API_KEY,
            ENV_API_BASE_URL,
            ENV_PLATFORM_API_BASE_URL,
            ENV_MODEL_API_BASE_URL,
            ENV_DISABLE_UPDATE_CHECK,
        )
    )
    if not stored and not has_env_config:
        rprint("[dim]No configuration set yet.[/dim]")
        rprint("[dim]Run [bold]pretorin login[/bold] to get started.[/dim]")
        return

    rprint(table)
    rprint(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@app.command("path")
def config_path() -> None:
    """Show the config file path."""
    rprint(str(CONFIG_FILE))
