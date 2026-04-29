"""run_scan tool for the manual-attestation recipe."""

from __future__ import annotations

from typing import Any

from pretorin.scanners.manifest import fetch_test_manifest, rules_for_stig, summarize_results
from pretorin.scanners.manual import ManualScanner


async def run(
    ctx: Any,
    *,
    stig_id: str,
    attestations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Apply per-rule attestations and return a summary.

    The calling agent passes ``attestations`` as a list of
    ``{rule_id, status, note}`` dicts. The ManualScanner consumes them via
    config to produce the final TestResult list.
    """
    manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id=stig_id)
    rules = rules_for_stig(manifest, stig_id)
    if not rules:
        return {
            "stig_id": stig_id,
            "summary": {"total": 0},
            "rules": [],
            "note": f"No rules found in manifest for stig_id={stig_id!r}",
        }

    scanner = ManualScanner()
    config: dict[str, Any] = {
        "benchmark_id": stig_id,
        "attestations": attestations or [],
    }
    results = await scanner.execute(rules, config=config)
    summary = summarize_results(results)
    return {
        "stig_id": stig_id,
        "attestations_supplied": len(attestations or []),
        "scanner": {"name": "manual", "version": "1.0"},
        "summary": {k: v for k, v in summary.items() if k != "rules"},
        "rules": summary["rules"],
    }
