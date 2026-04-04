"""
Manual check scanner — for rules that require human verification.

Presents check text to the user and collects pass/fail/N/A responses
interactively. Used for policy-type CCIs and rules without automated
OVAL/InSpec checks.
"""

from __future__ import annotations

from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


class ManualScanner(ScannerBase):
    """Interactive manual check handler."""

    @property
    def name(self) -> str:
        return "manual"

    def supported_stigs(self) -> list[str]:
        # Manual scanner handles any STIG — it's the fallback
        return ["*"]

    async def detect(self) -> ScannerInfo:
        """Manual scanner is always available."""
        return ScannerInfo(
            name=self.name,
            version="1.0",
            available=True,
            supported_stigs=self.supported_stigs(),
        )

    async def execute(
        self,
        rules: list[dict[str, Any]],
        config: dict[str, Any] | None = None,
    ) -> list[TestResult]:
        """
        Collect manual check results.

        In interactive mode, prompts the user for each rule.
        In batch mode (config.batch=True), marks all as not_reviewed.

        Config options:
            batch: If True, skip prompts and mark all as not_reviewed
            benchmark_id: STIG benchmark ID for results
            responses: Pre-filled dict of rule_id → status for non-interactive use
        """
        config = config or {}
        benchmark_id = config.get("benchmark_id", "unknown")
        batch_mode = config.get("batch", False)
        pre_responses = config.get("responses", {})

        results = []
        for rule in rules:
            rule_id = rule.get("rule_id", "unknown")

            # Check for pre-filled response
            if rule_id in pre_responses:
                status_str = pre_responses[rule_id].lower()
                status_map = {
                    "pass": TestStatus.PASS,
                    "fail": TestStatus.FAIL,
                    "na": TestStatus.NOT_APPLICABLE,
                    "not_applicable": TestStatus.NOT_APPLICABLE,
                    "skip": TestStatus.NOT_REVIEWED,
                }
                status = status_map.get(status_str, TestStatus.NOT_REVIEWED)
                results.append(
                    TestResult(
                        rule_id=rule_id,
                        benchmark_id=benchmark_id,
                        status=status,
                        tool=self.name,
                        tool_output=f"Manual response: {status_str}",
                    )
                )
                continue

            if batch_mode:
                results.append(
                    TestResult(
                        rule_id=rule_id,
                        benchmark_id=benchmark_id,
                        status=TestStatus.NOT_REVIEWED,
                        tool=self.name,
                        tool_output="Batch mode — requires manual review",
                    )
                )
                continue

            # Interactive prompt
            title = rule.get("title", "")
            check_text = rule.get("check_text", "No check text available")

            print(f"\n{'=' * 60}")
            print(f"Rule: {rule_id}")
            if title:
                print(f"Title: {title}")
            print(f"Severity: {rule.get('severity', 'unknown')}")
            print(f"\nCheck:\n{check_text[:500]}")
            print(f"{'=' * 60}")

            while True:
                response = input("[P]ass / [F]ail / [N/A] / [S]kip > ").strip().lower()
                if response in ("p", "pass"):
                    status = TestStatus.PASS
                    break
                elif response in ("f", "fail"):
                    status = TestStatus.FAIL
                    break
                elif response in ("n", "na", "n/a", "not_applicable"):
                    status = TestStatus.NOT_APPLICABLE
                    break
                elif response in ("s", "skip", ""):
                    status = TestStatus.NOT_REVIEWED
                    break
                else:
                    print("Invalid input. Enter P, F, N/A, or S.")

            results.append(
                TestResult(
                    rule_id=rule_id,
                    benchmark_id=benchmark_id,
                    status=status,
                    tool=self.name,
                    tool_output=f"Manual assessment: {status.value}",
                )
            )

        return results
