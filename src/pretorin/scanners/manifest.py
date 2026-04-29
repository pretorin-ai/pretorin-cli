"""Test-manifest fetch + scanner filtering helpers shared by every scanner recipe.

Extracted from ``pretorin.scanners.orchestrator.ScanOrchestrator`` (per the
recipe-implementation design's WS4 §1) so each scanner recipe's
``scripts/run_scan.py`` can reuse them without dragging in the legacy
multi-scanner dispatch loop. The orchestrator is removed in WS4-final once
all five scanner recipes have ported.

These are the only pieces of the orchestrator that recipe scripts genuinely
need: pulling the manifest from the platform API, slicing it down to the
applicable rules for one STIG, and summarizing a list of TestResults into
the auditor-facing per-run evidence body.
"""

from __future__ import annotations

from typing import Any

from pretorin.scanners.base import TestResult, TestStatus


async def fetch_test_manifest(
    client: Any,  # PretorianClient — typed loosely to avoid an import cycle
    system_id: str,
    *,
    stig_id: str | None = None,
) -> dict[str, Any]:
    """Pull the test manifest for ``system_id`` from the platform.

    Optional ``stig_id`` narrows the manifest to one STIG; without it the
    manifest carries every applicable STIG for the system. The recipe scripts
    use the narrowing form when the calling agent asked for a specific STIG.
    """
    manifest: dict[str, Any] = await client.get_test_manifest(system_id, stig_id=stig_id)
    return manifest


def applicable_stigs(manifest: dict[str, Any], stig_id: str | None = None) -> list[dict[str, Any]]:
    """Return the manifest's applicable_stigs entries, optionally filtered.

    Each entry is a dict with ``stig_id`` plus ``rules`` (a list of rule dicts).
    Filtering by ``stig_id`` returns at most one entry; without filter, all.
    """
    stigs = manifest.get("applicable_stigs") or []
    if stig_id is None:
        return list(stigs)
    return [s for s in stigs if s.get("stig_id") == stig_id]


def rules_for_stig(manifest: dict[str, Any], stig_id: str) -> list[dict[str, Any]]:
    """Convenience: pull the rule list for one specific stig_id."""
    matched = applicable_stigs(manifest, stig_id=stig_id)
    if not matched:
        return []
    return list(matched[0].get("rules") or [])


def summarize_results(results: list[TestResult]) -> dict[str, Any]:
    """Reduce a list of TestResults to per-run summary counts.

    Used by every scanner recipe's ``run_scan`` to produce the dict the
    calling agent then turns into the evidence record's description body.
    Per-rule detail is attached as a list so the agent can include the most
    interesting individual results in the body.
    """
    total = len(results)
    passed = sum(1 for r in results if r.status == TestStatus.PASS)
    failed = sum(1 for r in results if r.status == TestStatus.FAIL)
    errored = sum(1 for r in results if r.status == TestStatus.ERROR)
    not_applicable = sum(1 for r in results if r.status == TestStatus.NOT_APPLICABLE)
    not_reviewed = sum(1 for r in results if r.status == TestStatus.NOT_REVIEWED)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "errored": errored,
        "not_applicable": not_applicable,
        "not_reviewed": not_reviewed,
        "rules": [
            {
                "rule_id": r.rule_id,
                "benchmark_id": r.benchmark_id,
                "status": r.status.value,
                "tool": r.tool,
                "tool_version": r.tool_version,
                "tool_output": (r.tool_output[:2000] if r.tool_output else ""),
                "tested_at": r.tested_at.isoformat(),
            }
            for r in results
        ],
    }


__all__ = [
    "applicable_stigs",
    "fetch_test_manifest",
    "rules_for_stig",
    "summarize_results",
]
