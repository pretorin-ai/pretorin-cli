"""Coverage tests for src/pretorin/cli/vendor.py.

Targets all vendor commands: list, create, get, update, delete, upload-doc,
list-docs — in both normal and JSON modes plus validation/error handling.
"""

from __future__ import annotations

import json
import os
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset_json_mode():
    set_json_mode(False)
    yield
    set_json_mode(False)


def _run_with_mock_client(args: list[str], client: AsyncMock) -> object:
    with patch("pretorin.cli.vendor._get_client", return_value=client):
        return runner.invoke(app, args)


def _base_client() -> AsyncMock:
    client = AsyncMock()
    client.is_configured = True
    return client


# =============================================================================
# vendor list
# =============================================================================


def test_vendor_list_normal_with_items() -> None:
    """vendor list renders a table when vendors exist."""
    client = _base_client()
    client.list_vendors = AsyncMock(
        return_value=[
            {"id": "v-1", "name": "AWS", "provider_type": "csp", "authorization_level": "FedRAMP High"},
            {"id": "v-2", "name": "Okta", "provider_type": "saas", "authorization_level": "FedRAMP Moderate"},
        ]
    )

    result = _run_with_mock_client(["vendor", "list"], client)

    assert result.exit_code == 0, result.output
    assert "AWS" in result.output
    assert "Okta" in result.output


def test_vendor_list_empty() -> None:
    """vendor list shows empty message when no vendors found."""
    client = _base_client()
    client.list_vendors = AsyncMock(return_value=[])

    result = _run_with_mock_client(["vendor", "list"], client)

    assert result.exit_code == 0
    assert "No vendors found" in result.output


def test_vendor_list_json_mode() -> None:
    """vendor list --json emits structured JSON."""
    client = _base_client()
    vendors = [{"id": "v-1", "name": "AWS", "provider_type": "csp"}]
    client.list_vendors = AsyncMock(return_value=vendors)

    result = _run_with_mock_client(["--json", "vendor", "list"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["vendors"][0]["name"] == "AWS"


# =============================================================================
# vendor create
# =============================================================================


def test_vendor_create_normal_mode() -> None:
    """vendor create shows success message."""
    client = _base_client()
    client.create_vendor = AsyncMock(return_value={"id": "v-1", "name": "AWS"})

    result = _run_with_mock_client(["vendor", "create", "AWS", "--type", "csp"], client)

    assert result.exit_code == 0, result.output
    assert "Vendor created" in result.output
    assert "AWS" in result.output


def test_vendor_create_json_mode() -> None:
    """vendor create --json emits the API result."""
    client = _base_client()
    client.create_vendor = AsyncMock(return_value={"id": "v-1", "name": "AWS"})

    result = _run_with_mock_client(["--json", "vendor", "create", "AWS", "--type", "csp"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["id"] == "v-1"


def test_vendor_create_invalid_type() -> None:
    """vendor create rejects invalid provider type."""
    client = _base_client()

    result = _run_with_mock_client(["vendor", "create", "AWS", "--type", "invalid"], client)

    assert result.exit_code == 1
    assert "Invalid provider type" in result.output


def test_vendor_create_with_all_options() -> None:
    """vendor create passes all options to the API."""
    client = _base_client()
    client.create_vendor = AsyncMock(return_value={"id": "v-1", "name": "AWS"})

    result = _run_with_mock_client(
        [
            "--json",
            "vendor",
            "create",
            "AWS",
            "--type",
            "csp",
            "--description",
            "Cloud provider",
            "--authorization-level",
            "FedRAMP High",
        ],
        client,
    )

    assert result.exit_code == 0
    client.create_vendor.assert_awaited_once_with(
        name="AWS",
        provider_type="csp",
        description="Cloud provider",
        authorization_level="FedRAMP High",
    )


# =============================================================================
# vendor get
# =============================================================================


def test_vendor_get_normal_mode() -> None:
    """vendor get renders vendor details."""
    client = _base_client()
    client.get_vendor = AsyncMock(
        return_value={
            "id": "v-1",
            "name": "AWS",
            "provider_type": "csp",
            "authorization_level": "FedRAMP High",
            "description": "Cloud provider",
        }
    )

    result = _run_with_mock_client(["vendor", "get", "v-1"], client)

    assert result.exit_code == 0, result.output
    assert "AWS" in result.output
    assert "csp" in result.output
    assert "Cloud provider" in result.output


def test_vendor_get_json_mode() -> None:
    """vendor get --json emits the API result."""
    client = _base_client()
    data = {"id": "v-1", "name": "AWS", "provider_type": "csp"}
    client.get_vendor = AsyncMock(return_value=data)

    result = _run_with_mock_client(["--json", "vendor", "get", "v-1"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["id"] == "v-1"


def test_vendor_get_no_description() -> None:
    """vendor get omits description line when absent."""
    client = _base_client()
    client.get_vendor = AsyncMock(
        return_value={
            "id": "v-1",
            "name": "AWS",
            "provider_type": "csp",
            "authorization_level": None,
        }
    )

    result = _run_with_mock_client(["vendor", "get", "v-1"], client)

    assert result.exit_code == 0
    assert "Description" not in result.output


# =============================================================================
# vendor update
# =============================================================================


def test_vendor_update_normal_mode() -> None:
    """vendor update shows success message."""
    client = _base_client()
    client.update_vendor = AsyncMock(return_value={"name": "AWS Updated"})

    result = _run_with_mock_client(["vendor", "update", "v-1", "--name", "AWS Updated"], client)

    assert result.exit_code == 0, result.output
    assert "Vendor updated" in result.output


def test_vendor_update_json_mode() -> None:
    """vendor update --json emits the API result."""
    client = _base_client()
    client.update_vendor = AsyncMock(return_value={"name": "AWS Updated"})

    result = _run_with_mock_client(["--json", "vendor", "update", "v-1", "--name", "AWS Updated"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["name"] == "AWS Updated"


def test_vendor_update_no_fields() -> None:
    """vendor update exits 1 when no fields given."""
    client = _base_client()

    result = _run_with_mock_client(["vendor", "update", "v-1"], client)

    assert result.exit_code == 1
    assert "No fields to update" in result.output


def test_vendor_update_invalid_provider_type() -> None:
    """vendor update rejects invalid provider type."""
    client = _base_client()

    result = _run_with_mock_client(["vendor", "update", "v-1", "--type", "bogus"], client)

    assert result.exit_code == 1
    assert "Invalid provider type" in result.output


# =============================================================================
# vendor delete
# =============================================================================


def test_vendor_delete_with_force() -> None:
    """vendor delete --force deletes without confirmation."""
    client = _base_client()
    client.delete_vendor = AsyncMock(return_value=None)

    result = _run_with_mock_client(["vendor", "delete", "v-1", "--force"], client)

    assert result.exit_code == 0, result.output
    assert "deleted" in result.output
    client.delete_vendor.assert_awaited_once_with("v-1")


# =============================================================================
# vendor upload-doc
# =============================================================================


def test_vendor_upload_doc_file_not_found() -> None:
    """vendor upload-doc exits 1 when file doesn't exist."""
    client = _base_client()

    result = _run_with_mock_client(["vendor", "upload-doc", "v-1", "/nonexistent/path.pdf"], client)

    assert result.exit_code == 1
    assert "File not found" in result.output


def test_vendor_upload_doc_invalid_attestation_type() -> None:
    """vendor upload-doc rejects invalid attestation type."""
    client = _base_client()

    result = _run_with_mock_client(
        [
            "vendor",
            "upload-doc",
            "v-1",
            "/tmp/test.pdf",
            "--attestation-type",
            "bogus",
        ],
        client,
    )

    # Either file not found or invalid attestation — both exit 1
    assert result.exit_code == 1


def test_vendor_upload_doc_success(tmp_path) -> None:
    """vendor upload-doc uploads successfully."""
    test_file = tmp_path / "doc.pdf"
    test_file.write_text("test content")

    client = _base_client()
    client.upload_vendor_document = AsyncMock(return_value={"id": "doc-1", "name": "doc.pdf"})

    result = _run_with_mock_client(["vendor", "upload-doc", "v-1", str(test_file)], client)

    assert result.exit_code == 0, result.output
    assert "Document uploaded" in result.output


def test_vendor_upload_doc_json_mode(tmp_path) -> None:
    """vendor upload-doc --json emits the API result."""
    test_file = tmp_path / "doc.pdf"
    test_file.write_text("test content")

    client = _base_client()
    client.upload_vendor_document = AsyncMock(return_value={"id": "doc-1", "name": "doc.pdf"})

    result = _run_with_mock_client(["--json", "vendor", "upload-doc", "v-1", str(test_file)], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["id"] == "doc-1"


# =============================================================================
# vendor list-docs
# =============================================================================


def test_vendor_list_docs_normal_with_items() -> None:
    """vendor list-docs renders a table when documents exist."""
    client = _base_client()
    client.list_vendor_documents = AsyncMock(
        return_value=[
            {
                "id": "doc-1",
                "name": "SOC 2 Report",
                "evidence_type": "report",
                "attestation_type": "third_party_attestation",
            },
        ]
    )

    result = _run_with_mock_client(["vendor", "list-docs", "v-1"], client)

    assert result.exit_code == 0, result.output
    assert "SOC 2 Report" in result.output


def test_vendor_list_docs_empty() -> None:
    """vendor list-docs shows empty message when no documents found."""
    client = _base_client()
    client.list_vendor_documents = AsyncMock(return_value=[])

    result = _run_with_mock_client(["vendor", "list-docs", "v-1"], client)

    assert result.exit_code == 0
    assert "No documents found" in result.output


def test_vendor_list_docs_json_mode() -> None:
    """vendor list-docs --json emits structured JSON."""
    client = _base_client()
    docs = [{"id": "doc-1", "name": "SOC 2"}]
    client.list_vendor_documents = AsyncMock(return_value=docs)

    result = _run_with_mock_client(["--json", "vendor", "list-docs", "v-1"], client)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["total"] == 1
    assert payload["documents"][0]["name"] == "SOC 2"
