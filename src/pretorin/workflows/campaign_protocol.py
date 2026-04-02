"""Shared request normalization and validation for campaign adapters."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pretorin.utils import normalize_control_id
from pretorin.workflows.campaign import (
    OUTPUT_AUTO,
    OUTPUT_COMPACT,
    OUTPUT_JSON,
    OUTPUT_LIVE,
    CampaignRunRequest,
    default_checkpoint_path,
)

CAMPAIGN_OUTPUT_MODES = {OUTPUT_AUTO, OUTPUT_LIVE, OUTPUT_COMPACT, OUTPUT_JSON}
CAMPAIGN_CONTROL_MODES = {"initial", "notes-fix", "review-fix"}
CAMPAIGN_POLICY_SCOPE_MODES = {"answer", "review-fix"}
CAMPAIGN_ARTIFACTS = {"narratives", "evidence", "both"}


def parse_csv(value: str | None, *, normalizer: Callable[[str], Any] | None = None) -> list[str]:
    """Parse a comma-separated option into a list of strings."""
    if not value:
        return []
    items = [item.strip() for item in value.split(",") if item.strip()]
    if normalizer is None:
        return items
    return [str(normalizer(item)) for item in items]


def resolve_checkpoint_path(checkpoint: str | Path | None, *, domain: str, mode: str) -> Path:
    """Resolve an explicit checkpoint path or generate the default path."""
    if checkpoint is None:
        return default_checkpoint_path(domain, mode).resolve()
    return Path(checkpoint).expanduser().resolve()


def validate_output_mode(value: str) -> str:
    """Validate and return a supported campaign output mode."""
    if value not in CAMPAIGN_OUTPUT_MODES:
        raise ValueError("--output must be one of: auto, live, compact, json")
    return value


def build_campaign_request(
    *,
    domain: str,
    mode: str,
    apply: bool,
    output: str,
    concurrency: int,
    max_retries: int,
    checkpoint_path: str | Path | None,
    working_directory: str | Path,
    system: str | None = None,
    framework_id: str | None = None,
    family_id: str | None = None,
    control_ids: list[str] | None = None,
    all_controls: bool = False,
    artifacts: str = "both",
    review_job: str | None = None,
    policy_ids: list[str] | None = None,
    all_incomplete: bool = False,
) -> CampaignRunRequest:
    """Normalize and validate campaign inputs into one shared request object."""
    if domain not in {"controls", "policy", "scope"}:
        raise ValueError("domain must be one of: controls, policy, scope")

    validate_output_mode(output)
    normalized_control_ids = [normalize_control_id(item) for item in (control_ids or [])]
    normalized_policy_ids = [str(item) for item in (policy_ids or [])]
    resolved_checkpoint = resolve_checkpoint_path(checkpoint_path, domain=domain, mode=mode)
    resolved_working_directory = Path(working_directory).resolve()

    if domain == "controls":
        if mode not in CAMPAIGN_CONTROL_MODES:
            raise ValueError("--mode must be one of: initial, notes-fix, review-fix")
        if artifacts not in CAMPAIGN_ARTIFACTS:
            raise ValueError("--artifacts must be one of: narratives, evidence, both")
        if not system or not framework_id:
            raise ValueError("Control campaigns require --system and --framework-id.")
        target_sources = sum(1 for enabled in (bool(family_id), bool(normalized_control_ids), all_controls) if enabled)
        if target_sources != 1:
            raise ValueError("Exactly one of --family, --controls, or --all-controls is required.")
        if mode == "review-fix" and not review_job:
            raise ValueError("--review-job is required for controls --mode review-fix")
        if mode != "review-fix" and review_job:
            raise ValueError("--review-job is only valid with controls --mode review-fix")
    elif domain == "policy":
        if mode not in CAMPAIGN_POLICY_SCOPE_MODES:
            raise ValueError("--mode must be one of: answer, review-fix")
        if normalized_policy_ids and all_incomplete:
            raise ValueError("Use either --policies or --all-incomplete, not both.")
        all_incomplete = all_incomplete or not normalized_policy_ids
    else:
        if mode not in CAMPAIGN_POLICY_SCOPE_MODES:
            raise ValueError("--mode must be one of: answer, review-fix")
        if not system or not framework_id:
            raise ValueError("Scope campaigns require --system and --framework-id.")

    return CampaignRunRequest(
        domain=domain,
        mode=mode,
        apply=apply,
        output=output,
        concurrency=concurrency,
        max_retries=max_retries,
        checkpoint_path=resolved_checkpoint,
        working_directory=resolved_working_directory,
        system=system,
        framework_id=framework_id,
        family_id=family_id,
        control_ids=normalized_control_ids,
        all_controls=all_controls,
        artifacts=artifacts,
        review_job=review_job,
        policy_ids=normalized_policy_ids,
        all_incomplete=all_incomplete,
    )


def build_campaign_request_from_mapping(arguments: dict[str, Any]) -> CampaignRunRequest:
    """Build a campaign request from MCP-style JSON arguments."""
    return build_campaign_request(
        domain=str(arguments.get("domain", "")).strip(),
        mode=str(arguments.get("mode", "")).strip(),
        apply=bool(arguments.get("apply", False)),
        output=str(arguments.get("output", OUTPUT_JSON)),
        concurrency=int(arguments.get("concurrency", 4)),
        max_retries=int(arguments.get("max_retries", 2)),
        checkpoint_path=arguments.get("checkpoint_path"),
        working_directory=str(arguments.get("working_directory") or Path.cwd()),
        system=arguments.get("system_id"),
        framework_id=arguments.get("framework_id"),
        family_id=arguments.get("family_id"),
        control_ids=[str(item) for item in arguments.get("control_ids", [])],
        all_controls=bool(arguments.get("all_controls", False)),
        artifacts=str(arguments.get("artifacts", "both")),
        review_job=arguments.get("review_job"),
        policy_ids=[str(item) for item in arguments.get("policy_ids", [])],
        all_incomplete=bool(arguments.get("all_incomplete", False)),
    )
