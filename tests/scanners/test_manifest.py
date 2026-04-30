"""Tests for pretorin.scanners.manifest helpers shared by every scanner recipe."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from pretorin.scanners.base import TestResult as ScannerTestResult
from pretorin.scanners.base import TestStatus as ScannerTestStatus
from pretorin.scanners.manifest import (
    applicable_stigs,
    fetch_test_manifest,
    rules_for_stig,
    summarize_results,
)


class _FakeAPIClient:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.calls: list[tuple[str, str | None]] = []

    async def get_test_manifest(self, system_id: str, *, stig_id: str | None = None) -> dict[str, Any]:
        self.calls.append((system_id, stig_id))
        return self._payload


# =============================================================================
# fetch_test_manifest
# =============================================================================


@pytest.mark.asyncio
async def test_fetch_test_manifest_passes_stig_id_through() -> None:
    payload = {"applicable_stigs": []}
    client = _FakeAPIClient(payload)
    result = await fetch_test_manifest(client, "sys-1", stig_id="RHEL_9_STIG")
    assert result is payload
    assert client.calls == [("sys-1", "RHEL_9_STIG")]


@pytest.mark.asyncio
async def test_fetch_test_manifest_without_stig_id() -> None:
    client = _FakeAPIClient({"applicable_stigs": []})
    await fetch_test_manifest(client, "sys-2")
    assert client.calls == [("sys-2", None)]


# =============================================================================
# applicable_stigs / rules_for_stig
# =============================================================================


def _manifest(*stigs: dict[str, Any]) -> dict[str, Any]:
    return {"applicable_stigs": list(stigs)}


def test_applicable_stigs_returns_all_when_unfiltered() -> None:
    m = _manifest({"stig_id": "A", "rules": []}, {"stig_id": "B", "rules": []})
    assert [s["stig_id"] for s in applicable_stigs(m)] == ["A", "B"]


def test_applicable_stigs_filters_by_id() -> None:
    m = _manifest({"stig_id": "A", "rules": []}, {"stig_id": "B", "rules": []})
    matched = applicable_stigs(m, stig_id="B")
    assert len(matched) == 1
    assert matched[0]["stig_id"] == "B"


def test_applicable_stigs_handles_missing_key() -> None:
    assert applicable_stigs({}) == []
    assert applicable_stigs({"applicable_stigs": None}) == []


def test_rules_for_stig_returns_rule_list() -> None:
    rules = [{"rule_id": "R-1"}, {"rule_id": "R-2"}]
    m = _manifest({"stig_id": "A", "rules": rules})
    assert rules_for_stig(m, "A") == rules


def test_rules_for_stig_empty_when_stig_missing() -> None:
    m = _manifest({"stig_id": "A", "rules": [{"rule_id": "R-1"}]})
    assert rules_for_stig(m, "ZZZ") == []


def test_rules_for_stig_empty_when_rules_null() -> None:
    m = _manifest({"stig_id": "A", "rules": None})
    assert rules_for_stig(m, "A") == []


# =============================================================================
# summarize_results
# =============================================================================


def _result(status: ScannerTestStatus, **kw: Any) -> ScannerTestResult:
    defaults: dict[str, Any] = {
        "rule_id": "R-1",
        "benchmark_id": "B-1",
        "status": status,
        "tested_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "tool": "fake",
        "tool_version": "1.0",
        "tool_output": "ok",
    }
    defaults.update(kw)
    return ScannerTestResult(**defaults)


def test_summarize_results_empty() -> None:
    s = summarize_results([])
    assert s["total"] == 0
    assert s["passed"] == s["failed"] == s["errored"] == 0
    assert s["not_applicable"] == s["not_reviewed"] == 0
    assert s["rules"] == []


def test_summarize_results_counts_each_status() -> None:
    results = [
        _result(ScannerTestStatus.PASS, rule_id="R-1"),
        _result(ScannerTestStatus.PASS, rule_id="R-2"),
        _result(ScannerTestStatus.FAIL, rule_id="R-3"),
        _result(ScannerTestStatus.ERROR, rule_id="R-4"),
        _result(ScannerTestStatus.NOT_APPLICABLE, rule_id="R-5"),
        _result(ScannerTestStatus.NOT_REVIEWED, rule_id="R-6"),
    ]
    s = summarize_results(results)
    assert s["total"] == 6
    assert s["passed"] == 2
    assert s["failed"] == 1
    assert s["errored"] == 1
    assert s["not_applicable"] == 1
    assert s["not_reviewed"] == 1
    assert [r["rule_id"] for r in s["rules"]] == ["R-1", "R-2", "R-3", "R-4", "R-5", "R-6"]
    assert s["rules"][0]["status"] == "pass"
    assert s["rules"][2]["status"] == "fail"


def test_summarize_results_truncates_tool_output() -> None:
    long_output = "x" * 5000
    s = summarize_results([_result(ScannerTestStatus.PASS, tool_output=long_output)])
    assert len(s["rules"][0]["tool_output"]) == 2000


def test_summarize_results_handles_empty_tool_output() -> None:
    s = summarize_results([_result(ScannerTestStatus.PASS, tool_output="")])
    assert s["rules"][0]["tool_output"] == ""
