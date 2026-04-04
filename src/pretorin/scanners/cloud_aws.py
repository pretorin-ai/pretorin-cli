"""
AWS cloud scanner integration.

Queries AWS Security Hub findings and AWS Config compliance data to
evaluate cloud-specific STIG rules. Maps Security Hub standard controls
to STIG rule IDs via CCI references.

Requires: AWS CLI v2 (aws binary) + configured credentials
"""

from __future__ import annotations

import json
from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


class AWSCloudScanner(ScannerBase):
    """AWS Security Hub / Config scanner."""

    @property
    def name(self) -> str:
        return "cloud_aws"

    def supported_stigs(self) -> list[str]:
        return [
            "Amazon_Elastic_Kubernetes_Service_EKS_STIG",
        ]

    async def detect(self) -> ScannerInfo:
        """Check if AWS CLI is available and configured."""
        code, stdout, stderr = await self._run_command(["aws", "--version"], timeout=10)

        if code != 0:
            return ScannerInfo(
                name=self.name,
                version="",
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint="Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html",
            )

        version = stdout.strip().split()[0].replace("aws-cli/", "")

        # Check if credentials are configured
        code2, _, _ = await self._run_command(["aws", "sts", "get-caller-identity"], timeout=10)
        if code2 != 0:
            return ScannerInfo(
                name=self.name,
                version=version,
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint="AWS CLI installed but credentials not configured. Run: aws configure",
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
        Query AWS Security Hub for STIG-mapped findings.

        Config options:
            region: AWS region (default: from AWS config)
            account_id: AWS account ID to filter
            benchmark_id: STIG benchmark ID for results
        """
        config = config or {}
        benchmark_id = config.get("benchmark_id", "unknown")
        region = config.get("region", "")

        # Query Security Hub findings
        cmd = [
            "aws",
            "securityhub",
            "get-findings",
            "--filters",
            json.dumps(
                {
                    "ComplianceStatus": [{"Value": "PASSED", "Comparison": "EQUALS"}],
                    "RecordState": [{"Value": "ACTIVE", "Comparison": "EQUALS"}],
                }
            ),
            "--max-items",
            "500",
            "--output",
            "json",
        ]
        if region:
            cmd.extend(["--region", region])

        code, stdout, stderr = await self._run_command(cmd, timeout=60)

        if code != 0:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output=f"AWS Security Hub query failed: {stderr[:1000]}",
                )
                for r in rules
            ]

        try:
            findings_data = json.loads(stdout)
        except json.JSONDecodeError:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output="Failed to parse Security Hub response",
                )
                for r in rules
            ]

        # Build findings map by control ID
        findings_map: dict[str, str] = {}
        for finding in findings_data.get("Findings", []):
            compliance = finding.get("Compliance", {})
            status = compliance.get("Status", "")
            # Security Hub control IDs may map to STIG rules via CCI
            control_id = finding.get("ProductFields", {}).get("ControlId", "")
            if control_id:
                findings_map[control_id] = status

        # Map findings to rules (best-effort matching via CCI cross-reference)
        results = []
        for rule in rules:
            rule_id = rule.get("rule_id", "unknown")
            # For now, mark as not_reviewed since direct mapping requires
            # a CCI→SecurityHub control mapping table
            results.append(
                TestResult(
                    rule_id=rule_id,
                    benchmark_id=benchmark_id,
                    status=TestStatus.NOT_REVIEWED,
                    tool=self.name,
                    tool_output=f"Security Hub findings available: {len(findings_map)} controls",
                )
            )

        return results
