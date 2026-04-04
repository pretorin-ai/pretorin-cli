"""
OpenSCAP scanner integration.

Wraps `oscap xccdf eval` to run DISA STIG profiles and parses the
XCCDF results XML into standardized TestResult objects.

Requires: openscap-scanner package (oscap binary)
STIG profiles: DISA STIG XCCDF files with profiles defined
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


class OpenSCAPScanner(ScannerBase):
    """OpenSCAP XCCDF evaluation scanner."""

    @property
    def name(self) -> str:
        return "openscap"

    def supported_stigs(self) -> list[str]:
        # OpenSCAP handles any XCCDF-based STIG
        return [
            "RHEL_9_STIG",
            "RHEL_8_STIG",
            "RHEL_7_STIG",
            "CAN_Ubuntu_22-04_LTS_STIG",
            "CAN_Ubuntu_20-04_LTS_STIG",
            "SLES_15_STIG",
        ]

    async def detect(self) -> ScannerInfo:
        """Check if oscap binary is available."""
        code, stdout, stderr = await self._run_command(["oscap", "--version"], timeout=10)

        if code != 0:
            return ScannerInfo(
                name=self.name,
                version="",
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint=(
                    "Install: sudo dnf install openscap-scanner (RHEL/Fedora)"
                    " or sudo apt install libopenscap8 (Debian/Ubuntu)"
                ),
            )

        # Parse version from output like "OpenSCAP command line tool (oscap) 1.3.7"
        version = ""
        match = re.search(r"oscap\)\s+([\d.]+)", stdout)
        if match:
            version = match.group(1)

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
        Run oscap xccdf eval against a STIG profile.

        Config options:
            xccdf_path: Path to STIG XCCDF file (required)
            profile: XCCDF profile ID to evaluate (default: auto-detect)
            target: Remote target (default: localhost)
            results_path: Where to write results XML (default: temp file)
        """
        config = config or {}
        xccdf_path = config.get("xccdf_path")
        if not xccdf_path:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=config.get("benchmark_id", "unknown"),
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output="No xccdf_path provided in scanner config",
                )
                for r in rules
            ]

        profile = config.get("profile", "")
        benchmark_id = config.get("benchmark_id", "unknown")
        results_path = config.get("results_path", "/tmp/oscap-results.xml")

        # Build oscap command
        cmd = [
            "oscap", "xccdf", "eval",
            "--results", results_path,
        ]
        if profile:
            cmd.extend(["--profile", profile])
        cmd.append(str(xccdf_path))

        # Run evaluation
        code, stdout, stderr = await self._run_command(cmd, timeout=600)

        # oscap returns 0 for all-pass, 2 for some-fail, 1 for error
        if code == 1 and "Error" in stderr:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output=f"oscap error: {stderr[:2000]}",
                )
                for r in rules
            ]

        # Parse results XML
        return self._parse_results_xml(
            Path(results_path), benchmark_id, rules
        )

    def _parse_results_xml(
        self, results_path: Path, benchmark_id: str, rules: list[dict[str, Any]]
    ) -> list[TestResult]:
        """Parse XCCDF results XML into TestResult objects."""
        if not results_path.exists():
            return []

        try:
            tree = ET.parse(results_path)
        except ET.ParseError:
            return []

        root = tree.getroot()
        ns_match = re.match(r"\{(.+?)\}", root.tag)
        ns = ns_match.group(1) if ns_match else ""

        # Build rule_id set for filtering
        rule_id_set = {r.get("rule_id") for r in rules}

        results = []
        # Find all rule-result elements
        for rr in root.iter(f"{{{ns}}}rule-result" if ns else "rule-result"):
            rule_id = rr.get("idref", "")
            if rule_id not in rule_id_set:
                continue

            result_el = rr.find(f"{{{ns}}}result" if ns else "result")
            result_text = result_el.text.strip() if result_el is not None and result_el.text else "unknown"

            # Map XCCDF result to our status
            status_map = {
                "pass": TestStatus.PASS,
                "fail": TestStatus.FAIL,
                "notapplicable": TestStatus.NOT_APPLICABLE,
                "notchecked": TestStatus.NOT_REVIEWED,
                "informational": TestStatus.NOT_REVIEWED,
                "error": TestStatus.ERROR,
                "unknown": TestStatus.NOT_REVIEWED,
                "notselected": TestStatus.NOT_APPLICABLE,
            }
            status = status_map.get(result_text.lower(), TestStatus.ERROR)

            # Extract check output if present
            check_el = rr.find(f".//{{{ns}}}check" if ns else ".//check")
            output = ""
            if check_el is not None:
                msg_el = check_el.find(f"{{{ns}}}message" if ns else "message")
                if msg_el is not None and msg_el.text:
                    output = msg_el.text.strip()[:5000]

            results.append(
                TestResult(
                    rule_id=rule_id,
                    benchmark_id=benchmark_id,
                    status=status,
                    tool=self.name,
                    tool_output=output,
                )
            )

        return results
