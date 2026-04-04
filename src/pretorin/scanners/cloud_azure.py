"""
Azure cloud scanner integration.

Queries Azure Policy compliance state and Microsoft Defender for Cloud
to evaluate cloud-specific STIG rules.

Requires: Azure CLI (az binary) + authenticated session
"""

from __future__ import annotations

import json
from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


class AzureCloudScanner(ScannerBase):
    """Azure Policy / Defender for Cloud scanner."""

    @property
    def name(self) -> str:
        return "cloud_azure"

    def supported_stigs(self) -> list[str]:
        return [
            "Microsoft_Azure_Foundations_STIG",
        ]

    async def detect(self) -> ScannerInfo:
        """Check if Azure CLI is available and authenticated."""
        code, stdout, stderr = await self._run_command(["az", "version", "--output", "json"], timeout=10)

        if code != 0:
            return ScannerInfo(
                name=self.name,
                version="",
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint="Install: https://learn.microsoft.com/en-us/cli/azure/install-azure-cli",
            )

        try:
            version_data = json.loads(stdout)
            version = version_data.get("azure-cli", "")
        except json.JSONDecodeError:
            version = ""

        # Check if logged in
        code2, _, _ = await self._run_command(["az", "account", "show", "--output", "json"], timeout=10)
        if code2 != 0:
            return ScannerInfo(
                name=self.name,
                version=version,
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint="Azure CLI installed but not authenticated. Run: az login",
            )

        return ScannerInfo(
            name=self.name,
            version=version,
            available=True,
            supported_stigs=self.supported_stigs(),
        )

    async def execute(
        self,
        rules: list[dict[str, Any]],
        config: dict[str, Any] | None = None,
    ) -> list[TestResult]:
        """
        Query Azure Policy compliance for STIG-mapped rules.

        Config options:
            subscription_id: Azure subscription ID
            benchmark_id: STIG benchmark ID for results
        """
        config = config or {}
        benchmark_id = config.get("benchmark_id", "unknown")
        subscription = config.get("subscription_id", "")

        cmd = [
            "az",
            "policy",
            "state",
            "summarize",
            "--output",
            "json",
        ]
        if subscription:
            cmd.extend(["--subscription", subscription])

        code, stdout, stderr = await self._run_command(cmd, timeout=60)

        if code != 0:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output=f"Azure Policy query failed: {stderr[:1000]}",
                )
                for r in rules
            ]

        # Map policy compliance to STIG rules (best-effort)
        results = []
        for rule in rules:
            results.append(
                TestResult(
                    rule_id=rule.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.NOT_REVIEWED,
                    tool=self.name,
                    tool_output="Azure Policy compliance data available — rule mapping pending",
                )
            )

        return results
