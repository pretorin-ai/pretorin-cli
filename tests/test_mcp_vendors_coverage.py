"""Coverage tests for src/pretorin/mcp/handlers/vendors.py.

Tests all vendor and control responsibility handler functions.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from mcp.types import CallToolResult

from pretorin.mcp.handlers.vendors import (
    handle_create_vendor,
    handle_delete_vendor,
    handle_generate_inheritance_narrative,
    handle_get_control_responsibility,
    handle_get_stale_edges,
    handle_get_vendor,
    handle_link_evidence_to_vendor,
    handle_list_vendor_documents,
    handle_list_vendors,
    handle_remove_control_responsibility,
    handle_set_control_responsibility,
    handle_sync_stale_edges,
    handle_update_vendor,
    handle_upload_vendor_document,
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
# Vendor CRUD
# ---------------------------------------------------------------------------


class TestHandleListVendors:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(list_vendors=[{"id": "v1", "name": "Vendor A"}])
        result = await handle_list_vendors(client, {})
        client.list_vendors.assert_awaited_once()
        assert not _is_error(result)
        assert '"total": 1' in result[0].text


class TestHandleCreateVendor:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(create_vendor={"id": "v1"})
        result = await handle_create_vendor(client, {
            "name": "Acme", "provider_type": "IaaS",
        })
        client.create_vendor.assert_awaited_once_with(
            name="Acme", provider_type="IaaS",
            description=None, authorization_level=None,
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_optional_fields(self):
        client = _make_client(create_vendor={"id": "v1"})
        result = await handle_create_vendor(client, {
            "name": "Acme", "provider_type": "IaaS",
            "description": "Cloud provider", "authorization_level": "FedRAMP High",
        })
        client.create_vendor.assert_awaited_once_with(
            name="Acme", provider_type="IaaS",
            description="Cloud provider", authorization_level="FedRAMP High",
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_name(self):
        client = _make_client()
        result = await handle_create_vendor(client, {"provider_type": "IaaS"})
        assert _is_error(result)

    @pytest.mark.anyio
    async def test_missing_provider_type(self):
        client = _make_client()
        result = await handle_create_vendor(client, {"name": "Acme"})
        assert _is_error(result)


class TestHandleGetVendor:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_vendor={"id": "v1", "name": "Acme"})
        result = await handle_get_vendor(client, {"vendor_id": "v1"})
        client.get_vendor.assert_awaited_once_with("v1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_vendor_id(self):
        client = _make_client()
        result = await handle_get_vendor(client, {})
        assert _is_error(result)


class TestHandleUpdateVendor:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(update_vendor={"id": "v1", "name": "Updated"})
        result = await handle_update_vendor(client, {
            "vendor_id": "v1", "name": "Updated",
        })
        client.update_vendor.assert_awaited_once_with("v1", name="Updated")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_multiple_fields(self):
        client = _make_client(update_vendor={"id": "v1"})
        result = await handle_update_vendor(client, {
            "vendor_id": "v1", "name": "New Name",
            "description": "New desc", "provider_type": "SaaS",
        })
        client.update_vendor.assert_awaited_once_with(
            "v1", name="New Name", description="New desc", provider_type="SaaS",
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_no_fields_still_calls(self):
        client = _make_client(update_vendor={"id": "v1"})
        result = await handle_update_vendor(client, {"vendor_id": "v1"})
        client.update_vendor.assert_awaited_once_with("v1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_vendor_id(self):
        client = _make_client()
        result = await handle_update_vendor(client, {})
        assert _is_error(result)


class TestHandleDeleteVendor:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client()
        result = await handle_delete_vendor(client, {"vendor_id": "v1"})
        client.delete_vendor.assert_awaited_once_with("v1")
        assert not _is_error(result)
        assert '"deleted"' in result[0].text

    @pytest.mark.anyio
    async def test_missing_vendor_id(self):
        client = _make_client()
        result = await handle_delete_vendor(client, {})
        assert _is_error(result)


class TestHandleUploadVendorDocument:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(upload_vendor_document={"document_id": "d1"})
        result = await handle_upload_vendor_document(client, {
            "vendor_id": "v1", "file_path": "/tmp/doc.pdf",
        })
        client.upload_vendor_document.assert_awaited_once_with(
            vendor_id="v1", file_path="/tmp/doc.pdf",
            name=None, description=None, attestation_type="vendor_provided",
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_with_optional_fields(self):
        client = _make_client(upload_vendor_document={"document_id": "d1"})
        result = await handle_upload_vendor_document(client, {
            "vendor_id": "v1", "file_path": "/tmp/doc.pdf",
            "name": "SOC2 Report", "description": "Latest audit",
            "attestation_type": "third_party_audit",
        })
        client.upload_vendor_document.assert_awaited_once_with(
            vendor_id="v1", file_path="/tmp/doc.pdf",
            name="SOC2 Report", description="Latest audit",
            attestation_type="third_party_audit",
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_upload_vendor_document(client, {"vendor_id": "v1"})
        assert _is_error(result)

        result = await handle_upload_vendor_document(client, {"file_path": "/tmp/f"})
        assert _is_error(result)


class TestHandleListVendorDocuments:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(list_vendor_documents=[{"id": "d1"}])
        result = await handle_list_vendor_documents(client, {"vendor_id": "v1"})
        client.list_vendor_documents.assert_awaited_once_with("v1")
        assert not _is_error(result)
        assert '"total": 1' in result[0].text

    @pytest.mark.anyio
    async def test_missing_vendor_id(self):
        client = _make_client()
        result = await handle_list_vendor_documents(client, {})
        assert _is_error(result)


class TestHandleLinkEvidenceToVendor:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(link_evidence_to_vendor={"status": "linked"})
        result = await handle_link_evidence_to_vendor(client, {
            "evidence_id": "e1", "vendor_id": "v1",
            "attestation_type": "vendor_provided",
        })
        client.link_evidence_to_vendor.assert_awaited_once_with(
            evidence_id="e1", vendor_id="v1", attestation_type="vendor_provided",
        )
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_evidence_id(self):
        client = _make_client()
        result = await handle_link_evidence_to_vendor(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Control responsibility
# ---------------------------------------------------------------------------


class TestHandleGetControlResponsibility:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_control_responsibility={"mode": "shared"})
        result = await handle_get_control_responsibility(client, {
            "system_id": "sys-1", "control_id": "AC-2", "framework_id": "fw-1",
        })
        client.get_control_responsibility.assert_awaited_once()
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_get_control_responsibility(client, {
            "system_id": "sys-1",
        })
        assert _is_error(result)


class TestHandleSetControlResponsibility:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(set_control_responsibility={"status": "set"})
        result = await handle_set_control_responsibility(client, {
            "system_id": "sys-1", "control_id": "AC-2",
            "framework_id": "fw-1", "responsibility_mode": "shared",
        })
        client.set_control_responsibility.assert_awaited_once()
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_set_control_responsibility(client, {
            "system_id": "sys-1", "control_id": "AC-2",
        })
        assert _is_error(result)


class TestHandleRemoveControlResponsibility:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client()
        result = await handle_remove_control_responsibility(client, {
            "system_id": "sys-1", "control_id": "AC-2", "framework_id": "fw-1",
        })
        client.remove_control_responsibility.assert_awaited_once()
        assert not _is_error(result)
        assert '"removed"' in result[0].text

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_remove_control_responsibility(client, {})
        assert _is_error(result)


# ---------------------------------------------------------------------------
# Stale edges
# ---------------------------------------------------------------------------


class TestHandleGetStaleEdges:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(get_stale_edges=[{"edge_id": "e1"}])
        result = await handle_get_stale_edges(client, {"system_id": "sys-1"})
        client.get_stale_edges.assert_awaited_once_with("sys-1")
        assert not _is_error(result)
        assert '"total": 1' in result[0].text

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        result = await handle_get_stale_edges(client, {})
        assert _is_error(result)


class TestHandleSyncStaleEdges:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(sync_stale_edges={"synced": 3})
        result = await handle_sync_stale_edges(client, {"system_id": "sys-1"})
        client.sync_stale_edges.assert_awaited_once_with("sys-1")
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_system_id(self):
        client = _make_client()
        result = await handle_sync_stale_edges(client, {})
        assert _is_error(result)


class TestHandleGenerateInheritanceNarrative:
    @pytest.mark.anyio
    async def test_success(self):
        client = _make_client(generate_inheritance_narrative={"narrative": "text"})
        result = await handle_generate_inheritance_narrative(client, {
            "system_id": "sys-1", "control_id": "AC-2", "framework_id": "fw-1",
        })
        client.generate_inheritance_narrative.assert_awaited_once()
        assert not _is_error(result)

    @pytest.mark.anyio
    async def test_missing_params(self):
        client = _make_client()
        result = await handle_generate_inheritance_narrative(client, {
            "system_id": "sys-1",
        })
        assert _is_error(result)
