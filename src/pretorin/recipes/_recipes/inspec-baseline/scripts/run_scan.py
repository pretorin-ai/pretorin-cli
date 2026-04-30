"""run_scan tool for the inspec-baseline recipe."""

from __future__ import annotations

from typing import Any

from pretorin.scanners.inspec import InSpecScanner
from pretorin.scanners.manifest import fetch_test_manifest, rules_for_stig, summarize_results


async def run(ctx: Any, *, stig_id: str, target: str = "local") -> dict[str, Any]:
    """Pull the manifest, run InSpec, return a per-run summary.

    Per the WS4 design, scanner recipes emit ONE summary evidence record per
    scan run rather than one per failed rule. This helper produces the dict
    the calling agent then turns into the evidence description.
    """
    manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id=stig_id)
    rules = rules_for_stig(manifest, stig_id)
    if not rules:
        return {
            "stig_id": stig_id,
            "target": target,
            "summary": {"total": 0},
            "rules": [],
            "note": f"No rules found in manifest for stig_id={stig_id!r}",
        }

    scanner = InSpecScanner()
    info = await scanner.detect()
    if not info.available:
        return {
            "stig_id": stig_id,
            "target": target,
            "summary": {"total": 0},
            "rules": [],
            "error": (f"InSpec is not installed or not reachable: {info.install_hint or 'see install docs'}"),
        }

    results = await scanner.execute(rules, config={"target": target, "benchmark_id": stig_id})
    summary = summarize_results(results)
    return {
        "stig_id": stig_id,
        "target": target,
        "scanner": {"name": "inspec", "version": info.version},
        "summary": {k: v for k, v in summary.items() if k != "rules"},
        "rules": summary["rules"],
    }
