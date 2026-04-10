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


@pytest.mark.asyncio
async def test_resolve_execution_context_rejects_stale_environment() -> None:
    """When both system and framework fall back to stored config, environment mismatch should be caught."""
    from unittest.mock import MagicMock, patch

    mock_config = MagicMock()
    mock_config.check_context_environment.return_value = (
        "Context was set against 'https://localhost:8000' but the current API environment is "
        "'https://platform.pretorin.com'. Run 'pretorin context set' to update your context."
    )
    mock_config.get.side_effect = lambda key, *a: {
        "active_system_id": "sys-1",
        "active_framework_id": "fedramp-moderate",
    }.get(key)

    client = AsyncMock()
    with patch("pretorin.client.config.Config", return_value=mock_config):
        with pytest.raises(PretorianClientError, match="Context was set against"):
            await resolve_execution_context(client)


@pytest.mark.asyncio
async def test_resolve_execution_context_skips_env_check_with_explicit_args() -> None:
    """When explicit system/framework are passed, environment check should not fire."""
    from pretorin.client import config as config_module

    client = AsyncMock()
    client.list_systems = AsyncMock(return_value=[{"id": "sys-1", "name": "Test System"}])
    client.get_system_compliance_status = AsyncMock(
        return_value={"frameworks": [{"framework_id": "fedramp-moderate"}]}
    )

    # Even if stored context URL is stale, explicit args should bypass the check.
    system_id, framework_id = await resolve_execution_context(
        client,
        system="sys-1",
        framework="fedramp-moderate",
    )
    assert system_id == "sys-1"
    assert framework_id == "fedramp-moderate"
