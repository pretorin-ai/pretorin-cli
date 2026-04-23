"""Campaign CLI commands for workflow-aligned fanout runs."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich import print as rprint
from rich.markup import escape

from pretorin.cli.commands import require_auth
from pretorin.cli.output import is_json_mode, print_json
from pretorin.client.api import PretorianClient, PretorianClientError
from pretorin.workflows.campaign import (
    OUTPUT_JSON,
    CampaignRunRequest,
    get_campaign_status,
    run_campaign,
)
from pretorin.workflows.campaign_protocol import (
    build_campaign_request,
    parse_csv,
    validate_output_mode,
)

app = typer.Typer(
    name="campaign",
    help="Workflow-aligned bulk campaign runs across controls, policy, and scope.",
    no_args_is_help=True,
)
controls_app = typer.Typer(invoke_without_command=True, no_args_is_help=False)
policy_app = typer.Typer(invoke_without_command=True, no_args_is_help=False)
scope_app = typer.Typer(invoke_without_command=True, no_args_is_help=False)


async def _run_request(request: CampaignRunRequest) -> None:
    async with PretorianClient() as client:
        require_auth(client)
        try:
            summary = await run_campaign(client, request)
        except PretorianClientError as exc:
            rprint(f"[red]{escape(exc.message)}[/red]")
            raise typer.Exit(1)

    if is_json_mode() or request.output == "json":
        print_json(summary.to_dict())
        return

    if summary.prepared_only:
        rprint(f"[{request.output == 'live' and 'bold' or 'cyan'}]Checkpoint:[/] {summary.checkpoint_path}")
        for step in summary.next_steps:
            rprint(f"[dim]- {escape(step)}[/dim]")


def _validate_output(value: str) -> None:
    try:
        validate_output_mode(value)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc


@controls_app.callback()
def controls_campaign(
    system: str = typer.Option(..., "--system", help="System name or ID."),
    framework_id: str = typer.Option(..., "--framework-id", help="Framework ID."),
    family: str | None = typer.Option(
        None,
        "--family",
        help=(
            "Control family ID or abbreviation (case-insensitive). "
            "List with `pretorin frameworks families <framework-id>`."
        ),
    ),
    controls: str | None = typer.Option(None, "--controls", help="Comma-separated control IDs."),
    all_controls: bool = typer.Option(False, "--all-controls", help="Target all controls in the framework."),
    mode: str = typer.Option(..., "--mode", help="initial, notes-fix, or review-fix"),
    artifacts: str = typer.Option("both", "--artifacts", help="narratives, evidence, or both"),
    review_job: str | None = typer.Option(None, "--review-job", help="Family review job id for review-fix mode."),
    concurrency: int = typer.Option(4, "--concurrency", help="Maximum concurrent workers."),
    max_retries: int = typer.Option(2, "--max-retries", help="Max retries per control."),
    checkpoint: str | None = typer.Option(None, "--checkpoint", help="Checkpoint file path."),
    apply: bool = typer.Option(False, "--apply", help="Persist generated changes."),
    output: str = typer.Option("auto", "--output", help="auto, live, compact, or json"),
) -> None:
    """Run a controls campaign."""
    try:
        request = build_campaign_request(
            domain="controls",
            mode=mode,
            apply=apply,
            output=output,
            concurrency=concurrency,
            max_retries=max_retries,
            checkpoint_path=checkpoint,
            working_directory=Path.cwd(),
            system=system,
            framework_id=framework_id,
            family_id=family,
            control_ids=parse_csv(controls),
            all_controls=all_controls,
            artifacts=artifacts,
            review_job=review_job,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    asyncio.run(_run_request(request))


@policy_app.callback()
def policy_campaign(
    policies: str | None = typer.Option(None, "--policies", help="Comma-separated policy ids."),
    all_incomplete: bool = typer.Option(False, "--all-incomplete", help="Target all incomplete policies."),
    mode: str = typer.Option(..., "--mode", help="answer or review-fix"),
    system: str | None = typer.Option(None, "--system", help="Optional system context passthrough."),
    concurrency: int = typer.Option(4, "--concurrency", help="Maximum concurrent workers."),
    max_retries: int = typer.Option(2, "--max-retries", help="Max retries per policy."),
    checkpoint: str | None = typer.Option(None, "--checkpoint", help="Checkpoint file path."),
    apply: bool = typer.Option(False, "--apply", help="Persist generated changes."),
    output: str = typer.Option("auto", "--output", help="auto, live, compact, or json"),
) -> None:
    """Run a policy campaign."""
    try:
        request = build_campaign_request(
            domain="policy",
            mode=mode,
            apply=apply,
            output=output,
            concurrency=concurrency,
            max_retries=max_retries,
            checkpoint_path=checkpoint,
            working_directory=Path.cwd(),
            system=system,
            policy_ids=parse_csv(policies),
            all_incomplete=all_incomplete,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    asyncio.run(_run_request(request))


@scope_app.callback()
def scope_campaign(
    system: str = typer.Option(..., "--system", help="System name or ID."),
    framework_id: str = typer.Option(..., "--framework-id", help="Framework ID."),
    mode: str = typer.Option(..., "--mode", help="answer or review-fix"),
    concurrency: int = typer.Option(4, "--concurrency", help="Maximum concurrent workers."),
    max_retries: int = typer.Option(2, "--max-retries", help="Max retries per question."),
    checkpoint: str | None = typer.Option(None, "--checkpoint", help="Checkpoint file path."),
    apply: bool = typer.Option(False, "--apply", help="Persist generated changes."),
    output: str = typer.Option("auto", "--output", help="auto, live, compact, or json"),
) -> None:
    """Run a scope campaign."""
    try:
        request = build_campaign_request(
            domain="scope",
            mode=mode,
            apply=apply,
            output=output,
            concurrency=concurrency,
            max_retries=max_retries,
            checkpoint_path=checkpoint,
            working_directory=Path.cwd(),
            system=system,
            framework_id=framework_id,
        )
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from exc
    asyncio.run(_run_request(request))


app.add_typer(controls_app, name="controls", help="Fan out work across controls in one workflow scope.")
app.add_typer(policy_app, name="policy", help="Fan out work across many policy workflows.")
app.add_typer(scope_app, name="scope", help="Fan out work across one scope workflow.")


@app.command("status")
def campaign_status(
    checkpoint: str = typer.Option(..., "--checkpoint", help="Campaign checkpoint file path."),
    output: str = typer.Option("auto", "--output", help="auto, live, compact, or json"),
) -> None:
    """Show the current state of a prepared or running campaign."""
    _validate_output(output)
    summary = get_campaign_status(Path(checkpoint).expanduser().resolve())
    if is_json_mode() or output == OUTPUT_JSON:
        print_json(summary.to_dict())
        return
    rprint(summary.status_snapshot)
