"""Additional coverage tests for src/pretorin/client/api.py.

Covers lines 181-184 (_handle_error 429 with Retry-After), 296-299 (_request
retry with unparseable Retry-After).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from pretorin.client.api import (
    PretorianClient,
    PretorianClientError,
    RateLimitError,
)

TEST_BASE_URL = "https://test.pretorin.api/api/v1/public"
TEST_API_KEY = "test-api-key-12345"


def _make_client(handler, api_key=TEST_API_KEY):
    """Create a PretorianClient with a MockTransport handler injected."""
    client = PretorianClient(api_key=api_key, api_base_url=TEST_BASE_URL)
    transport = httpx.MockTransport(handler)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=TEST_BASE_URL,
        headers=client._get_headers(),
        timeout=client._timeout,
    )
    return client


class TestHandleError429:
    """Tests for _handle_error with 429 status code."""

    def test_handle_error_429_with_valid_retry_after(self):
        """Lines 181-184: 429 with parseable Retry-After header."""
        response = httpx.Response(
            429,
            json={"detail": "Rate limited"},
            headers={"Retry-After": "30"},
            request=httpx.Request("GET", TEST_BASE_URL + "/test"),
        )
        client = PretorianClient(api_key=TEST_API_KEY, api_base_url=TEST_BASE_URL)

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_error(response)

        assert exc_info.value.retry_after == 30.0
        assert exc_info.value.status_code == 429
        assert "Rate limited" in exc_info.value.message

    def test_handle_error_429_with_unparseable_retry_after(self):
        """Lines 183-184: 429 with Retry-After that can't be parsed as float."""
        response = httpx.Response(
            429,
            json={"detail": "Too many requests"},
            headers={"Retry-After": "not-a-number"},
            request=httpx.Request("GET", TEST_BASE_URL + "/test"),
        )
        client = PretorianClient(api_key=TEST_API_KEY, api_base_url=TEST_BASE_URL)

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_error(response)

        assert exc_info.value.retry_after is None

    def test_handle_error_429_without_retry_after(self):
        """429 with no Retry-After header."""
        response = httpx.Response(
            429,
            json={"detail": "Rate limited"},
            request=httpx.Request("GET", TEST_BASE_URL + "/test"),
        )
        client = PretorianClient(api_key=TEST_API_KEY, api_base_url=TEST_BASE_URL)

        with pytest.raises(RateLimitError) as exc_info:
            client._handle_error(response)

        assert exc_info.value.retry_after is None


class TestRequestRetry429:
    """Tests for _request retry logic with 429."""

    @pytest.mark.asyncio
    async def test_request_retries_429_with_unparseable_retry_after(self):
        """Lines 296-299: 429 with Retry-After that falls to ValueError branch."""
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                return httpx.Response(
                    429,
                    json={"detail": "Rate limited"},
                    headers={"Retry-After": "invalid-value"},
                )
            return httpx.Response(200, json={"ok": True})

        client = _make_client(handler)
        with patch("pretorin.client.api._BACKOFF_BASE", 0.01), \
             patch("pretorin.client.api.asyncio.sleep"):
            result = await client._request("GET", "/test")

        assert result == {"ok": True}
        assert call_count == 4

    @pytest.mark.asyncio
    async def test_request_429_exhausts_retries(self):
        """429 exhausts retries and raises RateLimitError."""
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"detail": "Rate limited"},
                headers={"Retry-After": "1"},
            )

        client = _make_client(handler)
        with patch("pretorin.client.api.asyncio.sleep"):
            with pytest.raises(RateLimitError):
                await client._request("GET", "/test")
