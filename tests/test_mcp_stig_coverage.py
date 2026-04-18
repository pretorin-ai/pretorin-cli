"""Coverage tests for src/pretorin/mcp/handlers/stig.py.

Tests all STIG and CCI handler functions including both read-only
reference tools and system-scoped tools.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult

from pretorin.mcp.handlers.stig import (
    handle_get_cci,
    handle_get_cci_chain,
    handle_get_cci_status,
    handle_get_stig,
    handle_get_stig_applicability,
    handle_get_stig_rule,
    handle_get_test_manifest,
    handle_infer_stigs,
    handle_list_ccis,
    handle_list_stig_rules,
    handle_list_stigs,
    handle_submit_test_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_client(**overrides) -> AsyncMock:
    client = AsyncMock()
    client.is_configured = True
    for attr, val in overrides.items():
        setattr(client, attr, AsyncMock(return_value=val))
    return client


def _is_error(result) -> bool:
    return isinstance(result, CallToolResult) and result.isError is True


# ---------------------------------------------------------------------------
# Read-only reference tools
# ---------------------------------------------------------------------------


class TestHandleListStigs:
    @pytest.mark.anyio
    async def test_defaults(self):
        client = _make_client(list_stigs={"stigs": []})
        result = await handle_list_stigs(client, {})
        client.list_stigs.assert_awaited_once_with(
            technology_area=None, product=None, limit=100, offset=0,
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_filters(self):
        client = _make_client(list_stigs={"stigs": [{"id": "s1"}]})
        result = await handle_list_stigs(client, {
            "technology_area": "Network",
            "product": "Cisco",
            "limit": 10,
            "offset": 5,
        })
        client.list_stigs.assert_awaited_once_with(
            technology_area="Network", product="Cisco", limit=10, offset=5,
        )
        assert not _is_error(result)


class TestHandleGetStig:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_stig={"id": "stig-1", "title": "Test STIG"})
        result = await handle_get_stig(client, {"stig_id": "stig-1"})
        client.get_stig.assert_awaited_once_with(stig_id="stig-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_stig_id(self):
        client = _make_client()
        result = await handle_get_stig(client, {})
        assert _is_error(result)


class TestHandleListStigRules:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(list_stig_rules={"rules": []})
        result = await handle_list_stig_rules(client, {"stig_id": "s1"})
        client.list_stig_rules.assert_awaited_once_with(
            stig_id="s1", severity=None, cci_id=None, limit=100, offset=0,
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_filters(self):
        client = _make_client(list_stig_rules={"rules": []})
        result = await handle_list_stig_rules(client, {
            "stig_id": "s1", "severity": "high", "cci_id": "CCI-001",
            "limit": 50, "offset": 10,
        })
        client.list_stig_rules.assert_awaited_once_with(
            stig_id="s1", severity="high", cci_id="CCI-001", limit=50, offset=10,
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_stig_id(self):
        client = _make_client()
        result = await handle_list_stig_rules(client, {})
        assert _is_error(result)


class TestHandleGetStigRule:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_stig_rule={"rule": "data"})
        result = await handle_get_stig_rule(client, {"stig_id": "s1", "rule_id": "r1"})
        client.get_stig_rule.assert_awaited_once_with(stig_id="s1", rule_id="r1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_stig_rule(client, {"stig_id": "s1"})
        assert _is_error(result)

        result = await handle_get_stig_rule(client, {})
        assert _is_error(result)


class TestHandleListCcis:
    @pytest.mark.anyio
    async def test_defaults(self):
        client = _make_client(list_ccis={"ccis": []})
        result = await handle_list_ccis(client, {})
        client.list_ccis.assert_awaited_once_with(
            nist_control_id=None, status=None, limit=100, offset=0,
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_filters(self):
        client = _make_client(list_ccis={"ccis": []})
        result = await handle_list_ccis(client, {
            "nist_control_id": "AC-2", "status": "active", "limit": 25, "offset": 3,
        })
        client.list_ccis.assert_awaited_once_with(
            nist_control_id="AC-2", status="active", limit=25, offset=3,
        )
        assert not _is_error(result)


class TestHandleGetCciChain:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_cci_chain={"chain": []})
        result = await handle_get_cci_chain(client, {"nist_control_id": "AC-2"})
        client.get_cci_chain.assert_awaited_once_with(nist_control_id="AC-2")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_param(self):
        client = _make_client()
        result = await handle_get_cci_chain(client, {})
        assert _is_error(result)


class TestHandleGetCci:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_cci={"cci_id": "CCI-001"})
        result = await handle_get_cci(client, {"cci_id": "CCI-001"})
        client.get_cci.assert_awaited_once_with(cci_id="CCI-001")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_param(self):
        client = _make_client()
        result = await handle_get_cci(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# System-scoped tools
# ---------------------------------------------------------------------------


class TestHandleGetTestManifest:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_test_manifest={"manifest": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_get_test_manifest(client, {"system_id": "sys-1"})
        client.get_test_manifest.assert_awaited_once_with(system_id="sys-1", stig_id=None)
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_stig_filter(self):
        client = _make_client(get_test_manifest={"manifest": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_get_test_manifest(client, {"system_id": "sys-1", "stig_id": "stig-1"})
        client.get_test_manifest.assert_awaited_once_with(system_id="sys-1", stig_id="stig-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value=None),
            )
            result = await handle_get_test_manifest(client, {})
        assert _is_error(result)


class TestHandleSubmitTestResults:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(submit_test_results={"status": "ok"})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_submit_test_results(client, {
                "system_id": "sys-1",
                "cli_run_id": "run-1",
                "results": [{"rule_id": "r1", "status": "pass"}],
            })
        client.submit_test_results.assert_awaited_once()
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_required(self):
        client = _make_client()
        result = await handle_submit_test_results(client, {"cli_run_id": "run-1"})
        assert _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value=None),
            )
            result = await handle_submit_test_results(client, {
                "system_id": "sys-1",
                "cli_run_id": "run-1",
                "results": [],
            })
        assert _is_error(result)


class TestHandleGetStigApplicability:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_stig_applicability={"applicable": []})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_get_stig_applicability(client, {"system_id": "sys-1"})
        client.get_stig_applicability.assert_awaited_once_with(system_id="sys-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value=None),
            )
            result = await handle_get_stig_applicability(client, {})
        assert _is_error(result)


class TestHandleGetCciStatus:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_cci_status={"status": "pass"})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_get_cci_status(client, {
                "system_id": "sys-1", "nist_control_id": "AC-2",
            })
        client.get_cci_status.assert_awaited_once_with(system_id="sys-1", nist_control_id="AC-2")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value=None),
            )
            result = await handle_get_cci_status(client, {})
        assert _is_error(result)


class TestHandleInferStigs:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(infer_stigs={"stigs": ["stig-1"]})
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value="sys-1"),
            )
            result = await handle_infer_stigs(client, {"system_id": "sys-1"})
        client.infer_stigs.assert_awaited_once_with(system_id="sys-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "pretorin.mcp.handlers.stig.resolve_system_id",
                AsyncMock(return_value=None),
            )
            result = await handle_infer_stigs(client, {})
        assert _is_error(result)
