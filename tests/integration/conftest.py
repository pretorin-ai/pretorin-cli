"""Fixtures for integration tests."""

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio

from pretorin.client import PretorianClient


@pytest.fixture
def api_key() -> str:
    """Get API key from environment or skip test."""
    key = os.environ.get("PRETORIN_API_KEY")
    if not key:
        pytest.skip("PRETORIN_API_KEY environment variable not set")
    return key


@pytest_asyncio.fixture
async def authenticated_client(api_key: str) -> AsyncIterator[PretorianClient]:
    """Create an authenticated PretorianClient for testing.

    Uses the API key from the environment variable.
    """
    # Set the API key in environment for the client to pick up
    os.environ["PRETORIN_API_KEY"] = api_key

    async with PretorianClient() as client:
        yield client


# Common test data - framework ID is stable
KNOWN_FRAMEWORK_ID = "nist-800-53-r5"
