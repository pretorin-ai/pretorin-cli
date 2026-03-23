"""Stateful scope questionnaire commands for Pretorin CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.commands import require_auth
from pretorin.cli.context import resolve_execution_context
from pretorin.cli.output import is_json_mode, print_json
from pretorin.client.api import PretorianClient, PretorianClientError
from pretorin.client.config import Config
from pretorin.workflows.questionnaire_population import draft_scope_questionnaire

app = typer.Typer(
    name="scope",
    help="View and populate persisted scope questionnaire state.",
    no_args_is_help=True,
)

console = Console()


def _platform_base_url() -> str:
    base_url = Config().platform_api_base_url.rstrip("/")
    for suffix in ("/api/v1/public", "/api/v1"):
        if base_url.endswith(suffix):
            return base_url[: -len(suffix)]
    return base_url


def _scope_handoff_url() -> str:
    return f"{_platform_base_url()}/compliance/scope"


def _validate_working_directory(path: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.exists():
        raise typer.BadParameter(f"path does not exist: {resolved}")
    return resolved


def _answer_map(payload: dict[str, Any] | None) -> dict[str, str | None]:
    questions = (payload or {}).get("questions", [])
    return {str(item.get("id")): item.get("answer") for item in questions if isinstance(item, dict) and item.get("id")}


def _normalize_text(value: str | None) -> str:
    return (value or "").strip()


def _build_scope_diffs(scope: Any, proposal: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_answers = _answer_map(scope.scope_qa_responses)
    proposal_map = {
        str(item.get("question_id")): item
        for item in proposal.get("questions", [])
        if isinstance(item, dict) and item.get("question_id")
    }

    diffs: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    for question in scope.scope_questions:
        existing = existing_answers.get(question.id)
        proposed = proposal_map.get(question.id)
        proposed_answer = proposed.get("proposed_answer") if proposed else None
        needs_manual_input = bool(proposed.get("needs_manual_input")) if proposed else False
        manual_input_reason = proposed.get("manual_input_reason") if proposed else None

        if proposed_answer is None:
            if needs_manual_input:
                status = "blocked"
            elif existing:
                status = "unchanged"
            else:
                status = "still_missing"
        elif _normalize_text(existing) == _normalize_text(proposed_answer):
            status = "unchanged"
        elif existing:
            status = "updated"
            updates.append({"question_id": question.id, "answer": proposed_answer})
        else:
            status = "newly_filled"
            updates.append({"question_id": question.id, "answer": proposed_answer})

        diffs.append(
            {
                "question_id": question.id,
                "section": question.section,
                "section_title": question.section_title,
                "question": question.question,
                "existing_answer": existing,
                "proposed_answer": proposed_answer,
                "status": status,
                "confidence": proposed.get("confidence") if proposed else None,
                "evidence_summary": proposed.get("evidence_summary") if proposed else None,
                "needs_manual_input": needs_manual_input,
                "manual_input_reason": manual_input_reason,
            }
        )
    return diffs, updates


def _print_review(review: Any, reviewed_at: str | None) -> None:
    rprint("\n[bold]Persisted Findings[/bold]")
    if not review:
        rprint("[dim]No saved review findings yet.[/dim]")
        return

    readiness = getattr(review, "readiness", None) or "unknown"
    rprint(f"Readiness: [bold]{readiness}[/bold]")
    if reviewed_at:
        rprint(f"Reviewed at: [dim]{reviewed_at}[/dim]")

    gaps = getattr(review, "gaps", []) or []
    if gaps:
        gap_table = Table(title="Gaps", show_header=True, header_style="bold")
        gap_table.add_column("Severity", no_wrap=True)
        gap_table.add_column("Area", no_wrap=True)
        gap_table.add_column("Description", max_width=80)
        for gap in gaps:
            gap_table.add_row(gap.severity, gap.area, gap.description)
        console.print(gap_table)

    changes = getattr(review, "recommended_changes", []) or []
    if changes:
        change_table = Table(title="Recommended Changes", show_header=True, header_style="bold")
        change_table.add_column("Priority", no_wrap=True)
        change_table.add_column("Section", no_wrap=True)
        change_table.add_column("Change", max_width=80)
        for change in changes:
            change_table.add_row(change.priority, change.section, change.change)
        console.print(change_table)


def _print_scope_state(scope: Any, *, system_id: str, framework_id: str) -> None:
    answered = sum(
        1 for item in (scope.scope_qa_responses or {}).get("questions", []) if _normalize_text(item.get("answer"))
    )
    total = len(scope.scope_questions)
    rprint(f"\n[bold]Scope Questionnaire[/bold] {system_id} / {framework_id}")
    rprint(f"Status: [bold]{scope.scope_status}[/bold]")
    rprint(f"Answered: [bold]{answered}/{total}[/bold]")
    _print_review(scope.scope_review, scope.scope_reviewed_at)


def _print_diffs(diffs: list[dict[str, Any]]) -> None:
    table = Table(title="Proposed Scope Updates", show_header=True, header_style="bold")
    table.add_column("Question", max_width=60)
    table.add_column("Status", no_wrap=True)
    table.add_column("Confidence", no_wrap=True)
    table.add_column("Answer Preview", max_width=80)
    for diff in diffs:
        answer_preview = diff["proposed_answer"] or diff["existing_answer"] or "(missing)"
        table.add_row(
            f"{diff['question_id']} - {diff['question']}",
            diff["status"],
            diff["confidence"] or "-",
            answer_preview,
        )
    console.print(table)


@app.command("show")
def scope_show(
    system: str | None = typer.Option(
        None,
        "--system",
        "-s",
        help="System name or ID (uses active context if not set).",
    ),
    framework_id: str | None = typer.Option(
        None,
        "--framework-id",
        "-f",
        help="Framework ID (uses active context if not set).",
    ),
) -> None:
    """Show persisted scope questionnaire state and saved review findings."""
    asyncio.run(_scope_show(system=system, framework_id=framework_id))


async def _scope_show(system: str | None, framework_id: str | None) -> None:
    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            scope = await client.get_scope(system_id, resolved_framework_id)
        except PretorianClientError as exc:
            rprint(f"[red]{exc.message}[/red]")
            raise typer.Exit(1)

        payload = {
            "system_id": system_id,
            "framework_id": resolved_framework_id,
            "scope": scope.model_dump(mode="json"),
            "handoff_url": _scope_handoff_url(),
        }
        if is_json_mode():
            print_json(payload)
            return
        _print_scope_state(scope, system_id=system_id, framework_id=resolved_framework_id)
        rprint(f"\nPlatform handoff: [link={_scope_handoff_url()}]{_scope_handoff_url()}[/link]")


@app.command("populate")
def scope_populate(
    system: str | None = typer.Option(
        None,
        "--system",
        "-s",
        help="System name or ID (uses active context if not set).",
    ),
    framework_id: str | None = typer.Option(
        None,
        "--framework-id",
        "-f",
        help="Framework ID (uses active context if not set).",
    ),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path to inspect for observable answers."),
    apply: bool = typer.Option(False, "--apply", help="Persist changed answers back to the platform."),
) -> None:
    """Draft stateful scope questionnaire updates from the current workspace."""
    asyncio.run(_scope_populate(system=system, framework_id=framework_id, path=path, apply=apply))


async def _scope_populate(
    system: str | None,
    framework_id: str | None,
    path: str,
    apply: bool,
) -> None:
    working_directory = _validate_working_directory(path)

    async with PretorianClient() as client:
        require_auth(client)
        try:
            system_id, resolved_framework_id = await resolve_execution_context(
                client,
                system=system,
                framework=framework_id,
            )
            scope = await client.get_scope(system_id, resolved_framework_id)
            proposal = await draft_scope_questionnaire(
                client,
                system_id=system_id,
                framework_id=resolved_framework_id,
                working_directory=working_directory,
            )
        except PretorianClientError as exc:
            rprint(f"[red]{exc.message}[/red]")
            raise typer.Exit(1)

        diffs, updates = _build_scope_diffs(scope, proposal)
        handoff_url = _scope_handoff_url()

        payload = {
            "system_id": system_id,
            "framework_id": resolved_framework_id,
            "parse_status": proposal.get("parse_status"),
            "summary": proposal.get("summary"),
            "diffs": diffs,
            "updates": updates,
            "applied": False,
            "handoff_url": handoff_url,
        }
        if apply and proposal.get("parse_status") == "json" and updates:
            try:
                await client.patch_scope_qa(system_id, resolved_framework_id, updates)
            except PretorianClientError as exc:
                rprint(f"[red]{exc.message}[/red]")
                raise typer.Exit(1)
            payload["applied"] = True
        if is_json_mode():
            print_json(payload)
            return

        _print_scope_state(scope, system_id=system_id, framework_id=resolved_framework_id)
        if proposal.get("summary"):
            rprint(f"\n[bold]Model Summary[/bold]\n{proposal['summary']}")
        _print_diffs(diffs)

        if proposal.get("parse_status") != "json":
            rprint("\n[yellow]The model response could not be parsed into structured updates.[/yellow]")
            raise typer.Exit(1)

        if payload["applied"]:
            rprint("\n[green]Saved updated scope answers to the platform.[/green]")
        elif apply and updates:
            rprint(
                "\n[yellow]Skipped saving scope answers because the model output "
                "was not valid structured JSON.[/yellow]"
            )
        elif apply:
            rprint("\n[dim]No changed scope answers to save.[/dim]")

        rprint(f"\nPlatform handoff: [link={handoff_url}]{handoff_url}[/link]")
