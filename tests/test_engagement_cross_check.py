"""Tests for the engagement-layer cross-check.

The cross-check runs platform reads (list_systems, list_frameworks,
get_control, get_system_compliance_status). Tests stub each with the
shape the real client returns and verify the entity-coherence rules.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.client.api import PretorianClientError
from pretorin.engagement.cross_check import cross_check_entities
from pretorin.engagement.entities import EngagementEntities


def _entities(**kw):
    kw.setdefault("intent_verb", "work_on")
    kw.setdefault("raw_prompt", "test")
    return EngagementEntities(**kw)


def _client_with(
    *,
    systems=(),
    frameworks=(),
    control_lookup=None,
    compliance_status_by_system=None,
):
    """Build a MagicMock client with the methods cross_check uses."""
    client = MagicMock()
    client.list_systems = AsyncMock(return_value=list(systems))

    framework_objs = MagicMock()
    framework_objs.frameworks = list(frameworks)
    client.list_frameworks = AsyncMock(return_value=framework_objs)

    async def _get_control(framework_id, control_id):
        if control_lookup is None:
            raise PretorianClientError("no controls registered")
        if (framework_id, control_id) in control_lookup:
            return MagicMock()
        raise PretorianClientError(f"control {control_id} not in {framework_id}")

    client.get_control = _get_control

    async def _status(system_id):
        if compliance_status_by_system is None:
            return {"frameworks": []}
        return compliance_status_by_system.get(system_id, {"frameworks": []})

    client.get_system_compliance_status = _status
    return client


# =============================================================================
# System resolution
# =============================================================================


@pytest.mark.asyncio
async def test_unknown_system_id_is_hard_error() -> None:
    client = _client_with(systems=[{"id": "sys-1", "name": "Primary"}])
    result = await cross_check_entities(client, _entities(system_id="sys-zz"))
    assert result.has_hard_error
    assert any("not found" in msg for msg in result.hard_errors)


@pytest.mark.asyncio
async def test_friendly_name_resolves_to_id() -> None:
    client = _client_with(systems=[{"id": "sys-abc123", "name": "Production"}])
    result = await cross_check_entities(client, _entities(system_id="Production"))
    assert not result.has_hard_error
    assert result.resolved_system_id == "sys-abc123"


@pytest.mark.asyncio
async def test_cross_system_active_context_is_ambiguity() -> None:
    """If the named system doesn't match the active CLI context, flag."""
    client = _client_with(systems=[{"id": "sys-other", "name": "Other"}])
    result = await cross_check_entities(
        client,
        _entities(system_id="sys-other"),
        active_system_id="sys-active",
    )
    assert not result.has_hard_error
    assert result.has_ambiguity
    assert any("does not match the active CLI context" in m for m in result.ambiguities)


# =============================================================================
# Framework resolution
# =============================================================================


@pytest.mark.asyncio
async def test_unknown_framework_is_hard_error() -> None:
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_with(frameworks=[f])
    result = await cross_check_entities(client, _entities(framework_id="bogus"))
    assert result.has_hard_error


@pytest.mark.asyncio
async def test_framework_not_attached_to_system_is_ambiguity() -> None:
    f1 = MagicMock()
    f1.id = "fedramp-moderate"
    f2 = MagicMock()
    f2.id = "nist-800-53-r5"
    client = _client_with(
        systems=[{"id": "sys-1", "name": "Primary"}],
        frameworks=[f1, f2],
        compliance_status_by_system={"sys-1": {"frameworks": [{"framework_id": "nist-800-53-r5"}]}},
    )
    result = await cross_check_entities(
        client,
        _entities(system_id="sys-1", framework_id="fedramp-moderate"),
    )
    assert not result.has_hard_error
    assert result.has_ambiguity
    assert any("not attached to system" in m for m in result.ambiguities)


# =============================================================================
# Control coherence
# =============================================================================


@pytest.mark.asyncio
async def test_unknown_control_in_any_framework_is_hard_error() -> None:
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_with(
        frameworks=[f],
        control_lookup={("nist-800-53-r5", "ac-2")},
    )
    result = await cross_check_entities(
        client,
        _entities(framework_id="nist-800-53-r5", control_ids=["zz-99"]),
    )
    assert result.has_hard_error


@pytest.mark.asyncio
async def test_control_in_wrong_framework_is_ambiguity() -> None:
    f1 = MagicMock()
    f1.id = "nist-800-53-r5"
    f2 = MagicMock()
    f2.id = "fedramp-moderate"
    client = _client_with(
        frameworks=[f1, f2],
        # ac-2 lives in nist-800-53-r5 but the user named fedramp-moderate.
        control_lookup={("nist-800-53-r5", "ac-2")},
    )
    result = await cross_check_entities(
        client,
        _entities(framework_id="fedramp-moderate", control_ids=["ac-2"]),
    )
    assert not result.has_hard_error
    assert result.has_ambiguity


@pytest.mark.asyncio
async def test_control_in_correct_framework_passes_clean() -> None:
    f = MagicMock()
    f.id = "nist-800-53-r5"
    client = _client_with(
        systems=[{"id": "sys-1", "name": "Primary"}],
        frameworks=[f],
        control_lookup={("nist-800-53-r5", "ac-2")},
        compliance_status_by_system={"sys-1": {"frameworks": [{"framework_id": "nist-800-53-r5"}]}},
    )
    result = await cross_check_entities(
        client,
        _entities(
            system_id="sys-1",
            framework_id="nist-800-53-r5",
            control_ids=["ac-2"],
        ),
    )
    assert not result.has_hard_error
    assert not result.has_ambiguity
    assert result.resolved_system_id == "sys-1"
    assert result.resolved_framework_id == "nist-800-53-r5"
