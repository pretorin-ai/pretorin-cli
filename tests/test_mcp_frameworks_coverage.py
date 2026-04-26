"""Tests for src/pretorin/mcp/handlers/frameworks.py.

Covers all eight handler functions with mock client responses.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from pretorin.mcp.handlers.frameworks import (
    handle_get_control,
    handle_get_control_references,
    handle_get_controls_batch,
    handle_get_document_requirements,
    handle_get_framework,
    handle_list_control_families,
    handle_list_controls,
    handle_list_frameworks,
)

# ---------------------------------------------------------------------------
# handle_list_frameworks
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_list_frameworks() -> None:
    client = AsyncMock()
    client.list_frameworks = AsyncMock(
        return_value=SimpleNamespace(
            total=1,
            frameworks=[
                SimpleNamespace(
                    external_id="fedramp-moderate",
                    title="FedRAMP Moderate",
                    version="5.0",
                    tier="operational",
                    category="federal",
                    families_count=18,
                    controls_count=325,
                )
            ],
        )
    )

    result = await handle_list_frameworks(client, {})

    assert len(result) == 1
    data = json.loads(result[0].text)
    assert data["total"] == 1
    assert data["frameworks"][0]["id"] == "fedramp-moderate"
    assert data["frameworks"][0]["title"] == "FedRAMP Moderate"
    assert data["frameworks"][0]["controls_count"] == 325


@pytest.mark.asyncio
async def test_handle_list_frameworks_empty() -> None:
    client = AsyncMock()
    client.list_frameworks = AsyncMock(return_value=SimpleNamespace(total=0, frameworks=[]))

    result = await handle_list_frameworks(client, {})
    data = json.loads(result[0].text)
    assert data["total"] == 0
    assert data["frameworks"] == []


# ---------------------------------------------------------------------------
# handle_get_framework
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_get_framework() -> None:
    client = AsyncMock()
    client.get_framework = AsyncMock(
        return_value=SimpleNamespace(
            external_id="fedramp-moderate",
            title="FedRAMP Moderate",
            version="5.0",
            oscal_version="1.1.2",
            description="FedRAMP Moderate baseline",
            tier="operational",
            category="federal",
            published="2023-01-01",
            last_modified="2024-06-01",
            ai_context="Use for federal cloud systems.",
        )
    )

    result = await handle_get_framework(client, {"framework_id": "fedramp-moderate"})

    data = json.loads(result[0].text)
    assert data["id"] == "fedramp-moderate"
    assert data["oscal_version"] == "1.1.2"
    assert data["description"] == "FedRAMP Moderate baseline"
    assert data["ai_context"] == "Use for federal cloud systems."
    client.get_framework.assert_called_once_with("fedramp-moderate")


# ---------------------------------------------------------------------------
# handle_list_control_families
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_list_control_families() -> None:
    client = AsyncMock()
    client.list_control_families = AsyncMock(
        return_value=[
            SimpleNamespace(
                id="ac",
                title="Access Control",
                class_type="SP800-53",
                controls_count=25,
                ai_context="Controls for access management.",
            ),
            SimpleNamespace(
                id="au",
                title="Audit and Accountability",
                class_type="SP800-53",
                controls_count=16,
                ai_context="Controls for auditing.",
            ),
        ]
    )

    result = await handle_list_control_families(client, {"framework_id": "fedramp-moderate"})

    data = json.loads(result[0].text)
    assert data["framework_id"] == "fedramp-moderate"
    assert data["total"] == 2
    families = data["families"]
    assert families[0]["id"] == "ac"
    assert families[0]["title"] == "Access Control"
    assert families[1]["id"] == "au"
    client.list_control_families.assert_called_once_with("fedramp-moderate")


# ---------------------------------------------------------------------------
# handle_list_controls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_list_controls_with_family_filter() -> None:
    client = AsyncMock()
    client.list_controls = AsyncMock(
        return_value=[
            SimpleNamespace(id="ac-02", title="Account Management", family_id="ac"),
            SimpleNamespace(id="ac-03", title="Access Enforcement", family_id="ac"),
        ]
    )

    result = await handle_list_controls(client, {"framework_id": "fedramp-moderate", "family_id": "ac"})

    data = json.loads(result[0].text)
    assert data["framework_id"] == "fedramp-moderate"
    assert data["family_id"] == "ac"
    assert data["total"] == 2
    assert data["controls"][0]["id"] == "ac-02"
    client.list_controls.assert_called_once_with("fedramp-moderate", "ac")


@pytest.mark.asyncio
async def test_handle_list_controls_without_family_filter() -> None:
    client = AsyncMock()
    client.list_controls = AsyncMock(return_value=[])

    result = await handle_list_controls(client, {"framework_id": "fedramp-moderate"})

    data = json.loads(result[0].text)
    assert data["total"] == 0
    client.list_controls.assert_called_once_with("fedramp-moderate", None)


# ---------------------------------------------------------------------------
# handle_get_control
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_get_control() -> None:
    client = AsyncMock()
    client.get_control = AsyncMock(
        return_value=SimpleNamespace(
            id="ac-02",
            title="Account Management",
            class_type="SP800-53",
            control_type="base",
            params=[{"id": "ac-02_prm_1", "label": "time period"}],
            parts=[{"id": "ac-02_smt", "name": "statement", "prose": "The organization manages accounts."}],
            controls=[SimpleNamespace(id="ac-02.01"), SimpleNamespace(id="ac-02.02")],
            ai_guidance="Focus on account lifecycle.",
        )
    )

    result = await handle_get_control(client, {"framework_id": "fedramp-moderate", "control_id": "ac-2"})

    data = json.loads(result[0].text)
    assert data["id"] == "ac-02"
    assert data["title"] == "Account Management"
    assert data["enhancements_count"] == 2
    assert data["ai_guidance"] == "Focus on account lifecycle."
    # control_id is normalized before the API call
    client.get_control.assert_called_once_with("fedramp-moderate", "ac-02")


@pytest.mark.asyncio
async def test_handle_get_control_no_enhancements() -> None:
    client = AsyncMock()
    client.get_control = AsyncMock(
        return_value=SimpleNamespace(
            id="sc-07",
            title="Boundary Protection",
            class_type="SP800-53",
            control_type="base",
            params=[],
            parts=[],
            controls=None,
            ai_guidance="",
        )
    )

    result = await handle_get_control(client, {"framework_id": "fedramp-moderate", "control_id": "sc-07"})

    data = json.loads(result[0].text)
    assert data["enhancements_count"] == 0


# ---------------------------------------------------------------------------
# handle_get_controls_batch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_get_controls_batch_with_model_dump() -> None:
    client = AsyncMock()
    batch_result = MagicMock()
    batch_result.model_dump = lambda: {"controls": [{"id": "ac-02"}, {"id": "sc-07"}], "total": 2}
    client.get_controls_batch = AsyncMock(return_value=batch_result)

    result = await handle_get_controls_batch(
        client,
        {"framework_id": "fedramp-moderate", "control_ids": ["ac-2", "sc-7"]},
    )

    data = json.loads(result[0].text)
    assert data["total"] == 2
    # control IDs are normalized before the batch call
    client.get_controls_batch.assert_called_once_with("fedramp-moderate", ["ac-02", "sc-07"])


@pytest.mark.asyncio
async def test_handle_get_controls_batch_no_ids() -> None:
    client = AsyncMock()
    batch_result = {"controls": [], "total": 0}
    client.get_controls_batch = AsyncMock(return_value=batch_result)

    result = await handle_get_controls_batch(client, {"framework_id": "fedramp-moderate"})

    client.get_controls_batch.assert_called_once_with("fedramp-moderate", None)
    data = json.loads(result[0].text)
    assert data["total"] == 0


# ---------------------------------------------------------------------------
# handle_get_control_references
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_get_control_references() -> None:
    client = AsyncMock()
    client.get_control_references = AsyncMock(
        return_value=SimpleNamespace(
            control_id="ac-02",
            title="Account Management",
            statement="The organization manages system accounts.",
            guidance="Account management includes establishing account types.",
            objectives=["Establish account types", "Manage accounts"],
            parameters={"ac-02_prm_1": "90 days"},
            related_controls=[
                SimpleNamespace(id="ac-03", title="Access Enforcement", family_id="ac"),
                SimpleNamespace(id="ia-02", title="Identification and Authentication", family_id="ia"),
            ],
        )
    )

    result = await handle_get_control_references(client, {"framework_id": "fedramp-moderate", "control_id": "ac-2"})

    data = json.loads(result[0].text)
    assert data["control_id"] == "ac-02"
    assert data["statement"] == "The organization manages system accounts."
    assert len(data["related_controls"]) == 2
    assert data["related_controls"][0]["id"] == "ac-03"
    client.get_control_references.assert_called_once_with("fedramp-moderate", "ac-02")


# ---------------------------------------------------------------------------
# handle_get_document_requirements
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_get_document_requirements() -> None:
    client = AsyncMock()
    client.get_document_requirements = AsyncMock(
        return_value=SimpleNamespace(
            framework_id="fedramp-moderate",
            framework_title="FedRAMP Moderate",
            total=2,
            explicit_documents=[
                SimpleNamespace(
                    id="doc-1",
                    document_name="System Security Plan",
                    description="Describes the security controls.",
                    is_required=True,
                    control_references=["ac-02", "sc-07"],
                )
            ],
            implicit_documents=[
                SimpleNamespace(
                    id="doc-2",
                    document_name="Risk Assessment",
                    description="Documents identified risks.",
                    control_references=["ra-03"],
                )
            ],
        )
    )

    result = await handle_get_document_requirements(client, {"framework_id": "fedramp-moderate"})

    data = json.loads(result[0].text)
    assert data["framework_id"] == "fedramp-moderate"
    assert data["framework_title"] == "FedRAMP Moderate"
    assert data["total"] == 2
    assert len(data["explicit_documents"]) == 1
    assert data["explicit_documents"][0]["document_name"] == "System Security Plan"
    assert data["explicit_documents"][0]["is_required"] is True
    assert len(data["implicit_documents"]) == 1
    assert data["implicit_documents"][0]["document_name"] == "Risk Assessment"
    client.get_document_requirements.assert_called_once_with("fedramp-moderate")


@pytest.mark.asyncio
async def test_handle_get_document_requirements_empty() -> None:
    client = AsyncMock()
    client.get_document_requirements = AsyncMock(
        return_value=SimpleNamespace(
            framework_id="nist-800-53-r5",
            framework_title="NIST 800-53 Rev 5",
            total=0,
            explicit_documents=[],
            implicit_documents=[],
        )
    )

    result = await handle_get_document_requirements(client, {"framework_id": "nist-800-53-r5"})

    data = json.loads(result[0].text)
    assert data["total"] == 0
    assert data["explicit_documents"] == []
    assert data["implicit_documents"] == []
