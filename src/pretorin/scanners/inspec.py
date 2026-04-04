"""
Chef InSpec / MITRE SAF scanner integration.

Wraps `inspec exec` to run MITRE SAF STIG InSpec profiles and parses
the JSON output into standardized TestResult objects.

Requires: Chef InSpec (inspec binary)
Profiles: MITRE SAF InSpec profiles (https://github.com/mitre/)
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from typing import Any

from pretorin.scanners.base import ScannerBase, ScannerInfo, TestResult, TestStatus


class InSpecScanner(ScannerBase):
    """Chef InSpec / MITRE SAF scanner."""

    @property
    def name(self) -> str:
        return "inspec"

    def supported_stigs(self) -> list[str]:
        # InSpec MITRE SAF profiles cover a wide range
        return [
            "RHEL_9_STIG",
            "RHEL_8_STIG",
            "RHEL_7_STIG",
            "CAN_Ubuntu_22-04_LTS_STIG",
            "CAN_Ubuntu_20-04_LTS_STIG",
            "MS_Windows_Server_2022_STIG",
            "MS_Windows_Server_2019_STIG",
            "Kubernetes_STIG",
            "PostgreSQL_9-x_STIG",
            "NGINX_STIG",
            "Apache_Server_2-4_UNIX_STIG",
        ]

    async def detect(self) -> ScannerInfo:
        """Check if inspec binary is available."""
        code, stdout, stderr = await self._run_command(["inspec", "version"], timeout=15)

        if code != 0:
            return ScannerInfo(
                name=self.name,
                version="",
                available=False,
                supported_stigs=self.supported_stigs(),
                install_hint="Install: curl https://omnitruck.chef.io/install.sh | sudo bash -s -- -P inspec",
            )

        version = stdout.strip().split("\n")[0]

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
        Run inspec exec against a MITRE SAF profile.

        Config options:
            profile: Path or URL to InSpec profile (required)
            target: Target connection string (e.g., "ssh://user@host")
            reporter: Output format (default: json)
            benchmark_id: STIG benchmark ID for results
            attrs: Path to attributes YAML file
        """
        config = config or {}
        profile = config.get("profile")
        benchmark_id = config.get("benchmark_id", "unknown")

        if not profile:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output="No profile provided in scanner config",
                )
                for r in rules
            ]

        # Build inspec command with JSON reporter
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            results_path = tf.name

        cmd = [
            "inspec",
            "exec",
            str(profile),
            "--reporter",
            f"json:{results_path}",
        ]

        target = config.get("target")
        if target:
            cmd.extend(["--target", target])

        attrs = config.get("attrs")
        if attrs:
            cmd.extend(["--attrs", str(attrs)])

        # InSpec returns 0=pass, 100=has-failures, 101=profile-error
        code, stdout, stderr = await self._run_command(cmd, timeout=600)

        if code == 101:
            return [
                TestResult(
                    rule_id=r.get("rule_id", "unknown"),
                    benchmark_id=benchmark_id,
                    status=TestStatus.ERROR,
                    tool=self.name,
                    tool_output=f"InSpec profile error: {stderr[:2000]}",
                )
                for r in rules
            ]

        return self._parse_json_results(Path(results_path), benchmark_id, rules)

    def _parse_json_results(
        self, results_path: Path, benchmark_id: str, rules: list[dict[str, Any]]
    ) -> list[TestResult]:
        """Parse InSpec JSON output into TestResult objects."""
        if not results_path.exists():
            return []

        try:
            with open(results_path) as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        # Build rule_id lookup — InSpec control IDs may match V-IDs or SV-IDs
        rule_lookup: dict[str, str] = {}
        for r in rules:
            rule_lookup[r.get("rule_id", "")] = r.get("rule_id", "")
            if r.get("group_id"):
                rule_lookup[r["group_id"]] = r.get("rule_id", "")

        results = []
        profiles = data.get("profiles", [])

        for profile in profiles:
            for control in profile.get("controls", []):
                control_id = control.get("id", "")

                # Match to our rule IDs
                matched_rule_id = rule_lookup.get(control_id)
                if not matched_rule_id:
                    # Try matching by stripping version suffix
                    base_id = re.sub(r"r\d+_rule$", "", control_id)
                    matched_rule_id = rule_lookup.get(base_id)
                if not matched_rule_id:
                    continue

                # Aggregate control results
                control_results = control.get("results", [])
                if not control_results:
                    status = TestStatus.NOT_REVIEWED
                    output = ""
                else:
                    statuses = [cr.get("status", "") for cr in control_results]
                    if "failed" in statuses:
                        status = TestStatus.FAIL
                    elif all(s == "passed" for s in statuses):
                        status = TestStatus.PASS
                    elif all(s == "skipped" for s in statuses):
                        status = TestStatus.NOT_APPLICABLE
                    else:
                        status = TestStatus.FAIL

                    # Collect output messages
                    messages = []
                    for cr in control_results:
                        if cr.get("message"):
                            messages.append(cr["message"])
                        elif cr.get("skip_message"):
                            messages.append(f"SKIP: {cr['skip_message']}")
                    output = "\n".join(messages)[:5000]

                results.append(
                    TestResult(
                        rule_id=matched_rule_id,
                        benchmark_id=benchmark_id,
                        status=status,
                        tool=self.name,
                        tool_output=output,
                    )
                )

        return results
