"""Context commands for the Pretorin CLI."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from pretorin.cli.output import is_json_mode, print_json
from pretorin.scope import ExecutionScope

# Lazy imports for attestation to avoid circular deps at module level.
# Used in: resolve_execution_context, _context_verify, _context_set, context_clear.

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


def _format_scope_label(
    *,
    system_id: str | None,
    framework_id: str | None,
    system_name: str | None = None,
) -> str:
    """Return a compact scope label for guardrail messages."""
    subject = system_name or system_id or "-"
    if system_id and system_name and system_name != system_id:
        subject = f"{system_name} ({system_id})"
    return f"{subject} / {framework_id or '-'}"


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


def _enforce_source_attestation(
    system_id: str,
    framework_id: str,
    allow_unverified_sources: bool,
    control_id: str | None = None,
) -> None:
    """Block writes when the verified source snapshot shows a mismatch or manifest requirements are unsatisfied."""
    if allow_unverified_sources:
        return

    from pretorin.attestation import (
        VerificationStatus,
        check_snapshot_validity,
        load_snapshot,
    )
    from pretorin.client.config import Config

    snapshot = load_snapshot(system_id, framework_id)
    if snapshot is None:
        return

    config = Config()
    status = check_snapshot_validity(
        snapshot,
        system_id=system_id,
        framework_id=framework_id,
        api_base_url=config.platform_api_base_url,
    )
    if status == VerificationStatus.MISMATCH:
        from pretorin.client.api import PretorianClientError

        raise PretorianClientError(
            "Source attestation mismatch: the verified context no longer matches "
            "the current environment. Run 'pretorin context verify' to re-verify, "
            "or pass allow_unverified_sources to override."
        )

    # Phase 3: manifest evaluation
    from pretorin.attestation import (
        _MANIFEST_LOAD_CACHE,
        ManifestStatus,
        evaluate_manifest,
        extract_family_from_control_id,
        load_manifest,
    )

    manifest = load_manifest(system_id)
    if manifest is None:
        return

    # Cache the loaded manifest so build_write_provenance can skip file I/O
    _MANIFEST_LOAD_CACHE[system_id] = manifest

    family = extract_family_from_control_id(control_id) if control_id else None
    result = evaluate_manifest(manifest, snapshot.sources, family_id=family)

    if result.status == ManifestStatus.UNSATISFIED:
        from pretorin.client.api import PretorianClientError as _ManifestError

        missing = ", ".join(r.source_type for r in result.missing_required)
        raise _ManifestError(
            f"Source manifest check failed: missing required sources: {missing}. "
            "Verify sources with 'pretorin context verify' or add manual attestations "
            "in your source_providers config."
        )
    if result.missing_recommended:
        import logging as _logging

        _logging.getLogger(__name__).warning(
            "Recommended sources missing: %s",
            ", ".join(r.source_type for r in result.missing_recommended),
        )


async def resolve_execution_context(
    client: Any,
    *,
    system: str | None = None,
    framework: str | None = None,
    scope: ExecutionScope | None = None,
    enforce_active_context: bool = False,
    allow_scope_override: bool = False,
    allow_unverified_sources: bool = False,
    control_id: str | None = None,
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

    config = Config()

    # When falling back to stored config, verify the environment hasn't changed.
    if system is None and framework is None:
        env_error = config.check_context_environment()
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

    if enforce_active_context and not allow_scope_override:
        if scope is not None:
            if system_id != scope.system_id or framework_id != scope.framework_id:
                raise PretorianClientError(
                    "Execution scope is "
                    f"'{_format_scope_label(system_id=scope.system_id, framework_id=scope.framework_id)}'; "
                    "refusing write to "
                    f"'{_format_scope_label(system_id=system_id, framework_id=framework_id)}' "
                    "without explicit scope override."
                )
            _enforce_source_attestation(system_id, framework_id, allow_unverified_sources, control_id=control_id)
            return system_id, framework_id

        active_system_id = config.active_system_id
        active_framework_id = config.active_framework_id
        if active_system_id and active_framework_id:
            if system_id != active_system_id or framework_id != active_framework_id:
                active_scope_label = _format_scope_label(
                    system_id=active_system_id,
                    framework_id=active_framework_id,
                    system_name=config.active_system_name,
                )
                requested_scope_label = _format_scope_label(
                    system_id=system_id,
                    framework_id=framework_id,
                )
                raise PretorianClientError(
                    "Active context is "
                    f"'{active_scope_label}'; "
                    "refusing write to "
                    f"'{requested_scope_label}' "
                    "without explicit scope override."
                )
    if enforce_active_context:
        _enforce_source_attestation(system_id, framework_id, allow_unverified_sources, control_id=control_id)
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
    no_verify: bool = typer.Option(
        False,
        "--no-verify",
        help="Skip source verification after setting context.",
    ),
) -> None:
    """Set the active system and framework context.

    If no flags are provided, runs in interactive mode.
    After setting context, source verification runs automatically.
    """
    asyncio.run(_context_set(system=system, framework=framework, no_verify=no_verify))


async def _context_set(
    system: str | None,
    framework: str | None,
    no_verify: bool = False,
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

        # Delete old snapshot if scope changed
        old_system_id = config.active_system_id
        old_framework_id = config.active_framework_id
        if old_system_id and old_framework_id:
            if old_system_id != system_id or old_framework_id != target_framework_id:
                from pretorin.attestation import delete_snapshot

                delete_snapshot(old_system_id, old_framework_id)

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

        # --- Auto-verify sources ---
        if not no_verify:
            await _run_source_verification(
                system_id=system_id,
                framework_id=target_framework_id or "",
                api_base_url=config.platform_api_base_url,
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

        # Add verification status from snapshot if one exists
        from pretorin.attestation import load_snapshot as _load_snapshot

        snapshot = _load_snapshot(system_id, framework_id)
        if snapshot is not None:
            payload["verification_status"] = snapshot.status.value
            payload["verified_at"] = snapshot.verified_at
            payload["verified_sources"] = [s.provider_type for s in snapshot.sources]
        else:
            payload["verification_status"] = "unverified"

        _show_context_payload(payload, quiet=quiet)


@app.command("clear")
def context_clear() -> None:
    """Clear the active system and framework context."""
    from pretorin.client.config import Config

    config = Config()
    system_id = config.active_system_id
    framework_id = config.active_framework_id

    # Delete snapshot for current scope
    if system_id and framework_id:
        from pretorin.attestation import delete_snapshot

        delete_snapshot(system_id, framework_id)

    config.delete("active_system_id")
    config.delete("active_system_name")
    config.delete("active_framework_id")
    config.delete("context_api_base_url")

    if is_json_mode():
        print_json({"cleared": True})
    else:
        rprint(f"\n  {ROMEBOT_HAPPY}  Context cleared.\n")
        rprint("  Run [bold]pretorin context set[/bold] to select a new system and framework.")


# ---------------------------------------------------------------------------
# Source verification helpers
# ---------------------------------------------------------------------------


async def _run_source_verification(
    *,
    system_id: str,
    framework_id: str,
    api_base_url: str,
    ttl: int = 3600,
    quiet: bool = False,
) -> None:
    """Run source providers and persist a verified snapshot.

    Best-effort: failures are logged but do not raise.
    """
    try:
        from pretorin import __version__
        from pretorin.attestation import (
            VerificationStatus,
            VerifiedSnapshot,
            run_all_providers,
            save_snapshot,
        )

        sources = await run_all_providers()

        now = datetime.now(timezone.utc).isoformat()
        status = VerificationStatus.VERIFIED if sources else VerificationStatus.PARTIAL

        snapshot = VerifiedSnapshot(
            system_id=system_id,
            framework_id=framework_id,
            api_base_url=api_base_url,
            sources=tuple(sources),
            verified_at=now,
            ttl_seconds=ttl,
            status=status,
            cli_version=__version__,
        )

        save_snapshot(snapshot)

        if is_json_mode():
            return

        if not quiet:
            _display_verification_panel(snapshot)
    except Exception:
        import logging as _log

        _log.getLogger(__name__).debug("Source verification failed", exc_info=True)
        if not is_json_mode() and not quiet:
            rprint(f"\n  {ROMEBOT_THINKING}  Source verification skipped.")


def _display_verification_panel(snapshot: Any) -> None:
    """Display a rich panel showing verification results."""
    source_lines = ""
    if snapshot.sources:
        for src in snapshot.sources:
            source_lines += f"\n  [bold]{src.provider_type}:[/bold] {src.display_name or src.identity}"
    else:
        source_lines = "\n  [dim]No external sources detected[/dim]"

    status_color = "#95D7E0" if snapshot.status.value == "verified" else "#EAB536"
    rprint()
    rprint(
        Panel(
            f"  [bold]Status:[/bold]  {snapshot.status.value}{source_lines}",
            title=f"{ROMEBOT_HAPPY}  Source Verification",
            border_style=status_color,
            padding=(1, 2),
        )
    )


# ---------------------------------------------------------------------------
# context verify command
# ---------------------------------------------------------------------------


@app.command("verify")
def context_verify(
    ttl: int = typer.Option(
        3600,
        "--ttl",
        help="Verification TTL in seconds.",
    ),
    quiet: bool = typer.Option(
        False,
        "--quiet",
        "-q",
        help="Compact output.",
    ),
) -> None:
    """Verify active context with source attestation.

    Checks that the current session is connected to the expected
    external sources (git repo, cloud account, k8s cluster) and
    persists a verified snapshot for write guards.
    """
    asyncio.run(_context_verify(ttl=ttl, quiet=quiet))


async def _context_verify(*, ttl: int = 3600, quiet: bool = False) -> None:
    """Run source verification against the active context."""
    from pretorin.client.api import PretorianClient, PretorianClientError
    from pretorin.client.config import Config

    config = Config()
    system_id = config.get("active_system_id")
    framework_id = config.get("active_framework_id")

    if not system_id or not framework_id:
        if is_json_mode():
            print_json({"error": "No active context set."})
        else:
            rprint(f"\n  {ROMEBOT_SAD}  No active context set.\n")
            rprint("  Run [bold]pretorin context set[/bold] to select a system and framework.")
        raise typer.Exit(1)

    # Validate platform context
    env_error = config.check_context_environment()
    if env_error:
        if is_json_mode():
            print_json({"error": env_error})
        else:
            rprint(f"\n  {ROMEBOT_SAD}  {env_error}\n")
        raise typer.Exit(1)

    async with PretorianClient() as client:
        if not client.is_configured:
            rprint(f"\n  {ROMEBOT_SAD}  Not logged in. Run [bold]pretorin login[/bold] first.")
            raise typer.Exit(1)

        try:
            await resolve_execution_context(
                client,
                system=system_id,
                framework=framework_id,
                allow_unverified_sources=True,
            )
        except PretorianClientError as e:
            if is_json_mode():
                print_json({"error": e.message})
            else:
                rprint(f"\n  {ROMEBOT_SAD}  Context validation failed: {e.message}\n")
            raise typer.Exit(1)

    # Run source verification
    await _run_source_verification(
        system_id=system_id,
        framework_id=framework_id,
        api_base_url=config.platform_api_base_url,
        ttl=ttl,
        quiet=quiet,
    )

    if is_json_mode():
        from pretorin.attestation import load_snapshot as _load

        snap = _load(system_id, framework_id)
        if snap:
            result_dict: dict[str, Any] = {
                "system_id": snap.system_id,
                "framework_id": snap.framework_id,
                "status": snap.status.value,
                "verified_at": snap.verified_at,
                "sources": [{"provider_type": s.provider_type, "identity": s.identity} for s in snap.sources],
            }
            # Include manifest evaluation in JSON output
            from pretorin.attestation import evaluate_manifest, load_manifest

            manifest = load_manifest(system_id)
            if manifest is not None:
                m_result = evaluate_manifest(manifest, snap.sources)
                result_dict["manifest_status"] = m_result.status.value
                if m_result.missing_required:
                    result_dict["missing_required_sources"] = [r.source_type for r in m_result.missing_required]
                if m_result.missing_recommended:
                    result_dict["missing_recommended_sources"] = [r.source_type for r in m_result.missing_recommended]
            print_json(result_dict)
    else:
        # Show manifest evaluation in rich output
        from pretorin.attestation import evaluate_manifest, load_manifest, load_snapshot

        snap = load_snapshot(system_id, framework_id)
        if snap:
            manifest = load_manifest(system_id)
            if manifest is not None:
                m_result = evaluate_manifest(manifest, snap.sources)
                lines: list[str] = []
                for req in m_result.satisfied:
                    desc = f" ({req.description})" if req.description else ""
                    lines.append(f"  [green]\u2713[/green] {req.source_type}{desc}")
                for req in m_result.missing_required:
                    desc = f" ({req.description})" if req.description else ""
                    lines.append(f"  [red]\u2717[/red] {req.source_type} [red](required, missing)[/red]{desc}")
                for req in m_result.missing_recommended:
                    desc = f" ({req.description})" if req.description else ""
                    lines.append(
                        f"  [yellow]![/yellow] {req.source_type} [yellow](recommended, missing)[/yellow]{desc}"
                    )
                if lines:
                    rprint(
                        Panel(
                            "\n".join(lines),
                            title=f"[bold]Manifest: {m_result.status.value}[/bold]",
                            border_style="green" if m_result.status.value == "satisfied" else "yellow"
                            if m_result.status.value == "partial" else "red",
                        )
                    )


# ---------------------------------------------------------------------------
# context manifest
# ---------------------------------------------------------------------------


@app.command("manifest")
def context_manifest(
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Compact output."),
) -> None:
    """Show the resolved source manifest and evaluate against detected sources."""
    from pretorin.attestation import evaluate_manifest, load_manifest, load_snapshot
    from pretorin.client.config import Config

    config = Config()
    system_id = config.get("active_system_id")
    framework_id = config.get("active_framework_id")

    if not system_id:
        if is_json_mode():
            print_json({"error": "No active context set."})
        else:
            rprint(f"\n  {ROMEBOT_SAD}  No active context. Run [bold]pretorin context set[/bold] first.\n")
        raise typer.Exit(1)

    manifest = load_manifest(system_id)
    if manifest is None:
        if is_json_mode():
            print_json({"manifest": None, "message": "No source manifest found."})
        else:
            rprint(f"\n  {ROMEBOT_THINKING}  No source manifest found for system [bold]{system_id}[/bold].\n")
            rprint("  Create [bold].pretorin/source-manifest.json[/bold] in your repo root,")
            rprint("  or set the [bold]PRETORIN_SOURCE_MANIFEST[/bold] env var.\n")
        return

    if is_json_mode():
        result_dict: dict[str, Any] = {
            "version": manifest.version,
            "system_sources": [
                {"source_type": r.source_type, "level": r.level.value} for r in manifest.system_sources
            ],
            "family_sources": {
                k: [{"source_type": r.source_type, "level": r.level.value} for r in v]
                for k, v in manifest.family_sources.items()
            },
        }
        if framework_id:
            snap = load_snapshot(system_id, framework_id)
            if snap:
                m_result = evaluate_manifest(manifest, snap.sources)
                result_dict["evaluation"] = {
                    "status": m_result.status.value,
                    "satisfied": [r.source_type for r in m_result.satisfied],
                    "missing_required": [r.source_type for r in m_result.missing_required],
                    "missing_recommended": [r.source_type for r in m_result.missing_recommended],
                }
        print_json(result_dict)
    else:
        rprint(f"\n  {ROMEBOT_HAPPY}  Source manifest (v{manifest.version})\n")
        table = Table(title="System-level sources")
        table.add_column("Source", style="bold")
        table.add_column("Level")
        table.add_column("Pattern")
        for req in manifest.system_sources:
            table.add_row(
                req.source_type,
                req.level.value,
                req.identity_pattern or req.account_id or "",
            )
        if manifest.system_sources:
            rprint(table)

        for family_key, family_reqs in sorted(manifest.family_sources.items()):
            ftable = Table(title=f"Family: {family_key.upper()}")
            ftable.add_column("Source", style="bold")
            ftable.add_column("Level")
            for req in family_reqs:
                ftable.add_row(req.source_type, req.level.value)
            rprint(ftable)

        # Evaluate against current snapshot
        if framework_id:
            snap = load_snapshot(system_id, framework_id)
            if snap:
                m_result = evaluate_manifest(manifest, snap.sources)
                rprint(f"\n  Evaluation: [bold]{m_result.status.value}[/bold]")
            else:
                rprint("\n  No verified snapshot. Run [bold]pretorin context verify[/bold] to evaluate.")
        rprint()
