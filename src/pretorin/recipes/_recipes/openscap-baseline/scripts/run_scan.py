"""run_scan tool for the openscap-baseline recipe."""

from __future__ import annotations

from typing import Any

from pretorin.scanners.manifest import fetch_test_manifest, rules_for_stig, summarize_results
from pretorin.scanners.openscap import OpenSCAPScanner


async def run(ctx: Any, *, stig_id: str, datastream: str | None = None) -> dict[str, Any]:
    """Pull the manifest, run OpenSCAP, return per-run summary."""
    manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id=stig_id)
    rules = rules_for_stig(manifest, stig_id)
    if not rules:
        return {
            "stig_id": stig_id,
            "summary": {"total": 0},
            "rules": [],
            "note": f"No rules found in manifest for stig_id={stig_id!r}",
        }

    scanner = OpenSCAPScanner()
    info = await scanner.detect()
    if not info.available:
        return {
            "stig_id": stig_id,
            "summary": {"total": 0},
            "rules": [],
            "error": f"OpenSCAP not available: {info.install_hint or 'see install docs'}",
        }

    config: dict[str, Any] = {"benchmark_id": stig_id}
    if datastream:
        config["datastream"] = datastream
    results = await scanner.execute(rules, config=config)
    summary = summarize_results(results)
    return {
        "stig_id": stig_id,
        "scanner": {"name": "openscap", "version": info.version},
        "summary": {k: v for k, v in summary.items() if k != "rules"},
        "rules": summary["rules"],
    }
