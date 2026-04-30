"""run_scan tool for the cloud-aws-baseline recipe."""

from __future__ import annotations

from typing import Any

from pretorin.scanners.cloud_aws import AWSCloudScanner
from pretorin.scanners.manifest import fetch_test_manifest, rules_for_stig, summarize_results


async def run(ctx: Any, *, stig_id: str, region: str | None = None) -> dict[str, Any]:
    """Pull the manifest, run AWS-cloud checks, return per-run summary."""
    manifest = await fetch_test_manifest(ctx.api_client, ctx.system_id, stig_id=stig_id)
    rules = rules_for_stig(manifest, stig_id)
    if not rules:
        return {
            "stig_id": stig_id,
            "summary": {"total": 0},
            "rules": [],
            "note": f"No rules found in manifest for stig_id={stig_id!r}",
        }

    scanner = AWSCloudScanner()
    info = await scanner.detect()
    if not info.available:
        return {
            "stig_id": stig_id,
            "summary": {"total": 0},
            "rules": [],
            "error": f"AWS scanner not available: {info.install_hint or 'configure AWS credentials'}",
        }

    config: dict[str, Any] = {"benchmark_id": stig_id}
    if region:
        config["region"] = region
    results = await scanner.execute(rules, config=config)
    summary = summarize_results(results)
    return {
        "stig_id": stig_id,
        "region": region,
        "scanner": {"name": "aws", "version": info.version},
        "summary": {k: v for k, v in summary.items() if k != "rules"},
        "rules": summary["rules"],
    }
