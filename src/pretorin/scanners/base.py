"""
Abstract base for STIG compliance scanners.

All scanners implement the same interface: detect availability, execute
checks against STIG rules, and return standardized TestResult objects.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TestStatus(str, Enum):
    """Outcome of a single STIG rule test."""

    PASS = "pass"
    FAIL = "fail"
    NOT_APPLICABLE = "not_applicable"
    NOT_REVIEWED = "not_reviewed"
    ERROR = "error"


@dataclass
class TestResult:
    """Standardized result from evaluating one STIG rule."""

    rule_id: str
    benchmark_id: str  # STIG stig_id (e.g., "RHEL_9_STIG")
    status: TestStatus
    tested_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tool: str = ""
    tool_version: str = ""
    tool_output: str = ""
    evidence_id: str | None = None


@dataclass
class ScannerInfo:
    """Metadata about an available scanner."""

    name: str
    version: str
    available: bool
    supported_stigs: list[str] = field(default_factory=list)
    install_hint: str = ""


class ScannerBase(ABC):
    """
    Abstract base class for STIG compliance scanners.

    Subclasses wrap external tools (OpenSCAP, InSpec, cloud APIs) and
    translate their output into standardized TestResult objects.
    """

    @abstractmethod
    async def detect(self) -> ScannerInfo:
        """
        Check if this scanner's tooling is installed and available.

        Returns:
            ScannerInfo with availability status and version.
        """
        ...

    @abstractmethod
    async def execute(
        self,
        rules: list[dict[str, Any]],
        config: dict[str, Any] | None = None,
    ) -> list[TestResult]:
        """
        Run checks against a set of STIG rules.

        Args:
            rules: List of rule dicts from the test manifest (rule_id, check_text, etc.)
            config: Scanner-specific configuration (profiles, targets, credentials)

        Returns:
            List of TestResult objects, one per rule evaluated.
        """
        ...

    @abstractmethod
    def supported_stigs(self) -> list[str]:
        """
        Which STIG benchmark IDs this scanner can evaluate.

        Returns:
            List of stig_id strings (e.g., ["RHEL_9_STIG", "RHEL_8_STIG"])
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable scanner name."""
        ...

    async def _run_command(
        self, cmd: list[str], timeout: int = 300
    ) -> tuple[int, str, str]:
        """
        Run a shell command asynchronously.

        Returns (return_code, stdout, stderr).
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return (
                proc.returncode or 0,
                stdout.decode("utf-8", errors="replace"),
                stderr.decode("utf-8", errors="replace"),
            )
        except asyncio.TimeoutError:
            proc.kill()
            return -1, "", f"Command timed out after {timeout}s"
        except FileNotFoundError:
            return -1, "", f"Command not found: {cmd[0]}"
