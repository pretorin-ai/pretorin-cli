"""Comprehensive unit tests for the PretorianClient API client.

Uses httpx.MockTransport to simulate HTTP responses without hitting real servers.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import patch

import httpx
import pytest

from pretorin.client.api import (
    AuthenticationError,
    NotFoundError,
    PretorianClient,
    PretorianClientError,
)
from pretorin.client.models import (
    ControlBatchResponse,
    ControlContext,
    ControlDetail,
    ControlFamilyDetail,
    ControlFamilySummary,
    ControlImplementationResponse,
    ControlMetadata,
    ControlReferences,
    ControlSummary,
    DocumentRequirementList,
    EvidenceBatchItemCreate,
    EvidenceBatchResponse,
    EvidenceCreate,
    EvidenceItemResponse,
    FrameworkList,
    FrameworkMetadata,
    MonitoringEventCreate,
    NarrativeResponse,
    OrgPolicyListResponse,
    OrgPolicyQuestionnaireResponse,
    ScopeResponse,
    SystemDetail,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TEST_BASE_URL = "https://test.pretorin.api/api/v1/public"
TEST_API_KEY = "test-api-key-12345"


def _make_client(handler, api_key: str | None = TEST_API_KEY) -> PretorianClient:
    """Create a PretorianClient with a MockTransport handler injected."""
    client = PretorianClient(api_key=api_key, api_base_url=TEST_BASE_URL)
    transport = httpx.MockTransport(handler)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=TEST_BASE_URL,
        headers=client._get_headers(),
        timeout=60.0,
    )
    return client


# ---------------------------------------------------------------------------
# Fixtures providing reusable mock response data
# ---------------------------------------------------------------------------

FRAMEWORK_SUMMARY = {
    "id": "nist-800-53-r5",
    "external_id": "nist-800-53-r5",
    "title": "NIST SP 800-53 Revision 5",
    "version": "5.0",
    "description": "Security and Privacy Controls",
    "families_count": 20,
    "controls_count": 1189,
}

FRAMEWORK_METADATA = {
    "id": "nist-800-53-r5",
    "external_id": "nist-800-53-r5",
    "title": "NIST SP 800-53 Revision 5",
    "version": "5.0",
    "description": "Security and Privacy Controls",
    "tier": "comprehensive",
    "category": "federal",
}

CONTROL_FAMILY_SUMMARY = {
    "id": "ac",
    "title": "Access Control",
    "class": "SP800-53",
    "controls_count": 25,
}

CONTROL_FAMILY_DETAIL = {
    "id": "ac",
    "title": "Access Control",
    "class": "SP800-53",
    "controls": [
        {"id": "ac-01", "title": "Policy and Procedures", "class": "SP800-53"},
        {"id": "ac-02", "title": "Account Management", "class": "SP800-53"},
    ],
}

CONTROL_SUMMARY = {
    "id": "ac-02",
    "title": "Account Management",
    "family_id": "ac",
}

CONTROL_DETAIL = {
    "id": "ac-02",
    "title": "Account Management",
    "class": "SP800-53",
    "control_type": "system",
}

CONTROL_REFERENCES = {
    "control_id": "ac-02",
    "title": "Account Management",
    "statement": "Manage system accounts.",
    "guidance": "Account management guidance.",
    "objectives": ["obj-1", "obj-2"],
}

CONTROL_BATCH_RESPONSE = {
    "controls": [
        {
            "id": "ac-01",
            "title": "Policy and Procedures",
            "family_id": "ac",
            "control_type": "organizational",
        },
        {
            "id": "ac-02",
            "title": "Account Management",
            "family_id": "ac",
            "control_type": "system",
        },
    ],
    "total": 2,
}

CONTROL_METADATA_RESPONSE = {
    "ac-01": {"title": "Policy and Procedures", "family": "ac", "type": "organizational"},
    "ac-02": {"title": "Account Management", "family": "ac", "type": "system"},
}

DOCUMENT_REQUIREMENTS = {
    "framework_id": "fedramp-moderate",
    "framework_title": "FedRAMP Moderate",
    "explicit_documents": [],
    "implicit_documents": [],
    "total": 0,
}

SYSTEM_DETAIL = {
    "id": "sys-001",
    "name": "Test System",
    "description": "A test system",
    "frameworks": [{"id": "nist-800-53-r5"}],
}

EVIDENCE_ITEM = {
    "id": "ev-001",
    "name": "Test Evidence",
    "description": "Evidence description",
    "evidence_type": "policy_document",
    "status": "active",
    "control_mappings": [],
}

NARRATIVE_RESPONSE = {
    "control_id": "ac-02",
    "framework_id": "nist-800-53-r5",
    "narrative": "Account management narrative.",
    "status": "draft",
}

CONTROL_IMPLEMENTATION = {
    "control_id": "ac-02",
    "status": "implemented",
    "implementation_narrative": "Accounts are managed centrally.",
    "evidence_count": 3,
    "notes": [],
}

CONTROL_CONTEXT = {
    "control_id": "ac-02",
    "title": "Account Management",
    "statement": "Manage system accounts.",
    "guidance": "Follow account lifecycle.",
    "objectives": ["obj-1"],
    "status": "implemented",
}

SCOPE_RESPONSE = {
    "scope_status": "complete",
    "scope_narrative": {"description": "This system manages user data."},
    "scope_qa_responses": {
        "questions": [
            {
                "id": "sd-1",
                "question": "What does the system do?",
                "answer": "Existing answer",
                "section": "system_description",
            }
        ]
    },
    "scope_questions": [
        {
            "id": "sd-1",
            "question": "What does the system do?",
            "section": "system_description",
            "section_title": "System Description",
            "order": 0,
            "guidance": {
                "tips": ["Explain the mission."],
                "example_response": "Example scope answer",
                "common_mistakes": ["Being too vague"],
            },
        }
    ],
    "excluded_controls": [],
    "scope_review": {
        "readiness": "needs_work",
        "gaps": [{"area": "boundary", "severity": "medium", "description": "Clarify scope."}],
        "recommended_changes": [
            {"section": "System Description", "change": "Add user counts.", "priority": "high"}
        ],
    },
    "scope_reviewed_at": "2026-03-02T00:00:00+00:00",
}

ORG_POLICY_LIST_RESPONSE = {
    "policies": [
        {
            "id": "pol-001",
            "name": "Access Control Policy",
            "policy_template_id": "access-control-policy",
            "status": "draft",
            "policy_qa_status": "in_progress",
            "policy_reviewed_at": "2026-03-02T00:00:00+00:00",
        }
    ],
    "total": 1,
}

ORG_POLICY_QUESTIONNAIRE_RESPONSE = {
    "policy_id": "pol-001",
    "name": "Access Control Policy",
    "policy_template_id": "access-control-policy",
    "policy_qa_status": "in_progress",
    "policy_qa_responses": {
        "questions": [
            {
                "id": "q_purpose_1",
                "question": "Why does this Access Control Policy exist?",
                "answer": "Existing purpose answer",
                "section_id": "purpose",
            }
        ]
    },
    "template": {
        "template_id": "access-control-policy",
        "template_name": "Access Control Policy",
        "document_type": "policy",
        "sections": [
            {
                "section_id": "purpose",
                "title": "Purpose",
                "order": 1,
                "required_content": [],
            }
        ],
        "questions": [
            {
                "question_id": "q_purpose_1",
                "question": "Why does this Access Control Policy exist?",
                "section_id": "purpose",
                "additional_section_ids": [],
                "guidance": {
                    "tips": ["Tie the policy to least privilege."],
                    "example_response": "This policy protects systems and data.",
                    "common_mistakes": "Being too vague",
                },
                "order": 1,
            }
        ],
    },
    "policy_review": {
        "readiness": "needs_work",
        "gaps": [{"area": "scope", "severity": "medium", "description": "Clarify exclusions."}],
        "recommended_changes": [
            {"section": "Scope", "change": "Add service accounts.", "priority": "high"}
        ],
    },
    "policy_reviewed_at": "2026-03-02T00:00:00+00:00",
}

EVIDENCE_BATCH_RESPONSE = {
    "framework_id": "nist-800-53-r5",
    "total": 1,
    "results": [
        {
            "index": 0,
            "status": "created",
            "evidence_id": "ev-new",
            "control_id": "ac-02",
            "framework_id": "nist-800-53-r5",
        },
    ],
}


# ===========================================================================
# Test Classes
# ===========================================================================


class TestConfiguration:
    """Test client configuration and is_configured property."""

    def test_is_configured_with_api_key(self):
        client = PretorianClient(api_key="some-key", api_base_url=TEST_BASE_URL)
        assert client.is_configured is True

    def test_is_not_configured_without_api_key(self):
        with patch("pretorin.client.api.Config") as mock_config:
            mock_config.return_value.api_key = None
            mock_config.return_value.api_base_url = TEST_BASE_URL
            client = PretorianClient(api_key=None, api_base_url=TEST_BASE_URL)
        assert client.is_configured is False

    def test_headers_contain_bearer_token(self):
        client = PretorianClient(api_key="my-token", api_base_url=TEST_BASE_URL)
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer my-token"
        assert headers["Content-Type"] == "application/json"
        assert "User-Agent" in headers
        assert "pretorin-cli/" in headers["User-Agent"]

    def test_headers_without_api_key(self):
        with patch("pretorin.client.api.Config") as mock_config:
            mock_config.return_value.api_key = None
            mock_config.return_value.api_base_url = TEST_BASE_URL
            client = PretorianClient(api_key=None, api_base_url=TEST_BASE_URL)
        headers = client._get_headers()
        assert "Authorization" not in headers

    def test_base_url_trailing_slash_stripped(self):
        client = PretorianClient(api_key="k", api_base_url="https://example.com/api/")
        assert client._api_base_url == "https://example.com/api"


class TestContextManager:
    """Test async context manager lifecycle."""

    async def test_aenter_returns_self(self):
        client = PretorianClient(api_key="k", api_base_url=TEST_BASE_URL)
        async with client as c:
            assert c is client

    async def test_aexit_closes_client(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"frameworks": [], "total": 0})

        client = _make_client(handler)
        async with client:
            # Make a request so internal client is active
            await client.list_frameworks()
            assert client._client is not None
            assert not client._client.is_closed
        # After exiting, client should be cleaned up
        assert client._client is None

    async def test_close_idempotent(self):
        client = PretorianClient(api_key="k", api_base_url=TEST_BASE_URL)
        # Closing without ever creating _client should not raise
        await client.close()
        await client.close()


class TestRequestLifecycle:
    """Test the _request method makes correct HTTP calls."""

    async def test_get_request_with_params(self):
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["path"] = request.url.path
            captured["query"] = str(request.url.query)
            return httpx.Response(200, json=[])

        client = _make_client(handler)
        await client._request("GET", "/frameworks/nist/controls", params={"family_id": "ac"})
        assert captured["method"] == "GET"
        assert captured["path"] == "/api/v1/public/frameworks/nist/controls"
        assert "family_id=ac" in captured["query"]

    async def test_post_request_with_json_body(self):
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["method"] = request.method
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={"id": "new"})

        client = _make_client(handler)
        await client._request("POST", "/artifacts", json={"framework_id": "nist"})
        assert captured["method"] == "POST"
        assert captured["body"] == {"framework_id": "nist"}

    async def test_204_returns_empty_dict(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(204)

        client = _make_client(handler)
        result = await client._request("DELETE", "/some-resource")
        assert result == {}

    async def test_json_response_parsed(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"key": "value", "count": 42})

        client = _make_client(handler)
        result = await client._request("GET", "/something")
        assert result == {"key": "value", "count": 42}


class TestErrorHandling:
    """Test HTTP error status codes are mapped to correct exceptions."""

    async def test_401_raises_authentication_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"detail": "Invalid API key"})

        client = _make_client(handler)
        with pytest.raises(AuthenticationError) as exc_info:
            await client._request("GET", "/frameworks")
        assert exc_info.value.status_code == 401
        assert "Invalid API key" in str(exc_info.value)

    async def test_403_raises_authentication_error_with_access_denied(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, json={"detail": "Forbidden resource"})

        client = _make_client(handler)
        with pytest.raises(AuthenticationError) as exc_info:
            await client._request("GET", "/restricted")
        assert exc_info.value.status_code == 403
        assert "Access denied" in str(exc_info.value)

    async def test_404_raises_not_found_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, json={"detail": "Control not found"})

        client = _make_client(handler)
        with pytest.raises(NotFoundError) as exc_info:
            await client._request("GET", "/frameworks/nist/controls/zz-99")
        assert exc_info.value.status_code == 404
        assert "Control not found" in str(exc_info.value)

    async def test_500_raises_client_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"detail": "Internal server error"})

        client = _make_client(handler)
        with pytest.raises(PretorianClientError) as exc_info:
            await client._request("GET", "/frameworks")
        assert exc_info.value.status_code == 500

    async def test_error_with_message_field(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, json={"message": "Validation failed"})

        client = _make_client(handler)
        with pytest.raises(PretorianClientError) as exc_info:
            await client._request("POST", "/artifacts")
        assert "Validation failed" in str(exc_info.value)

    async def test_error_with_non_json_body(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(502, text="Bad Gateway")

        client = _make_client(handler)
        with pytest.raises(PretorianClientError) as exc_info:
            await client._request("GET", "/frameworks")
        assert "Bad Gateway" in str(exc_info.value)

    async def test_error_with_non_dict_json(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, json=["error1", "error2"])

        client = _make_client(handler)
        with pytest.raises(PretorianClientError) as exc_info:
            await client._request("GET", "/frameworks")
        # The message should be stringified list, and details should be empty dict
        assert exc_info.value.details == {}

    async def test_error_details_populated(self):
        error_body = {"detail": "Quota exceeded", "limit": 100}

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json=error_body)

        client = _make_client(handler)
        with pytest.raises(PretorianClientError) as exc_info:
            await client._request("GET", "/frameworks")
        assert exc_info.value.details == error_body


class TestNetworkErrors:
    """Test network-level errors are wrapped in PretorianClientError."""

    async def test_connect_error_wrapped(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        client = _make_client(handler)
        with pytest.raises(PretorianClientError, match="Could not connect"):
            await client._request("GET", "/frameworks")

    async def test_timeout_error_wrapped(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("Read timed out")

        client = _make_client(handler)
        with pytest.raises(PretorianClientError, match="timed out"):
            await client._request("GET", "/frameworks")

    async def test_generic_http_error_wrapped(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.DecodingError("Invalid encoding")

        client = _make_client(handler)
        with pytest.raises(PretorianClientError, match="HTTP error"):
            await client._request("GET", "/frameworks")


class TestValidateApiKey:
    """Test API key validation."""

    async def test_validate_api_key_success(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"frameworks": [], "total": 0})

        client = _make_client(handler)
        result = await client.validate_api_key()
        assert result is True

    async def test_validate_api_key_missing_raises(self):
        with patch("pretorin.client.api.Config") as mock_config:
            mock_config.return_value.api_key = None
            mock_config.return_value.api_base_url = TEST_BASE_URL
            client = PretorianClient(api_key=None, api_base_url=TEST_BASE_URL)
        with pytest.raises(AuthenticationError, match="No API key configured"):
            await client.validate_api_key()

    async def test_validate_api_key_invalid_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, json={"detail": "Invalid key"})

        client = _make_client(handler)
        with pytest.raises(AuthenticationError):
            await client.validate_api_key()


class TestFrameworkEndpoints:
    """Test framework-related API methods."""

    async def test_list_frameworks_returns_model(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"total": 1, "frameworks": [FRAMEWORK_SUMMARY]},
            )

        client = _make_client(handler)
        result = await client.list_frameworks()
        assert isinstance(result, FrameworkList)
        assert result.total == 1
        assert len(result.frameworks) == 1
        assert result.frameworks[0].id == "nist-800-53-r5"

    async def test_get_framework_returns_model(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=FRAMEWORK_METADATA)

        client = _make_client(handler)
        result = await client.get_framework("nist-800-53-r5")
        assert isinstance(result, FrameworkMetadata)
        assert result.id == "nist-800-53-r5"
        assert result.title == "NIST SP 800-53 Revision 5"

    async def test_get_framework_sends_correct_path(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=FRAMEWORK_METADATA)

        client = _make_client(handler)
        await client.get_framework("fedramp-moderate")
        assert captured_path == "/api/v1/public/frameworks/fedramp-moderate"


class TestControlFamilyEndpoints:
    """Test control family API methods."""

    async def test_list_control_families(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[CONTROL_FAMILY_SUMMARY])

        client = _make_client(handler)
        result = await client.list_control_families("nist-800-53-r5")
        assert len(result) == 1
        assert isinstance(result[0], ControlFamilySummary)
        assert result[0].id == "ac"

    async def test_get_control_family(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=CONTROL_FAMILY_DETAIL)

        client = _make_client(handler)
        result = await client.get_control_family("nist-800-53-r5", "ac")
        assert isinstance(result, ControlFamilyDetail)
        assert result.id == "ac"
        assert len(result.controls) == 2

    async def test_get_control_family_sends_correct_path(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_FAMILY_DETAIL)

        client = _make_client(handler)
        await client.get_control_family("nist-800-53-r5", "ac")
        assert captured_path == "/api/v1/public/frameworks/nist-800-53-r5/families/ac"


class TestControlEndpoints:
    """Test control-related API methods."""

    async def test_list_controls_returns_models(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[CONTROL_SUMMARY])

        client = _make_client(handler)
        result = await client.list_controls("nist-800-53-r5")
        assert len(result) == 1
        assert isinstance(result[0], ControlSummary)
        assert result[0].id == "ac-02"

    async def test_list_controls_passes_family_id_param(self):
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=[CONTROL_SUMMARY])

        client = _make_client(handler)
        await client.list_controls("nist-800-53-r5", family_id="ac")
        assert captured_params.get("family_id") == "ac"

    async def test_list_controls_no_family_id_sends_no_param(self):
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=[])

        client = _make_client(handler)
        await client.list_controls("nist-800-53-r5")
        assert "family_id" not in captured_params

    async def test_get_control_normalizes_id(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_DETAIL)

        client = _make_client(handler)
        # Pass unpadded "ac-2" which should be normalized to "ac-02"
        await client.get_control("nist-800-53-r5", "ac-2")
        assert captured_path is not None
        assert captured_path.endswith("/controls/ac-02")

    async def test_get_control_returns_model(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=CONTROL_DETAIL)

        client = _make_client(handler)
        result = await client.get_control("nist-800-53-r5", "ac-02")
        assert isinstance(result, ControlDetail)
        assert result.id == "ac-02"
        assert result.control_type == "system"

    async def test_get_controls_batch(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json=CONTROL_BATCH_RESPONSE)

        client = _make_client(handler)
        result = await client.get_controls_batch(
            "nist-800-53-r5",
            control_ids=["ac-1", "ac-2"],
            include_references=True,
        )
        assert isinstance(result, ControlBatchResponse)
        assert result.total == 2
        assert len(result.controls) == 2
        # Verify IDs were normalized in the request body
        assert captured_body["control_ids"] == ["ac-01", "ac-02"]
        assert captured_body["include_references"] is True

    async def test_get_controls_batch_no_ids(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json=CONTROL_BATCH_RESPONSE)

        client = _make_client(handler)
        await client.get_controls_batch("nist-800-53-r5")
        assert "control_ids" not in captured_body
        assert captured_body["include_references"] is False

    async def test_get_control_references(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_REFERENCES)

        client = _make_client(handler)
        result = await client.get_control_references("nist-800-53-r5", "ac-2")
        assert isinstance(result, ControlReferences)
        assert result.control_id == "ac-02"
        assert len(result.objectives) == 2
        # Verify normalization happened in the URL
        assert captured_path is not None
        assert "/ac-02/" in captured_path

    async def test_get_controls_metadata_with_framework(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_METADATA_RESPONSE)

        client = _make_client(handler)
        result = await client.get_controls_metadata("nist-800-53-r5")
        assert captured_path is not None
        assert captured_path.endswith("/frameworks/nist-800-53-r5/controls/metadata")
        assert "ac-01" in result
        assert isinstance(result["ac-01"], ControlMetadata)

    async def test_get_controls_metadata_without_framework(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_METADATA_RESPONSE)

        client = _make_client(handler)
        result = await client.get_controls_metadata()
        assert captured_path is not None
        assert captured_path.endswith("/frameworks/controls/metadata")
        assert len(result) == 2


class TestDocumentRequirementsEndpoint:
    """Test document requirements retrieval."""

    async def test_get_document_requirements(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=DOCUMENT_REQUIREMENTS)

        client = _make_client(handler)
        result = await client.get_document_requirements("fedramp-moderate")
        assert isinstance(result, DocumentRequirementList)
        assert result.framework_id == "fedramp-moderate"


class TestSystemEndpoints:
    """Test system-related API methods."""

    async def test_list_systems_handles_list_response(self):
        systems_list = [{"id": "sys-001", "name": "System A"}, {"id": "sys-002", "name": "System B"}]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=systems_list)

        client = _make_client(handler)
        result = await client.list_systems()
        assert len(result) == 2
        assert result[0]["id"] == "sys-001"

    async def test_list_systems_handles_paginated_dict_with_systems_key(self):
        paginated = {
            "systems": [{"id": "sys-001", "name": "System A"}],
            "total": 1,
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=paginated)

        client = _make_client(handler)
        result = await client.list_systems()
        assert len(result) == 1
        assert result[0]["id"] == "sys-001"

    async def test_list_systems_handles_paginated_dict_with_items_key(self):
        paginated = {
            "items": [{"id": "sys-001", "name": "System A"}],
            "total": 1,
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=paginated)

        client = _make_client(handler)
        result = await client.list_systems()
        assert len(result) == 1

    async def test_get_system_returns_model(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SYSTEM_DETAIL)

        client = _make_client(handler)
        result = await client.get_system("sys-001")
        assert isinstance(result, SystemDetail)
        assert result.id == "sys-001"
        assert result.name == "Test System"

    async def test_get_system_compliance_status(self):
        compliance_data = {
            "system_id": "sys-001",
            "frameworks": [{"id": "nist", "status": "partial"}],
        }

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=compliance_data)

        client = _make_client(handler)
        result = await client.get_system_compliance_status("sys-001")
        assert result["system_id"] == "sys-001"

    async def test_get_system_sends_correct_path(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=SYSTEM_DETAIL)

        client = _make_client(handler)
        await client.get_system("sys-123")
        assert captured_path == "/api/v1/public/systems/sys-123"


class TestEvidenceEndpoints:
    """Test evidence-related API methods."""

    async def test_list_evidence_handles_list_response(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[EVIDENCE_ITEM])

        client = _make_client(handler)
        result = await client.list_evidence("sys-001", "nist-800-53-r5")
        assert len(result) == 1
        assert isinstance(result[0], EvidenceItemResponse)
        assert result[0].id == "ev-001"

    async def test_list_evidence_handles_dict_with_items_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": [EVIDENCE_ITEM], "total": 1})

        client = _make_client(handler)
        result = await client.list_evidence("sys-001", "nist-800-53-r5")
        assert len(result) == 1

    async def test_list_evidence_handles_dict_with_evidence_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"evidence": [EVIDENCE_ITEM], "total": 1})

        client = _make_client(handler)
        result = await client.list_evidence("sys-001", "nist-800-53-r5")
        assert len(result) == 1

    async def test_list_evidence_passes_params(self):
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=[])

        client = _make_client(handler)
        await client.list_evidence("sys-001", "nist-800-53-r5", control_id="ac-2", limit=50)
        assert captured_params["framework_id"] == "nist-800-53-r5"
        assert captured_params["control_id"] == "ac-02"  # normalized
        assert captured_params["limit"] == "50"

    async def test_list_evidence_omits_control_id_when_none(self):
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=[])

        client = _make_client(handler)
        await client.list_evidence("sys-001", "nist-800-53-r5")
        assert "control_id" not in captured_params

    async def test_get_evidence(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=EVIDENCE_ITEM)

        client = _make_client(handler)
        result = await client.get_evidence("ev-001")
        assert isinstance(result, EvidenceItemResponse)
        assert result.id == "ev-001"

    async def test_create_evidence(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "ev-new"})

        client = _make_client(handler)
        evidence = EvidenceCreate(
            name="New Evidence",
            description="Description",
            control_id="ac-2",
        )
        result = await client.create_evidence("sys-001", evidence)
        assert result["id"] == "ev-new"
        assert captured_body["control_id"] == "ac-02"  # normalized

    async def test_create_evidence_no_control_id(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "ev-new"})

        client = _make_client(handler)
        evidence = EvidenceCreate(
            name="New Evidence",
            description="Description",
        )
        result = await client.create_evidence("sys-001", evidence)
        assert result["id"] == "ev-new"
        # control_id should not be present (excluded by exclude_none)
        assert "control_id" not in captured_body or captured_body.get("control_id") is None

    async def test_create_evidence_batch(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json=EVIDENCE_BATCH_RESPONSE)

        client = _make_client(handler)
        items = [
            EvidenceBatchItemCreate(
                name="Evidence A",
                description="Desc A",
                control_id="ac-2",
            ),
        ]
        result = await client.create_evidence_batch("sys-001", "nist-800-53-r5", items)
        assert isinstance(result, EvidenceBatchResponse)
        assert result.total == 1
        assert captured_body["framework_id"] == "nist-800-53-r5"
        assert captured_body["items"][0]["control_id"] == "ac-02"

    async def test_link_evidence_to_control(self):
        captured_body: dict[str, Any] = {}
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"status": "linked"})

        client = _make_client(handler)
        result = await client.link_evidence_to_control(
            evidence_id="ev-001",
            control_id="ac-2",
            system_id="sys-001",
            framework_id="nist-800-53-r5",
        )
        assert result["status"] == "linked"
        assert captured_body["control_id"] == "ac-02"
        assert captured_body["framework_id"] == "nist-800-53-r5"
        assert captured_path is not None
        assert "/evidence/ev-001/link" in captured_path


class TestNarrativeEndpoints:
    """Test narrative-related API methods."""

    async def test_get_narrative(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=NARRATIVE_RESPONSE)

        client = _make_client(handler)
        result = await client.get_narrative("sys-001", "ac-02", "nist-800-53-r5")
        assert isinstance(result, NarrativeResponse)
        assert result.control_id == "ac-02"

    async def test_get_narrative_normalizes_control_id(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=NARRATIVE_RESPONSE)

        client = _make_client(handler)
        await client.get_narrative("sys-001", "ac-2", "nist-800-53-r5")
        assert captured_path is not None
        assert "/ac-02/" in captured_path

    async def test_update_narrative_calls_ensure_audit_markdown(self):
        """update_narrative should call ensure_audit_markdown before sending the request."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"status": "updated"})

        client = _make_client(handler)
        # A narrative without enough rich elements should fail validation
        with pytest.raises(ValueError, match="markdown requirements failed"):
            await client.update_narrative(
                "sys-001", "ac-02", "Plain text without any markdown", "nist-800-53-r5"
            )

    async def test_update_narrative_success(self):
        captured_body: dict[str, Any] = {}
        captured_params: dict[str, str] = {}
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            captured_body.update(json.loads(request.content))
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json={"status": "updated"})

        client = _make_client(handler)
        # Use a well-formatted narrative that passes markdown validation
        good_narrative = (
            "Account management is implemented through centralized identity provider.\n\n"
            "- Accounts are provisioned through SSO\n"
            "- Deprovisioning follows HR offboarding workflow\n"
            "- Quarterly access reviews are performed\n\n"
            "```\nSSO Provider: Okta\nMFA: Required for all users\n```\n\n"
            "For more details, see the [Access Control Policy](https://example.com/policy)."
        )
        result = await client.update_narrative(
            "sys-001", "ac-2", good_narrative, "nist-800-53-r5", is_ai_generated=True
        )
        assert result == {"status": "updated"}
        assert captured_body["narrative"] == good_narrative
        assert captured_body["is_ai_generated"] is True
        assert captured_params["framework_id"] == "nist-800-53-r5"
        # Verify control ID was normalized in path
        assert captured_path is not None
        assert "/ac-02/" in captured_path


class TestControlImplementationEndpoints:
    """Test control implementation and context methods."""

    async def test_get_control_implementation(self):
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=CONTROL_IMPLEMENTATION)

        client = _make_client(handler)
        result = await client.get_control_implementation("sys-001", "ac-2", "nist-800-53-r5")
        assert isinstance(result, ControlImplementationResponse)
        assert result.control_id == "ac-02"
        assert result.status == "implemented"
        assert captured_params["framework_id"] == "nist-800-53-r5"

    async def test_get_control_context(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json=CONTROL_CONTEXT)

        client = _make_client(handler)
        result = await client.get_control_context("sys-001", "ac-2", "nist-800-53-r5")
        assert isinstance(result, ControlContext)
        assert result.control_id == "ac-02"
        assert captured_path is not None
        assert "/ac-02/context" in captured_path

    async def test_get_scope(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=SCOPE_RESPONSE)

        client = _make_client(handler)
        result = await client.get_scope("sys-001", "nist-800-53-r5")
        assert isinstance(result, ScopeResponse)
        assert result.scope_status == "complete"
        assert result.scope_questions[0].id == "sd-1"
        assert result.scope_review is not None
        assert result.scope_review.gaps[0].area == "boundary"

    async def test_patch_scope_qa(self):
        captured_body: dict[str, Any] = {}
        captured_params: dict[str, str] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json=SCOPE_RESPONSE)

        client = _make_client(handler)
        result = await client.patch_scope_qa(
            "sys-001",
            "nist-800-53-r5",
            [{"question_id": "sd-1", "answer": "Updated answer"}],
        )

        assert isinstance(result, ScopeResponse)
        assert captured_body == {"updates": [{"question_id": "sd-1", "answer": "Updated answer"}]}
        assert captured_params["framework_id"] == "nist-800-53-r5"
        assert result.scope_qa_responses["questions"][0]["answer"] == "Existing answer"

    async def test_list_org_policies(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ORG_POLICY_LIST_RESPONSE)

        client = _make_client(handler)
        result = await client.list_org_policies()

        assert isinstance(result, OrgPolicyListResponse)
        assert result.total == 1
        assert result.policies[0].policy_template_id == "access-control-policy"

    async def test_get_org_policy_questionnaire(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=ORG_POLICY_QUESTIONNAIRE_RESPONSE)

        client = _make_client(handler)
        result = await client.get_org_policy_questionnaire("pol-001")

        assert isinstance(result, OrgPolicyQuestionnaireResponse)
        assert result.policy_id == "pol-001"
        assert result.template is not None
        assert result.template.questions[0].guidance.common_mistakes == ["Being too vague"]
        assert result.policy_review is not None
        assert result.policy_review.recommended_changes[0].section == "Scope"

    async def test_patch_org_policy_qa(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json=ORG_POLICY_QUESTIONNAIRE_RESPONSE)

        client = _make_client(handler)
        result = await client.patch_org_policy_qa(
            "pol-001",
            [{"question_id": "q_purpose_1", "answer": "Updated purpose"}],
        )

        assert isinstance(result, OrgPolicyQuestionnaireResponse)
        assert captured_body == {"updates": [{"question_id": "q_purpose_1", "answer": "Updated purpose"}]}
        assert result.policy_qa_responses["questions"][0]["id"] == "q_purpose_1"


class TestControlNotesEndpoints:
    """Test control notes add/list methods."""

    async def test_add_control_note(self):
        captured_body: dict[str, Any] = {}
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "note-001", "content": "Test note"})

        client = _make_client(handler)
        result = await client.add_control_note(
            "sys-001", "ac-2", "Test note", "nist-800-53-r5", source="mcp"
        )
        assert result["id"] == "note-001"
        assert captured_body["content"] == "Test note"
        assert captured_body["source"] == "mcp"
        assert captured_path is not None
        assert "/ac-02/notes" in captured_path

    async def test_list_control_notes_list_response(self):
        notes = [{"id": "note-1", "content": "Note 1"}, {"id": "note-2", "content": "Note 2"}]

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=notes)

        client = _make_client(handler)
        result = await client.list_control_notes("sys-001", "ac-02", "nist-800-53-r5")
        assert len(result) == 2

    async def test_list_control_notes_dict_with_notes_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"notes": [{"id": "n1"}], "total": 1})

        client = _make_client(handler)
        result = await client.list_control_notes("sys-001", "ac-02", "nist-800-53-r5")
        assert len(result) == 1

    async def test_list_control_notes_dict_with_items_key(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"items": [{"id": "n1"}], "total": 1})

        client = _make_client(handler)
        result = await client.list_control_notes("sys-001", "ac-02", "nist-800-53-r5")
        assert len(result) == 1


class TestUpdateControlStatus:
    """Test control status update method."""

    async def test_update_control_status(self):
        captured_body: dict[str, Any] = {}
        captured_params: dict[str, str] = {}
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            captured_body.update(json.loads(request.content))
            for key, value in request.url.params.items():
                captured_params[key] = value
            return httpx.Response(200, json={"status": "implemented"})

        client = _make_client(handler)
        result = await client.update_control_status(
            "sys-001", "ac-2", "implemented", "nist-800-53-r5"
        )
        assert result["status"] == "implemented"
        assert captured_body["status"] == "implemented"
        assert captured_params["framework_id"] == "nist-800-53-r5"
        assert captured_path is not None
        assert "/ac-02/status" in captured_path


class TestMonitoringEndpoints:
    """Test monitoring event creation."""

    async def test_create_monitoring_event(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "evt-001", "status": "created"})

        client = _make_client(handler)
        event = MonitoringEventCreate(
            event_type="security_scan",
            title="Weekly Scan",
            description="Automated weekly vulnerability scan",
            severity="medium",
            control_id="ra-5",
            framework_id="nist-800-53-r5",
        )
        result = await client.create_monitoring_event("sys-001", event)
        assert result["id"] == "evt-001"
        # control_id should be normalized
        assert captured_body["control_id"] == "ra-05"

    async def test_create_monitoring_event_no_control_id(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"id": "evt-002"})

        client = _make_client(handler)
        event = MonitoringEventCreate(
            title="General Event",
            description="An event without a control",
        )
        result = await client.create_monitoring_event("sys-001", event)
        assert result["id"] == "evt-002"
        # control_id should not have been normalized (it's None/not present)
        assert captured_body.get("control_id") is None or "control_id" not in captured_body


class TestSubmitArtifact:
    """Test compliance artifact submission."""

    async def test_submit_artifact_normalizes_control_ids(self):
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content))
            return httpx.Response(200, json={"artifact_id": "art-001", "url": "https://example.com"})

        client = _make_client(handler)
        from pretorin.client.models import (
            ComplianceArtifact,
            ComponentDefinition,
            ImplementationStatement,
        )

        artifact = ComplianceArtifact(
            framework_id="nist-800-53-r5",
            control_id="ac-2",
            component=ComponentDefinition(
                component_id="my-app",
                title="My Application",
                description="A web application",
                type="software",
                control_implementations=[
                    ImplementationStatement(
                        control_id="ac-2",
                        description="Accounts managed centrally.",
                        implementation_status="implemented",
                    ),
                ],
            ),
        )
        result = await client.submit_artifact(artifact)
        assert result["artifact_id"] == "art-001"
        # Top-level control_id normalized
        assert captured_body["control_id"] == "ac-02"
        # Nested implementation control_ids also normalized
        impl = captured_body["component"]["control_implementations"][0]
        assert impl["control_id"] == "ac-02"

    async def test_submit_artifact_sends_to_artifacts_endpoint(self):
        captured_path = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_path
            captured_path = request.url.path
            return httpx.Response(200, json={"artifact_id": "art-001"})

        client = _make_client(handler)
        from pretorin.client.models import (
            ComplianceArtifact,
            ComponentDefinition,
        )

        artifact = ComplianceArtifact(
            framework_id="nist-800-53-r5",
            control_id="ac-02",
            component=ComponentDefinition(
                component_id="my-app",
                title="My Application",
                description="A web application",
            ),
        )
        await client.submit_artifact(artifact)
        assert captured_path == "/api/v1/public/artifacts"


class TestNormalizeControlId:
    """Test the static _normalize_control_id helper."""

    def test_normalize_none_returns_none(self):
        assert PretorianClient._normalize_control_id(None) is None

    def test_normalize_pads_single_digit(self):
        assert PretorianClient._normalize_control_id("ac-2") == "ac-02"

    def test_normalize_already_padded(self):
        assert PretorianClient._normalize_control_id("ac-02") == "ac-02"

    def test_normalize_uppercase(self):
        assert PretorianClient._normalize_control_id("AC-3") == "ac-03"

    def test_normalize_with_enhancement(self):
        assert PretorianClient._normalize_control_id("ac-2.1") == "ac-02.1"


class TestGetClientLazyInit:
    """Test that _get_client lazily initializes the HTTP client."""

    async def test_client_created_on_first_call(self):
        client = PretorianClient(api_key="k", api_base_url=TEST_BASE_URL)
        assert client._client is None
        http_client = await client._get_client()
        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        await client.close()

    async def test_client_reused_on_subsequent_calls(self):
        client = PretorianClient(api_key="k", api_base_url=TEST_BASE_URL)
        c1 = await client._get_client()
        c2 = await client._get_client()
        assert c1 is c2
        await client.close()

    async def test_client_recreated_after_close(self):
        client = PretorianClient(api_key="k", api_base_url=TEST_BASE_URL)
        c1 = await client._get_client()
        await client.close()
        c2 = await client._get_client()
        assert c1 is not c2
        await client.close()
