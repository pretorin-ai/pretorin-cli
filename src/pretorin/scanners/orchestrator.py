"""
Scan orchestrator — coordinates scanner execution for STIG compliance testing.

1. Pulls test manifest from Pretorin API (applicable STIGs + rules)
2. Detects available scanner tools (OpenSCAP, InSpec, cloud CLIs)
3. Plans which scanners to run for which STIG rules
4. Executes scanners and collects results
5. Uploads results to Pretorin
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


@dataclass
class ScanPlanStep:
    """One step in the scan plan: a scanner + its assigned rules."""

    scanner_name: str
    benchmark_id: str
    rules: list[dict[str, Any]]
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScanPlan:
    """Full scan execution plan."""

    steps: list[ScanPlanStep]
    unassigned_rules: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ScanReport:
    """Results from a complete scan run."""

    cli_run_id: str
    started_at: datetime
    completed_at: datetime | None = None
    results: list[TestResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.FAIL)

    @property
    def not_reviewed(self) -> int:
        return sum(1 for r in self.results if r.status == TestStatus.NOT_REVIEWED)


class ScanOrchestrator:
    """
    Orchestrates STIG compliance scanning.

    Manages scanner detection, test planning, execution, and result
    submission to the Pretorin platform.
    """

    def __init__(self, scanners: list[ScannerBase] | None = None):
        if scanners is None:
            scanners = self._default_scanners()
        self._scanners = scanners
        self._scanner_info: dict[str, ScannerInfo] = {}

    @staticmethod
    def _default_scanners() -> list[ScannerBase]:
        """Create default set of all available scanners."""
        from pretorin.scanners.cloud_aws import AWSCloudScanner
        from pretorin.scanners.cloud_azure import AzureCloudScanner
        from pretorin.scanners.inspec import InSpecScanner
        from pretorin.scanners.manual import ManualScanner
        from pretorin.scanners.openscap import OpenSCAPScanner

        return [
            OpenSCAPScanner(),
            InSpecScanner(),
            AWSCloudScanner(),
            AzureCloudScanner(),
            ManualScanner(),
        ]

    async def detect_scanners(self) -> list[ScannerInfo]:
        """Detect which scanners are available on this system."""
        infos = []
        for scanner in self._scanners:
            info = await scanner.detect()
            self._scanner_info[scanner.name] = info
            infos.append(info)
        return infos

    def plan_scan(
        self,
        manifest: dict[str, Any],
        scanner_config: dict[str, Any] | None = None,
        preferred_scanner: str | None = None,
    ) -> ScanPlan:
        """
        Create a scan plan from a test manifest.

        Assigns rules to available scanners based on STIG compatibility.
        Rules with no matching scanner go to unassigned (require manual review).
        """
        scanner_config = scanner_config or {}
        steps: list[ScanPlanStep] = []
        unassigned: list[dict[str, Any]] = []

        # Build scanner lookup: name → (scanner, info)
        available = {
            s.name: s
            for s in self._scanners
            if self._scanner_info.get(s.name, ScannerInfo(name=s.name, version="", available=False)).available
        }

        for stig in manifest.get("applicable_stigs", []):
            stig_id = stig["stig_id"]
            rules = stig.get("rules", [])
            if not rules:
                continue

            # Find best scanner for this STIG
            assigned_scanner = None

            if preferred_scanner and preferred_scanner in available:
                scanner = available[preferred_scanner]
                if stig_id in scanner.supported_stigs() or "*" in scanner.supported_stigs():
                    assigned_scanner = preferred_scanner

            if not assigned_scanner:
                for name, scanner in available.items():
                    if name == "manual":
                        continue  # Manual is fallback only
                    supported = scanner.supported_stigs()
                    if stig_id in supported or "*" in supported:
                        assigned_scanner = name
                        break

            if assigned_scanner:
                config = scanner_config.get(assigned_scanner, {})
                config["benchmark_id"] = stig_id
                steps.append(
                    ScanPlanStep(
                        scanner_name=assigned_scanner,
                        benchmark_id=stig_id,
                        rules=rules,
                        config=config,
                    )
                )
            else:
                # No automated scanner — add to unassigned for manual review
                for rule in rules:
                    rule["_benchmark_id"] = stig_id
                unassigned.extend(rules)

        return ScanPlan(steps=steps, unassigned_rules=unassigned)

    async def execute_plan(self, plan: ScanPlan) -> ScanReport:
        """Execute a scan plan and collect results."""
        cli_run_id = str(uuid.uuid4())[:8]
        report = ScanReport(
            cli_run_id=cli_run_id,
            started_at=datetime.now(timezone.utc),
        )

        scanner_map = {s.name: s for s in self._scanners}

        for step in plan.steps:
            scanner = scanner_map.get(step.scanner_name)
            if not scanner:
                report.errors.append(f"Scanner not found: {step.scanner_name}")
                continue

            try:
                results = await scanner.execute(step.rules, step.config)
                report.results.extend(results)
            except Exception as e:
                report.errors.append(f"Scanner {step.scanner_name} failed for {step.benchmark_id}: {e}")
                # Mark rules as error
                for rule in step.rules:
                    report.results.append(
                        TestResult(
                            rule_id=rule.get("rule_id", "unknown"),
                            benchmark_id=step.benchmark_id,
                            status=TestStatus.ERROR,
                            tool=step.scanner_name,
                            tool_output=str(e)[:2000],
                        )
                    )

        report.completed_at = datetime.now(timezone.utc)
        return report

    async def run(
        self,
        client: Any,  # PretorianClient
        system_id: str,
        stig_id: str | None = None,
        preferred_scanner: str | None = None,
        scanner_config: dict[str, Any] | None = None,
        dry_run: bool = False,
    ) -> ScanReport:
        """
        Full scan pipeline: manifest → detect → plan → execute → upload.

        Args:
            client: Authenticated PretorianClient
            system_id: System to scan
            stig_id: Optional specific STIG to scan
            preferred_scanner: Force use of a specific scanner
            scanner_config: Per-scanner configuration
            dry_run: If True, plan but don't execute or upload
        """
        from pretorin import __version__

        # 1. Pull manifest
        manifest = await client.get_test_manifest(system_id, stig_id=stig_id)

        # 2. Detect scanners
        await self.detect_scanners()

        # 3. Plan
        plan = self.plan_scan(
            manifest,
            scanner_config=scanner_config,
            preferred_scanner=preferred_scanner,
        )

        if dry_run:
            # Return empty report with plan info
            report = ScanReport(
                cli_run_id="dry-run",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
            )
            return report

        # 4. Execute
        report = await self.execute_plan(plan)

        # 5. Upload results
        if report.results:
            result_dicts = [
                {
                    "rule_id": r.rule_id,
                    "benchmark_id": r.benchmark_id,
                    "status": r.status.value,
                    "tested_at": r.tested_at.isoformat(),
                    "tool": r.tool,
                    "tool_version": r.tool_version,
                    "tool_output": r.tool_output[:10000] if r.tool_output else None,
                }
                for r in report.results
            ]

            try:
                submit_response = await client.submit_test_results(
                    system_id,
                    cli_run_id=report.cli_run_id,
                    results=result_dicts,
                    cli_version=__version__,
                )
                if submit_response.get("rejected", 0) > 0:
                    report.errors.extend(submit_response.get("errors", []))
            except Exception as e:
                report.errors.append(f"Failed to upload results: {e}")

        return report
