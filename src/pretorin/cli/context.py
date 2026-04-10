"""Context commands for the Pretorin CLI."""

from __future__ import annotations

import asyncio
import re
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.scope import ExecutionScope

console = Console()

app = typer.Typer(
    name="context",
    help="Manage active system/framework context.",
    no_args_is_help=True,
)

ROMEBOT_HAPPY = "[#EAB536]\\[°◡°]/[/#EAB536]"
ROMEBOT_THINKING = "[#EAB536]\\[°~°][/#EAB536]"
ROMEBOT_SAD = "[#EAB536]\\[°︵°][/#EAB536]"
_MULTI_SCOPE_FRAMEWORK_PATTERN = re.compile(r"(,|/|\\|\band\b|&)", re.IGNORECASE)


def _resolve_context_values(
    system: str | None = None,
    framework: str | None = None,
    scope: ExecutionScope | None = None,
) -> tuple[str | None, str | None]:
    """Resolve context values from an explicit scope, flags, or stored config.

    Priority: scope > explicit flags > stored config.
    """
    if scope is not None and system is None and framework is None:
        return scope.system_id, scope.framework_id

    from pretorin.client.config import Config

    config = Config()
    return system or config.get("active_system_id"), framework or config.get("active_framework_id")


def _ensure_single_framework_scope(framework_id: str) -> str:
    """Reject obvious multi-framework selections in execution mode."""
    candidate = framework_id.strip()
    if not candidate:
        return candidate
    if _MULTI_SCOPE_FRAMEWORK_PATTERN.search(candidate):
        raise ValueError(
            "Framework scope must target exactly one framework. Split multi-level requests into separate runs."
        )
    return candidate


def _build_context_payload(
    *,
    system_id: str | None,
    framework_id: str | None,
    system_name: str | None = None,
    progress: int = 0,
    status: str = "unknown",
    valid: bool | None = None,
    validation_state: str = "unverified",
    validation_error: str | None = None,
) -> dict[str, Any]:
    """Create a consistent payload for context display and JSON output."""
    return {
        "active_system_id": system_id,
        "active_system_name": system_name or system_id,
        "active_framework_id": framework_id,
        "progress": progress,
        "status": status,
        "valid": valid,
        "validation_state": validation_state,
        "validation_error": validation_error,
    }


def _format_context_subject(payload: dict[str, Any]) -> str:
    """Return a compact human-readable system label."""
    system_id = payload.get("active_system_id")
    system_name = payload.get("active_system_name")
    if system_name and system_id and system_name != system_id:
        return f"{system_name} ({system_id})"
    return system_name or system_id or "-"


def _format_quiet_context(payload: dict[str, Any]) -> str:
    """Render a single-line context summary."""
    subject = _format_context_subject(payload)
    framework_id = payload.get("active_framework_id") or "-"
    validation_state = payload.get("validation_state")
    validation_error = payload.get("validation_error")
    if validation_state == "valid":
        return f"{subject} / {framework_id} [{payload.get('status', 'unknown')}, {payload.get('progress', 0)}%]"
    if validation_state == "invalid" and validation_error:
        return f"{subject} / {framework_id} [invalid: {validation_error}]"
    if validation_error:
        return f"{subject} / {framework_id} [unverified: {validation_error}]"
    return f"{subject} / {framework_id}"


def _show_context_payload(payload: dict[str, Any], *, quiet: bool = False) -> None:
    """Render context payload in JSON, compact, or panel form."""
    if is_json_mode():
        print_json(payload)
        return

    validation_state = payload.get("validation_state")
    validation_error = payload.get("validation_error")
    if quiet:
        console.print(_format_quiet_context(payload), markup=False)
        return

    status_line = (
        f"  [bold]System:[/bold]    {_format_context_subject(payload)}\n"
        f"  [bold]Framework:[/bold] {payload.get('active_framework_id')}\n"
        f"  [bold]Progress:[/bold]  {payload.get('progress', 0)}%\n"
        f"  [bold]Status:[/bold]    {payload.get('status', 'unknown')}"
    )
    if validation_state == "invalid" and validation_error:
        status_line += f"\n  [bold]Validation:[/bold] invalid\n  [bold]Note:[/bold]      {validation_error}"
    elif validation_error:
        status_line += f"\n  [bold]Validation:[/bold] {validation_state}\n  [bold]Note:[/bold]      {validation_error}"

    border_style = "#95D7E0" if validation_state == "valid" else "#EAB536"
    title_bot = ROMEBOT_HAPPY if validation_state == "valid" else ROMEBOT_THINKING
    rprint()
    rprint(
        Panel(
            status_line,
            title=f"{title_bot}  Active Context",
            border_style=border_style,
            padding=(1, 2),
        )
    )


async def resolve_execution_context(
    client: Any,
    *,
    system: str | None = None,
    framework: str | None = None,
    scope: ExecutionScope | None = None,
) -> tuple[str, str]:
    """Resolve and validate a single execution scope against the platform.

    When *scope* is provided and no explicit system/framework flags override it,
    the pre-validated scope is returned immediately without hitting the platform
    API.  This makes parallel agent runs safe — each subtask carries its own
    resolved scope instead of reading shared config.
    """
    if scope is not None and system is None and framework is None:
        return scope.system_id, scope.framework_id

    from pretorin.client.api import PretorianClientError
    from pretorin.client.config import Config
    from pretorin.workflows.compliance_updates import resolve_system

    # When falling back to stored config, verify the environment hasn't changed.
    if system is None and framework is None:
        env_error = Config().check_context_environment()
        if env_error:
            raise PretorianClientError(env_error)

    system_value, framework_value = _resolve_context_values(system=system, framework=framework)
    if not system_value or not framework_value:
        raise PretorianClientError(
            "No system/framework context set. Run 'pretorin context set' or pass --system and --framework-id."
        )

    try:
        framework_id = _ensure_single_framework_scope(framework_value)
    except ValueError as exc:
        raise PretorianClientError(str(exc)) from exc
    system_id, _ = await resolve_system(client, system_value)
    status = await client.get_system_compliance_status(system_id)
    available_frameworks = [fw.get("framework_id") for fw in status.get("frameworks", []) if fw.get("framework_id")]
    if not available_frameworks:
        raise PretorianClientError(
            f"System '{system_id}' has no configured frameworks. Add one in the Pretorin platform first."
        )
    if framework_id not in available_frameworks:
        raise PretorianClientError(
            f"Framework '{framework_id}' is not associated with system '{system_id}'. "
            f"Available frameworks: {', '.join(sorted(available_frameworks))}"
        )
    return system_id, framework_id


def resolve_context(
    system: str | None = None,
    framework: str | None = None,
) -> tuple[str, str]:
    """Resolve system_id and framework_id from flags or active context.

    Priority: explicit flags > stored context > error
    """
    system_id, framework_id = _resolve_context_values(system=system, framework=framework)

    if not system_id or not framework_id:
        rprint("[red]No system/framework context set.[/red]")
        rprint("Run [bold]pretorin context set[/bold] or use --system and --framework flags.")
        raise typer.Exit(1)

    return system_id, framework_id


@app.command("list")
def context_list() -> None:
    """List all systems and their compliance status."""
    asyncio.run(_context_list())


async def _context_list() -> None:
    """Fetch systems and compliance status from the API."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError

    async with PretorianClient() as client:
        require_auth(client)

        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_THINKING}  Fetching systems...\n")

        try:
            with Progress(
                SpinnerColumn(style="#EAB536"),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                disable=is_json_mode(),
            ) as progress:
                progress.add_task("Loading systems and compliance data...", total=None)
                systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        if not systems:
            rprint(f"  {ROMEBOT_SAD}  No systems found. Create a system in the Pretorin platform first.")
            raise typer.Exit(0)

        # Gather compliance status for each system
        rows: list[dict[str, Any]] = []
        for sys in systems:
            system_id = sys["id"]
            system_name = sys["name"]
            try:
                status = await client.get_system_compliance_status(system_id)
                frameworks = status.get("frameworks", [])
                if frameworks:
                    for fw in frameworks:
                        rows.append(
                            {
                                "system_name": system_name,
                                "system_id": system_id,
                                "framework_id": fw.get("framework_id", "unknown"),
                                "progress": fw.get("progress", 0),
                                "status": fw.get("status", "not_started"),
                            }
                        )
                else:
                    rows.append(
                        {
                            "system_name": system_name,
                            "system_id": system_id,
                            "framework_id": "-",
                            "progress": 0,
                            "status": "no frameworks",
                        }
                    )
            except PretorianClientError:
                rows.append(
                    {
                        "system_name": system_name,
                        "system_id": system_id,
                        "framework_id": "-",
                        "progress": 0,
                        "status": "error fetching status",
                    }
                )

        if is_json_mode():
            print_json(rows)
            return

        # Rich table output
        table = Table(
            title=f"{ROMEBOT_HAPPY}  Systems & Compliance Status",
            show_header=True,
            header_style="bold #FF9010",
        )
        table.add_column("System Name", style="bold")
        table.add_column("Framework ID")
        table.add_column("Progress %", justify="right")
        table.add_column("Status")

        status_colors = {
            "not_started": "#888888",
            "in_progress": "#EAB536",
            "implemented": "#95D7E0",
            "complete": "#4CAF50",
            "no frameworks": "#888888",
            "error fetching status": "#FF4444",
        }

        for row in rows:
            progress_str = f"{row['progress']}%" if row["framework_id"] != "-" else "-"
            status_color = status_colors.get(row["status"], "#888888")
            table.add_row(
                row["system_name"],
                row["framework_id"],
                progress_str,
                f"[{status_color}]{row['status']}[/{status_color}]",
            )

        rprint()
        rprint(table)
        rprint()


@app.command("set")
def context_set(
    system: str | None = typer.Option(
        None,
        "--system",
        "-s",
        help="System name or ID.",
    ),
    framework: str | None = typer.Option(
        None,
        "--framework",
        "-f",
        help="Framework ID (e.g., fedramp-moderate).",
    ),
) -> None:
    """Set the active system and framework context.

    If no flags are provided, runs in interactive mode.
    """
    asyncio.run(_context_set(system=system, framework=framework))


async def _context_set(
    system: str | None,
    framework: str | None,
) -> None:
    """Set context interactively or from flags."""
    from pretorin.cli.commands import require_auth
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    async with PretorianClient() as client:
        require_auth(client)

        if not is_json_mode():
            rprint(f"\n  {ROMEBOT_THINKING}  Connecting to Pretorin...\n")

        try:
            systems = await client.list_systems()
        except PretorianClientError as e:
            rprint(f"[red]Failed to list systems: {e.message}[/red]")
            raise typer.Exit(1)

        if not systems:
            rprint(f"  {ROMEBOT_SAD}  No systems found. Create a system in the Pretorin platform first.")
            raise typer.Exit(1)

        # --- Resolve system ---
        target_system = None

        if system is not None:
            # Match by name (partial, case-insensitive) or ID
            system_lower = system.lower()
            for s in systems:
                if s["id"] == system or s["name"].lower().startswith(system_lower):
                    target_system = s
                    break
            if target_system is None:
                rprint(f"[red]System not found: {system}[/red]")
                raise typer.Exit(1)
        else:
            # Interactive mode
            rprint("  [bold]Available systems:[/bold]\n")
            for i, s in enumerate(systems, 1):
                rprint(f"  {i}. {s['name']} ({s['id'][:8]}...)")

            rprint()
            choice = input("  Select system number: ")
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(systems):
                    raise ValueError
                target_system = systems[idx]
            except (ValueError, IndexError):
                rprint("[red]Invalid selection.[/red]")
                raise typer.Exit(1)

        system_id = target_system["id"]
        system_name = target_system["name"]

        # --- Resolve framework ---
        target_framework_id = None

        if framework is not None:
            # Validate framework is associated with this system
            try:
                status = await client.get_system_compliance_status(system_id)
                fw_ids = [fw.get("framework_id") for fw in status.get("frameworks", [])]
            except PretorianClientError:
                fw_ids = []

            if fw_ids and framework not in fw_ids:
                rprint(f"[red]Framework '{framework}' is not associated with system '{system_name}'.[/red]")
                rprint(f"  Available frameworks: {', '.join(fw_ids)}")
                raise typer.Exit(1)

            target_framework_id = framework
        else:
            # Interactive: list frameworks for the selected system
            try:
                status = await client.get_system_compliance_status(system_id)
                fw_list = status.get("frameworks", [])
            except PretorianClientError:
                fw_list = []

            if not fw_list:
                rprint(f"\n  {ROMEBOT_SAD}  No frameworks associated with system '{system_name}'.")
                rprint("  Add a framework to the system in the Pretorin platform first.")
                raise typer.Exit(1)

            rprint(f"\n  [bold]Frameworks for {system_name}:[/bold]\n")
            for i, fw in enumerate(fw_list, 1):
                fw_id = fw.get("framework_id", "unknown")
                fw_progress = fw.get("progress", 0)
                rprint(f"  {i}. {fw_id} ({fw_progress}% complete)")

            rprint()
            choice = input("  Select framework number: ")
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(fw_list):
                    raise ValueError
                target_framework_id = fw_list[idx].get("framework_id")
            except (ValueError, IndexError):
                rprint("[red]Invalid selection.[/red]")
                raise typer.Exit(1)

        # --- Save context ---
        config = Config()
        config.set("active_system_id", system_id)
        config.set("active_system_name", system_name)
        config.set("active_framework_id", target_framework_id)
        config.context_api_base_url = config.platform_api_base_url

        if is_json_mode():
            print_json(
                {
                    "system_id": system_id,
                    "system_name": system_name,
                    "framework_id": target_framework_id,
                }
            )
        else:
            rprint()
            rprint(
                Panel(
                    f"  [bold]System:[/bold]    {system_name} ({system_id[:8]}...)\n"
                    f"  [bold]Framework:[/bold] {target_framework_id}",
                    title=f"{ROMEBOT_HAPPY}  Context Set",
                    border_style="#95D7E0",
                    padding=(1, 2),
                )
            )


@app.command("show")
def context_show(
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Show a compact one-line summary instead of the rich panel.",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Exit non-zero when the stored context is missing, stale, or cannot be verified.",
    ),
) -> None:
    """Show the currently active system and framework context."""
    asyncio.run(_context_show(quiet=quiet, check=check))


async def _context_show(*, quiet: bool = False, check: bool = False) -> None:
    """Display the current context with live status."""
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    config = Config()
    system_id = config.get("active_system_id")
    cached_system_name = config.get("active_system_name")
    framework_id = config.get("active_framework_id")

    if not system_id or not framework_id:
        payload = _build_context_payload(
            system_id=system_id,
            framework_id=framework_id,
            system_name=cached_system_name,
            valid=False,
            validation_state="invalid",
            validation_error="No active context set.",
        )
        if is_json_mode():
            print_json(payload)
        elif quiet:
            rprint("no active context")
        else:
            rprint(f"\n  {ROMEBOT_SAD}  No active context set.\n")
            rprint("  Run [bold]pretorin context set[/bold] to select a system and framework.")
        if check:
            raise typer.Exit(1)
        return

    # Check for environment mismatch before hitting the API.
    env_error = config.check_context_environment()
    if env_error:
        payload = _build_context_payload(
            system_id=system_id,
            framework_id=framework_id,
            system_name=cached_system_name,
            valid=False,
            validation_state="invalid",
            validation_error=env_error,
        )
        _show_context_payload(payload, quiet=quiet)
        if check:
            raise typer.Exit(1)
        return

    async with PretorianClient() as client:
        if not client.is_configured:
            payload = _build_context_payload(
                system_id=system_id,
                framework_id=framework_id,
                system_name=cached_system_name,
                valid=None,
                validation_state="unverified",
                validation_error="Not logged in — showing stored context only.",
            )
            _show_context_payload(payload, quiet=quiet)
            if check:
                raise typer.Exit(1)
            return

        payload = _build_context_payload(
            system_id=system_id,
            framework_id=framework_id,
            system_name=cached_system_name,
            valid=None,
            validation_state="unverified",
        )

        try:
            systems = await client.list_systems()
        except PretorianClientError as e:
            payload["validation_error"] = f"Could not validate stored context: {e.message}"
            _show_context_payload(payload, quiet=quiet)
            if check:
                raise typer.Exit(1)
            return

        matched_system = next((item for item in systems if item.get("id") == system_id), None)
        if not matched_system:
            payload["valid"] = False
            payload["validation_state"] = "invalid"
            payload["validation_error"] = f"Stored system '{system_id}' no longer exists on the platform."
            _show_context_payload(payload, quiet=quiet)
            if check:
                raise typer.Exit(1)
            return

        payload["active_system_name"] = matched_system.get("name", system_id)

        try:
            compliance = await client.get_system_compliance_status(system_id)
        except PretorianClientError as e:
            payload["validation_error"] = f"Could not validate framework membership: {e.message}"
            _show_context_payload(payload, quiet=quiet)
            if check:
                raise typer.Exit(1)
            return

        frameworks = [fw for fw in compliance.get("frameworks", []) if fw.get("framework_id")]
        matched_framework = next((fw for fw in frameworks if fw.get("framework_id") == framework_id), None)
        if not matched_framework:
            payload["valid"] = False
            payload["validation_state"] = "invalid"
            if frameworks:
                available_frameworks = ", ".join(sorted(fw["framework_id"] for fw in frameworks))
                payload["validation_error"] = (
                    f"Framework '{framework_id}' is not associated with system "
                    f"'{payload['active_system_name']}'. Available frameworks: {available_frameworks}"
                )
            else:
                payload["validation_error"] = f"System '{payload['active_system_name']}' has no configured frameworks."
            _show_context_payload(payload, quiet=quiet)
            if check:
                raise typer.Exit(1)
            return

        payload["valid"] = True
        payload["validation_state"] = "valid"
        payload["progress"] = matched_framework.get("progress", 0)
        payload["status"] = matched_framework.get("status", "unknown")
        _show_context_payload(payload, quiet=quiet)


@app.command("clear")
def context_clear() -> None:
    """Clear the active system and framework context."""
    from pretorin.client.config import Config

    config = Config()
    config.delete("active_system_id")
    config.delete("active_system_name")
    config.delete("active_framework_id")
    config.delete("context_api_base_url")

    if is_json_mode():
        print_json({"cleared": True})
    else:
        rprint(f"\n  {ROMEBOT_HAPPY}  Context cleared.\n")
        rprint("  Run [bold]pretorin context set[/bold] to select a new system and framework.")
