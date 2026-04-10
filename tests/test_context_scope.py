"""Tests for CLI execution-scope resolution."""

from __future__ import annotations

from pathlib import Path
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
async def test_resolve_execution_context_rejects_stale_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """When both system and framework fall back to stored config, environment mismatch should be caught."""
    from pretorin.client import config as config_module

    monkeypatch.delenv("PRETORIN_PLATFORM_API_BASE_URL", raising=False)
    monkeypatch.delenv("PRETORIN_API_BASE_URL", raising=False)

    config_dir = Path(__file__).parent / "_tmp_ctx_env"
    config_file = config_dir / "config.json"
    monkeypatch.setattr(config_module, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(config_module, "CONFIG_FILE", config_file)

    try:
        cfg = config_module.Config()
        cfg.set("active_system_id", "sys-1")
        cfg.set("active_framework_id", "fedramp-moderate")
        cfg.context_api_base_url = "https://localhost:8000/api/v1/public"

        client = AsyncMock()
        with pytest.raises(PretorianClientError, match="Context was set against"):
            await resolve_execution_context(client)
    finally:
        import shutil

        shutil.rmtree(config_dir, ignore_errors=True)


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
