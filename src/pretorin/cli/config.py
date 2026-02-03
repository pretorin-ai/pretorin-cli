"""Configuration CLI commands for Pretorin."""

import typer
from rich import print as rprint
from rich.table import Table

from pretorin.client.config import CONFIG_FILE, ENV_API_BASE_URL, ENV_API_KEY, Config

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

    if not stored and not os.environ.get(ENV_API_KEY):
        rprint("[dim]No configuration set yet.[/dim]")
        rprint("[dim]Run [bold]pretorin login[/bold] to get started.[/dim]")
        return

    rprint(table)
    rprint(f"\n[dim]Config file: {CONFIG_FILE}[/dim]")


@app.command("path")
def config_path() -> None:
    """Show the config file path."""
    rprint(str(CONFIG_FILE))
