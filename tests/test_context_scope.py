"""Tests for CLI execution-scope resolution."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from pretorin.cli.context import resolve_execution_context
from pretorin.client.api import PretorianClientError


@pytest.mark.asyncio
async def test_resolve_execution_context_validates_framework_membership() -> None:
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )

    system_id, framework_id = await resolve_execution_context(
        client,
        system="sys-1",
        framework="fedramp-moderate",
    )

    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"


@pytest.mark.asyncio
async def test_resolve_execution_context_rejects_multi_framework_requests() -> None:
    client = AsyncMock()

    with pytest.raises(PretorianClientError, match="Framework scope must target exactly one framework"):
        await resolve_execution_context(
            client,
            system="sys-1",
            framework="fedramp-low and fedramp-moderate",
        )


@pytest.mark.asyncio
async def test_resolve_execution_context_rejects_wrong_framework_for_system() -> None:
    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )

    with pytest.raises(PretorianClientError, match="not associated with system"):
        await resolve_execution_context(
            client,
            system="sys-1",
            framework="fedramp-high",
        )
