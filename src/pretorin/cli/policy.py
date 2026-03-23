"""Stateful org-policy questionnaire commands for Pretorin CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from urllib.parse import quote

import typer
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from pretorin.cli.commands import require_auth
from pretorin.cli.output import is_json_mode, print_json
from pretorin.client.api import PretorianClient, PretorianClientError
from pretorin.client.config import Config
from pretorin.client.models import OrgPolicyQuestionnaireResponse, OrgPolicySummary
from pretorin.workflows.questionnaire_population import draft_policy_questionnaire

app = typer.Typer(
    name="policy",
    help="View and populate persisted org-policy questionnaire state.",
    no_args_is_help=True,
)

console = Console()


def _platform_base_url() -> str:
    base_url = Config().platform_api_base_url.rstrip("/")
    for suffix in ("/api/v1/public", "/api/v1"):
        if base_url.endswith(suffix):
            return base_url[: -len(suffix)]
    return base_url


def _policy_handoff_url(policy_id: str) -> str:
    return f"{_platform_base_url()}/compliance/policies?openPolicyId={quote(policy_id)}&openWorkflow=1"


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


async def _resolve_policy_selector(client: PretorianClient, selector: str) -> OrgPolicySummary:
    listing = await client.list_org_policies()
    if not listing.policies:
        raise PretorianClientError("No org policies found for this organization.")

    exact_id = next((policy for policy in listing.policies if policy.id == selector), None)
    if exact_id:
        return exact_id

    exact_template = next(
        (policy for policy in listing.policies if policy.policy_template_id == selector),
        None,
    )
    if exact_template:
        return exact_template

    lowered = selector.lower()
    by_name = [policy for policy in listing.policies if policy.name.lower() == lowered]
    if len(by_name) == 1:
        return by_name[0]
    if len(by_name) > 1:
        matches = ", ".join(f"{policy.name} ({policy.id})" for policy in by_name)
        raise PretorianClientError(f"Policy selector '{selector}' is ambiguous. Matches: {matches}")

    raise PretorianClientError(f"Policy '{selector}' not found. Run 'pretorin policy list' to see available policies.")


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


def _print_policy_state(questionnaire: OrgPolicyQuestionnaireResponse) -> None:
    answered = sum(
        1
        for item in (questionnaire.policy_qa_responses or {}).get("questions", [])
        if _normalize_text(item.get("answer"))
    )
    total = len(questionnaire.template.questions) if questionnaire.template else 0
    rprint(f"\n[bold]Policy Questionnaire[/bold] {questionnaire.name}")
    rprint(f"Policy ID: [dim]{questionnaire.policy_id}[/dim]")
    rprint(f"Status: [bold]{questionnaire.policy_qa_status or 'not_started'}[/bold]")
    rprint(f"Answered: [bold]{answered}/{total}[/bold]")
    _print_review(questionnaire.policy_review, questionnaire.policy_reviewed_at)


def _build_policy_diffs(
    questionnaire: OrgPolicyQuestionnaireResponse,
    proposal: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_answers = _answer_map(questionnaire.policy_qa_responses)
    proposal_map = {
        str(item.get("question_id")): item
        for item in proposal.get("questions", [])
        if isinstance(item, dict) and item.get("question_id")
    }

    diffs: list[dict[str, Any]] = []
    updates: list[dict[str, Any]] = []
    template_questions = questionnaire.template.questions if questionnaire.template else []
    for question in sorted(template_questions, key=lambda item: item.order):
        existing = existing_answers.get(question.question_id)
        proposed = proposal_map.get(question.question_id)
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
            updates.append({"question_id": question.question_id, "answer": proposed_answer})
        else:
            status = "newly_filled"
            updates.append({"question_id": question.question_id, "answer": proposed_answer})

        diffs.append(
            {
                "question_id": question.question_id,
                "section_id": question.section_id,
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


def _print_diffs(diffs: list[dict[str, Any]]) -> None:
    table = Table(title="Proposed Policy Updates", show_header=True, header_style="bold")
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


@app.command("list")
def policy_list() -> None:
    """List org policies available for questionnaire work."""
    asyncio.run(_policy_list())


async def _policy_list() -> None:
    async with PretorianClient() as client:
        require_auth(client)
        try:
            listing = await client.list_org_policies()
        except PretorianClientError as exc:
            rprint(f"[red]{exc.message}[/red]")
            raise typer.Exit(1)

        if is_json_mode():
            print_json(listing)
            return
        if not listing.policies:
            rprint("[dim]No org policies found.[/dim]")
            return

        table = Table(title="Org Policies", show_header=True, header_style="bold")
        table.add_column("Name", max_width=36)
        table.add_column("Policy ID", no_wrap=True)
        table.add_column("Template", no_wrap=True)
        table.add_column("QA Status", no_wrap=True)
        table.add_column("Reviewed", no_wrap=True)
        for policy in listing.policies:
            table.add_row(
                policy.name,
                policy.id,
                policy.policy_template_id or "-",
                policy.policy_qa_status or "not_started",
                policy.policy_reviewed_at or "-",
            )
        console.print(table)


@app.command("show")
def policy_show(
    policy: str = typer.Option(..., "--policy", help="Policy selector: id, exact template_id, or unique exact name."),
) -> None:
    """Show persisted policy questionnaire state and saved review findings."""
    asyncio.run(_policy_show(policy))


async def _policy_show(policy: str) -> None:
    async with PretorianClient() as client:
        require_auth(client)
        try:
            resolved = await _resolve_policy_selector(client, policy)
            questionnaire = await client.get_org_policy_questionnaire(resolved.id)
        except PretorianClientError as exc:
            rprint(f"[red]{exc.message}[/red]")
            raise typer.Exit(1)

        handoff_url = _policy_handoff_url(questionnaire.policy_id)
        payload = {
            "policy": questionnaire.model_dump(mode="json"),
            "handoff_url": handoff_url,
        }
        if is_json_mode():
            print_json(payload)
            return
        _print_policy_state(questionnaire)
        rprint(f"\nPlatform handoff: [link={handoff_url}]{handoff_url}[/link]")


@app.command("populate")
def policy_populate(
    policy: str = typer.Option(..., "--policy", help="Policy selector: id, exact template_id, or unique exact name."),
    path: str = typer.Option(".", "--path", "-p", help="Workspace path to inspect for observable answers."),
    apply: bool = typer.Option(False, "--apply", help="Persist changed answers back to the platform."),
) -> None:
    """Draft stateful org-policy questionnaire updates from the current workspace."""
    asyncio.run(_policy_populate(policy=policy, path=path, apply=apply))


async def _policy_populate(policy: str, path: str, apply: bool) -> None:
    working_directory = _validate_working_directory(path)

    async with PretorianClient() as client:
        require_auth(client)
        try:
            resolved = await _resolve_policy_selector(client, policy)
            questionnaire = await client.get_org_policy_questionnaire(resolved.id)
            proposal = await draft_policy_questionnaire(
                client,
                questionnaire=questionnaire,
                working_directory=working_directory,
            )
        except PretorianClientError as exc:
            rprint(f"[red]{exc.message}[/red]")
            raise typer.Exit(1)

        diffs, updates = _build_policy_diffs(questionnaire, proposal)
        handoff_url = _policy_handoff_url(questionnaire.policy_id)
        payload = {
            "policy_id": questionnaire.policy_id,
            "policy_name": questionnaire.name,
            "parse_status": proposal.get("parse_status"),
            "summary": proposal.get("summary"),
            "diffs": diffs,
            "updates": updates,
            "applied": False,
            "handoff_url": handoff_url,
        }
        if apply and proposal.get("parse_status") == "json" and updates:
            try:
                await client.patch_org_policy_qa(questionnaire.policy_id, updates)
            except PretorianClientError as exc:
                rprint(f"[red]{exc.message}[/red]")
                raise typer.Exit(1)
            payload["applied"] = True
        if is_json_mode():
            print_json(payload)
            return

        _print_policy_state(questionnaire)
        if proposal.get("summary"):
            rprint(f"\n[bold]Model Summary[/bold]\n{proposal['summary']}")
        _print_diffs(diffs)

        if proposal.get("parse_status") != "json":
            rprint("\n[yellow]The model response could not be parsed into structured updates.[/yellow]")
            raise typer.Exit(1)

        if payload["applied"]:
            rprint("\n[green]Saved updated policy answers to the platform.[/green]")
        elif apply and updates:
            rprint(
                "\n[yellow]Skipped saving policy answers because the model output "
                "was not valid structured JSON.[/yellow]"
            )
        elif apply:
            rprint("\n[dim]No changed policy answers to save.[/dim]")

        rprint(f"\nPlatform handoff: [link={handoff_url}]{handoff_url}[/link]")
