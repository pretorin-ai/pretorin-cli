"""Tests for the framework revision lifecycle client methods (GH #90).

Mocks the platform via httpx.MockTransport — no live API needed.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from pretorin.client.api import PretorianClient, PretorianClientError

TEST_BASE_URL = "https://test.pretorin.api/api/v1/public"
TEST_API_KEY = "test-api-key-12345"


def _make_client(handler) -> PretorianClient:
    client = PretorianClient(api_key=TEST_API_KEY, api_base_url=TEST_BASE_URL)
    transport = httpx.MockTransport(handler)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=TEST_BASE_URL,
        headers=client._get_headers(),
        timeout=60.0,
    )
    return client


def _minimal_artifact() -> dict[str, Any]:
    return {
        "framework_id": "acme-test",
        "version": "1.0",
        "source_format": "custom",
        "metadata": {"title": "Test", "version": "1.0", "last_modified": "2026-04-30T00:00:00Z"},
        "families": [],
    }


@pytest.mark.asyncio
async def test_create_custom_draft_sends_artifact_and_label():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "revision_id": "rev-uuid-1",
                "framework_id": "acme-test",
                "lifecycle_state": "draft",
                "version_label": "v1.0",
                "validation_status": "passed",
                "validation_report": {"valid": True, "errors": []},
            },
        )

    client = _make_client(handler)
    try:
        result = await client.create_custom_draft(
            framework_id="acme-test",
            artifact=_minimal_artifact(),
            version_label="v1.0",
        )
    finally:
        await client.close()

    assert captured["method"] == "POST"
    assert captured["path"].endswith("/frameworks/drafts/custom")
    assert captured["body"]["framework_id"] == "acme-test"
    assert captured["body"]["version_label"] == "v1.0"
    assert captured["body"]["artifact"]["framework_id"] == "acme-test"
    assert result["revision_id"] == "rev-uuid-1"
    assert result["lifecycle_state"] == "draft"


@pytest.mark.asyncio
async def test_create_custom_draft_omits_label_when_none():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"revision_id": "x", "lifecycle_state": "draft"})

    client = _make_client(handler)
    try:
        await client.create_custom_draft("acme", _minimal_artifact())
    finally:
        await client.close()

    assert "version_label" not in captured["body"]


@pytest.mark.asyncio
async def test_create_custom_draft_surfaces_validation_report_on_400():
    """The platform's 400 includes a structured validation_report — preserve it."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "detail": "Validation failed",
                "validation_report": {
                    "valid": False,
                    "errors": [
                        {"path": "families.0.id", "message": "is required"},
                        {"path": "metadata.title", "message": "is required"},
                    ],
                    "checks": {"schema": "fail"},
                },
            },
        )

    client = _make_client(handler)
    try:
        with pytest.raises(PretorianClientError) as exc_info:
            await client.create_custom_draft("acme", _minimal_artifact())
    finally:
        await client.close()

    assert exc_info.value.status_code == 400
    assert "validation_report" in exc_info.value.details
    assert len(exc_info.value.details["validation_report"]["errors"]) == 2


@pytest.mark.asyncio
async def test_publish_draft_targets_correct_path():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["path"] = request.url.path
        return httpx.Response(200, json={"lifecycle_state": "published"})

    client = _make_client(handler)
    try:
        result = await client.publish_draft("acme-test", "rev-uuid-1")
    finally:
        await client.close()

    assert captured["method"] == "POST"
    assert captured["path"].endswith("/frameworks/acme-test/drafts/rev-uuid-1/publish")
    assert result["lifecycle_state"] == "published"


@pytest.mark.asyncio
async def test_fork_framework_sends_source_and_target():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["path"] = request.url.path
        return httpx.Response(
            200,
            json={
                "revision_id": "rev-fork-1",
                "framework_id": "acme-nist",
                "lifecycle_state": "draft",
                "upstream_base_revision_id": "upstream-uuid",
            },
        )

    client = _make_client(handler)
    try:
        result = await client.fork_framework(
            source_framework_id="nist-800-53-r5",
            new_framework_id="acme-nist",
            version_label="initial",
        )
    finally:
        await client.close()

    assert captured["path"].endswith("/frameworks/drafts/fork")
    assert captured["body"]["source_framework_id"] == "nist-800-53-r5"
    assert captured["body"]["new_framework_id"] == "acme-nist"
    assert captured["body"]["version_label"] == "initial"
    assert result["upstream_base_revision_id"] == "upstream-uuid"


@pytest.mark.asyncio
async def test_create_rebase_draft_uses_framework_path():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"revision_id": "rev-rebase-1"})

    client = _make_client(handler)
    try:
        await client.create_rebase_draft("acme-nist", version_label="rebase-1")
    finally:
        await client.close()

    assert captured["path"].endswith("/frameworks/acme-nist/rebase-drafts")
    assert captured["body"]["version_label"] == "rebase-1"


@pytest.mark.asyncio
async def test_create_rebase_draft_omits_label_when_none():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        return httpx.Response(200, json={"revision_id": "x"})

    client = _make_client(handler)
    try:
        await client.create_rebase_draft("acme")
    finally:
        await client.close()

    assert captured["body"] == {}


@pytest.mark.asyncio
async def test_list_revisions_returns_list():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/frameworks/acme-test/revisions")
        return httpx.Response(
            200,
            json=[
                {"id": "rev-1", "lifecycle_state": "published", "version_label": "v1.0"},
                {"id": "rev-2", "lifecycle_state": "draft", "version_label": "v1.1"},
            ],
        )

    client = _make_client(handler)
    try:
        result = await client.list_revisions("acme-test")
    finally:
        await client.close()

    assert len(result) == 2
    assert result[0]["lifecycle_state"] == "published"
    assert result[1]["lifecycle_state"] == "draft"
