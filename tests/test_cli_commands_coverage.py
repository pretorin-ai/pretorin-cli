"""Comprehensive unit tests for src/pretorin/cli/commands.py.

Tests every command exposed by the frameworks sub-app:
  frameworks_list, framework_get, framework_families, framework_controls,
  control_get, framework_documents, family_get, framework_metadata,
  submit_artifact, and the _render_ai_guidance helper.

Pattern
-------
* CliRunner from typer.testing drives the CLI.
* PretorianClient is mocked via its async context-manager protocol so that
  no real HTTP calls are made.
* Each command is exercised for: JSON mode, Rich/table mode, not-authenticated
  guard, NotFoundError, AuthenticationError, PretorianClientError, and
  empty-result branches where they exist.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client.api import AuthenticationError, NotFoundError, PretorianClientError
from pretorin.client.models import (
    ControlDetail,
    ControlFamilyDetail,
    ControlFamilySummary,
    ControlInFamily,
    ControlMetadata,
    ControlReferences,
    ControlSummary,
    DocumentRequirement,
    DocumentRequirementList,
    FrameworkList,
    FrameworkMetadata,
    FrameworkSummary,
    RelatedControl,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_json_mode():
    """Ensure JSON mode is disabled before and after every test."""
    set_json_mode(False)
    yield
    set_json_mode(False)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _run_with_mock_client(args: list[str], client: AsyncMock):
    """Invoke the CLI with a fully mocked async PretorianClient."""
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    with patch("pretorin.cli.commands.PretorianClient", return_value=ctx):
        return runner.invoke(app, args)


def _authed_client(**kwargs) -> AsyncMock:
    """Return an AsyncMock client with is_configured=True."""
    client = AsyncMock()
    client.is_configured = True
    for key, value in kwargs.items():
        setattr(client, key, value)
    return client


def _unauthed_client() -> AsyncMock:
    """Return an AsyncMock client with is_configured=False."""
    client = AsyncMock()
    client.is_configured = False
    return client


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_FRAMEWORK_SUMMARY = FrameworkSummary(
    id="fw-1",
    external_id="fedramp-moderate",
    title="FedRAMP Moderate",
    version="rev-5",
    tier="operational",
    category="federal",
    families_count=17,
    controls_count=323,
)

_FRAMEWORK_LIST = FrameworkList(frameworks=[_FRAMEWORK_SUMMARY], total=1)

_FRAMEWORK_META = FrameworkMetadata(
    id="fw-1",
    external_id="fedramp-moderate",
    title="FedRAMP Moderate",
    version="rev-5",
    tier="operational",
    category="federal",
    description="FedRAMP Moderate baseline.",
)

_FAMILY_SUMMARY = ControlFamilySummary(
    **{"id": "access-control", "title": "Access Control", "class": "SP800-53", "controls_count": 25}
)

_CONTROL_IN_FAMILY = ControlInFamily(
    **{"id": "ac-02", "title": "Account Management", "class": "SP800-53"}
)

_FAMILY_DETAIL = ControlFamilyDetail(
    **{
        "id": "access-control",
        "title": "Access Control",
        "class": "SP800-53",
        "controls": [
            {"id": "ac-02", "title": "Account Management", "class": "SP800-53"},
            {"id": "ac-03", "title": "Access Enforcement", "class": "SP800-53"},
        ],
    }
)

_CONTROL_SUMMARY = ControlSummary(
    id="ac-02",
    title="Account Management",
    family_id="access-control",
)

_CONTROL_DETAIL = ControlDetail(
    **{
        "id": "ac-02",
        "title": "Account Management",
        "class": "SP800-53",
        "control_type": "system",
        "ai_guidance": {
            "overview": "Manage system accounts following least privilege.",
            "steps": ["Identify accounts", "Review quarterly"],
            "config": {"tool": "IAM", "policy": "strict"},
        },
        "params": [{"id": "ac-02_prm_1", "label": "account types"}],
        "controls": [{"id": "ac-02.01", "title": "Automated System Account Management"}],
    }
)

_CONTROL_REFS = ControlReferences(
    control_id="ac-02",
    title="Account Management",
    statement="The organization manages information system accounts.",
    guidance="Types of information system accounts include...",
    objectives=["Identify account types", "Assign account managers", "Review access"],
    related_controls=[
        RelatedControl(id="ac-03", title="Access Enforcement", family_id="access-control")
    ],
)

_DOC_REQUIREMENTS = DocumentRequirementList(
    framework_id="fedramp-moderate",
    framework_title="FedRAMP Moderate",
    explicit_documents=[
        DocumentRequirement(
            id="doc-1",
            document_name="System Security Plan",
            description="Comprehensive SSP",
            requirement_type="explicit",
            is_required=True,
        )
    ],
    implicit_documents=[
        DocumentRequirement(
            id="doc-2",
            document_name="Access Control Policy",
            description=None,
            requirement_type="implicit",
            is_required=False,
        )
    ],
    total=2,
)

_CONTROL_METADATA = {
    "ac-02": ControlMetadata(title="Account Management", family="access-control", type="system"),
    "ac-03": ControlMetadata(title="Access Enforcement", family="access-control", type="system"),
}


# ===========================================================================
# frameworks list
# ===========================================================================


class TestFrameworksList:
    def test_list_rich_output(self):
        client = _authed_client(list_frameworks=AsyncMock(return_value=_FRAMEWORK_LIST))
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 0
        assert "FedRAMP" in result.output or "fedramp" in result.output.lower()

    def test_list_json_output(self):
        client = _authed_client(list_frameworks=AsyncMock(return_value=_FRAMEWORK_LIST))
        result = _run_with_mock_client(["--json", "frameworks", "list"], client)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "frameworks" in data
        assert data["total"] == 1

    def test_list_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 1
        assert "Not logged in" in result.output

    def test_list_empty_frameworks(self):
        empty = FrameworkList(frameworks=[], total=0)
        client = _authed_client(list_frameworks=AsyncMock(return_value=empty))
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 0
        assert "No frameworks" in result.output

    def test_list_authentication_error(self):
        client = _authed_client(
            list_frameworks=AsyncMock(side_effect=AuthenticationError("Token expired"))
        )
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_list_client_error(self):
        client = _authed_client(
            list_frameworks=AsyncMock(side_effect=PretorianClientError("Server error"))
        )
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 1
        assert "Server error" in result.output

    def test_list_long_title_truncated(self):
        long_fw = FrameworkSummary(
            id="fw-long",
            external_id="very-long-framework",
            title="A" * 65,
            version="1.0",
            tier="foundational",
            families_count=1,
            controls_count=1,
        )
        fw_list = FrameworkList(frameworks=[long_fw], total=1)
        client = _authed_client(list_frameworks=AsyncMock(return_value=fw_list))
        result = _run_with_mock_client(["frameworks", "list"], client)
        assert result.exit_code == 0


# ===========================================================================
# frameworks get
# ===========================================================================


class TestFrameworkGet:
    def test_get_rich_output(self):
        client = _authed_client(get_framework=AsyncMock(return_value=_FRAMEWORK_META))
        result = _run_with_mock_client(["frameworks", "get", "fedramp-moderate"], client)
        assert result.exit_code == 0
        assert "FedRAMP Moderate" in result.output

    def test_get_json_output(self):
        client = _authed_client(get_framework=AsyncMock(return_value=_FRAMEWORK_META))
        result = _run_with_mock_client(["--json", "frameworks", "get", "fedramp-moderate"], client)
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["external_id"] == "fedramp-moderate"

    def test_get_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(["frameworks", "get", "fedramp-moderate"], client)
        assert result.exit_code == 1

    def test_get_not_found(self):
        client = _authed_client(
            get_framework=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(["frameworks", "get", "nonexistent"], client)
        assert result.exit_code == 1
        assert "Couldn't find framework" in result.output

    def test_get_authentication_error(self):
        client = _authed_client(
            get_framework=AsyncMock(side_effect=AuthenticationError("Bad token"))
        )
        result = _run_with_mock_client(["frameworks", "get", "fedramp-moderate"], client)
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_get_client_error(self):
        client = _authed_client(
            get_framework=AsyncMock(side_effect=PretorianClientError("Upstream error"))
        )
        result = _run_with_mock_client(["frameworks", "get", "fedramp-moderate"], client)
        assert result.exit_code == 1
        assert "Upstream error" in result.output


# ===========================================================================
# frameworks families
# ===========================================================================


class TestFrameworkFamilies:
    def test_families_rich_output(self):
        client = _authed_client(
            list_control_families=AsyncMock(return_value=[_FAMILY_SUMMARY])
        )
        result = _run_with_mock_client(["frameworks", "families", "fedramp-moderate"], client)
        assert result.exit_code == 0
        assert "Access Control" in result.output

    def test_families_json_output(self):
        client = _authed_client(
            list_control_families=AsyncMock(return_value=[_FAMILY_SUMMARY])
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "families", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["id"] == "access-control"

    def test_families_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(["frameworks", "families", "fedramp-moderate"], client)
        assert result.exit_code == 1

    def test_families_empty(self):
        client = _authed_client(list_control_families=AsyncMock(return_value=[]))
        result = _run_with_mock_client(["frameworks", "families", "fedramp-moderate"], client)
        assert result.exit_code == 0
        assert "No control families" in result.output

    def test_families_not_found(self):
        client = _authed_client(
            list_control_families=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(["frameworks", "families", "bad-id"], client)
        assert result.exit_code == 1
        assert "Couldn't find framework" in result.output

    def test_families_authentication_error(self):
        client = _authed_client(
            list_control_families=AsyncMock(side_effect=AuthenticationError("Expired"))
        )
        result = _run_with_mock_client(["frameworks", "families", "fedramp-moderate"], client)
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_families_client_error(self):
        client = _authed_client(
            list_control_families=AsyncMock(side_effect=PretorianClientError("Oops"))
        )
        result = _run_with_mock_client(["frameworks", "families", "fedramp-moderate"], client)
        assert result.exit_code == 1


# ===========================================================================
# frameworks controls
# ===========================================================================


class TestFrameworkControls:
    def test_controls_rich_output(self):
        client = _authed_client(
            list_controls=AsyncMock(return_value=[_CONTROL_SUMMARY])
        )
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 0
        assert "Account Management" in result.output

    def test_controls_json_output(self):
        client = _authed_client(
            list_controls=AsyncMock(return_value=[_CONTROL_SUMMARY])
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "controls", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["id"] == "ac-02"

    def test_controls_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 1

    def test_controls_empty(self):
        client = _authed_client(list_controls=AsyncMock(return_value=[]))
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 0
        assert "No controls found" in result.output

    def test_controls_with_family_positional(self):
        client = _authed_client(
            list_controls=AsyncMock(return_value=[_CONTROL_SUMMARY])
        )
        result = _run_with_mock_client(
            ["frameworks", "controls", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 0
        client.list_controls.assert_awaited_once_with("fedramp-moderate", "access-control")

    def test_controls_with_family_option(self):
        client = _authed_client(
            list_controls=AsyncMock(return_value=[_CONTROL_SUMMARY])
        )
        result = _run_with_mock_client(
            ["frameworks", "controls", "fedramp-moderate", "--family", "access-control"], client
        )
        assert result.exit_code == 0
        client.list_controls.assert_awaited_once_with("fedramp-moderate", "access-control")

    def test_controls_with_limit(self):
        controls = [
            ControlSummary(id=f"ac-0{i}", title=f"Control {i}", family_id="access-control")
            for i in range(1, 6)
        ]
        client = _authed_client(list_controls=AsyncMock(return_value=controls))
        result = _run_with_mock_client(
            ["frameworks", "controls", "fedramp-moderate", "--limit", "3"], client
        )
        assert result.exit_code == 0
        assert "Showing 3 of 5" in result.output

    def test_controls_with_limit_json(self):
        controls = [
            ControlSummary(id=f"ac-0{i}", title=f"Control {i}", family_id="access-control")
            for i in range(1, 6)
        ]
        client = _authed_client(list_controls=AsyncMock(return_value=controls))
        result = _run_with_mock_client(
            ["--json", "frameworks", "controls", "fedramp-moderate", "--limit", "2"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_controls_not_found(self):
        client = _authed_client(
            list_controls=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(["frameworks", "controls", "bad-fw"], client)
        assert result.exit_code == 1
        assert "Couldn't find framework" in result.output

    def test_controls_authentication_error(self):
        client = _authed_client(
            list_controls=AsyncMock(side_effect=AuthenticationError("Expired"))
        )
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 1

    def test_controls_client_error(self):
        client = _authed_client(
            list_controls=AsyncMock(side_effect=PretorianClientError("Service unavailable"))
        )
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 1
        assert "Service unavailable" in result.output

    def test_controls_long_title_truncated(self):
        long_ctrl = ControlSummary(
            id="ac-02", title="A" * 65, family_id="access-control"
        )
        client = _authed_client(list_controls=AsyncMock(return_value=[long_ctrl]))
        result = _run_with_mock_client(["frameworks", "controls", "fedramp-moderate"], client)
        assert result.exit_code == 0


# ===========================================================================
# frameworks control (control_get)
# ===========================================================================


class TestControlGet:
    def test_get_rich_output(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "AC-02" in result.output or "ac-02" in result.output.lower()

    def test_get_json_output(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "ac-02"
        assert "references" in data

    def test_get_brief_skips_references(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02", "--brief"], client
        )
        assert result.exit_code == 0
        # references should not have been fetched
        client.get_control_references.assert_not_awaited()

    def test_get_brief_json_skips_references(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "control", "fedramp-moderate", "ac-02", "--brief"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "references" not in data
        client.get_control_references.assert_not_awaited()

    def test_get_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 1

    def test_get_not_found(self):
        client = _authed_client(
            get_control=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "bad-ctrl"], client
        )
        assert result.exit_code == 1
        assert "Couldn't find control" in result.output

    def test_get_authentication_error(self):
        client = _authed_client(
            get_control=AsyncMock(side_effect=AuthenticationError("Auth failed"))
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_get_client_error(self):
        client = _authed_client(
            get_control=AsyncMock(side_effect=PretorianClientError("Timeout"))
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 1
        assert "Timeout" in result.output

    def test_get_shows_ai_guidance(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        # ai_guidance present in _CONTROL_DETAIL
        assert "AI Guidance" in result.output or "Guidance" in result.output

    def test_get_shows_objectives_truncated(self):
        many_objectives = ControlReferences(
            control_id="ac-02",
            objectives=[f"Objective {i}" for i in range(8)],
        )
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=many_objectives),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "more" in result.output

    def test_get_shows_enhancements_count(self):
        client = _authed_client(
            get_control=AsyncMock(return_value=_CONTROL_DETAIL),
            get_control_references=AsyncMock(return_value=_CONTROL_REFS),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        # _CONTROL_DETAIL has controls=[...]
        assert "Enhancement" in result.output


# ===========================================================================
# frameworks documents
# ===========================================================================


class TestFrameworkDocuments:
    def test_documents_rich_output(self):
        client = _authed_client(
            get_document_requirements=AsyncMock(return_value=_DOC_REQUIREMENTS)
        )
        result = _run_with_mock_client(
            ["frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        assert "System Security Plan" in result.output

    def test_documents_json_output(self):
        client = _authed_client(
            get_document_requirements=AsyncMock(return_value=_DOC_REQUIREMENTS)
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["framework_id"] == "fedramp-moderate"
        assert data["total"] == 2

    def test_documents_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(
            ["frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 1

    def test_documents_not_found(self):
        client = _authed_client(
            get_document_requirements=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(["frameworks", "documents", "bad-fw"], client)
        assert result.exit_code == 1
        assert "Couldn't find document requirements" in result.output

    def test_documents_authentication_error(self):
        client = _authed_client(
            get_document_requirements=AsyncMock(side_effect=AuthenticationError("Expired"))
        )
        result = _run_with_mock_client(
            ["frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_documents_client_error(self):
        client = _authed_client(
            get_document_requirements=AsyncMock(side_effect=PretorianClientError("Bad gateway"))
        )
        result = _run_with_mock_client(
            ["frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 1

    def test_documents_many_implicit_truncated(self):
        many_implicit = [
            DocumentRequirement(
                id=f"doc-{i}",
                document_name=f"Policy Doc {i}",
                requirement_type="implicit",
                is_required=False,
            )
            for i in range(15)
        ]
        docs = DocumentRequirementList(
            framework_id="fedramp-moderate",
            framework_title="FedRAMP Moderate",
            explicit_documents=[],
            implicit_documents=many_implicit,
            total=15,
        )
        client = _authed_client(get_document_requirements=AsyncMock(return_value=docs))
        result = _run_with_mock_client(
            ["frameworks", "documents", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        assert "more" in result.output


# ===========================================================================
# frameworks family (family_get)
# ===========================================================================


class TestFamilyGet:
    def test_family_rich_output(self):
        client = _authed_client(
            get_control_family=AsyncMock(return_value=_FAMILY_DETAIL)
        )
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 0
        assert "Access Control" in result.output

    def test_family_json_output(self):
        client = _authed_client(
            get_control_family=AsyncMock(return_value=_FAMILY_DETAIL)
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["id"] == "access-control"

    def test_family_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 1

    def test_family_not_found(self):
        client = _authed_client(
            get_control_family=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "nonexistent"], client
        )
        assert result.exit_code == 1
        assert "Couldn't find family" in result.output

    def test_family_authentication_error(self):
        client = _authed_client(
            get_control_family=AsyncMock(side_effect=AuthenticationError("Expired"))
        )
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 1

    def test_family_client_error(self):
        client = _authed_client(
            get_control_family=AsyncMock(side_effect=PretorianClientError("Server error"))
        )
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 1

    def test_family_no_controls(self):
        empty_family = ControlFamilyDetail(
            **{"id": "empty-family", "title": "Empty Family", "class": "SP800-53", "controls": []}
        )
        client = _authed_client(
            get_control_family=AsyncMock(return_value=empty_family)
        )
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "empty-family"], client
        )
        assert result.exit_code == 0

    def test_family_control_long_title_truncated(self):
        long_ctrl = ControlInFamily(
            **{"id": "ac-02", "title": "B" * 65, "class": "SP800-53"}
        )
        family = ControlFamilyDetail(
            **{
                "id": "access-control",
                "title": "Access Control",
                "class": "SP800-53",
                "controls": [{"id": "ac-02", "title": "B" * 65, "class": "SP800-53"}],
            }
        )
        client = _authed_client(get_control_family=AsyncMock(return_value=family))
        result = _run_with_mock_client(
            ["frameworks", "family", "fedramp-moderate", "access-control"], client
        )
        assert result.exit_code == 0


# ===========================================================================
# frameworks metadata (framework_metadata)
# ===========================================================================


class TestFrameworkMetadata:
    def test_metadata_rich_output(self):
        client = _authed_client(
            get_controls_metadata=AsyncMock(return_value=_CONTROL_METADATA)
        )
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        assert "ac-02" in result.output or "Account Management" in result.output

    def test_metadata_json_output(self):
        client = _authed_client(
            get_controls_metadata=AsyncMock(return_value=_CONTROL_METADATA)
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "ac-02" in data

    def test_metadata_not_authenticated(self):
        client = _unauthed_client()
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 1

    def test_metadata_empty(self):
        client = _authed_client(get_controls_metadata=AsyncMock(return_value={}))
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 0
        assert "No control metadata" in result.output

    def test_metadata_not_found(self):
        client = _authed_client(
            get_controls_metadata=AsyncMock(side_effect=NotFoundError("not found"))
        )
        result = _run_with_mock_client(["frameworks", "metadata", "bad-fw"], client)
        assert result.exit_code == 1
        assert "Couldn't find framework" in result.output

    def test_metadata_authentication_error(self):
        client = _authed_client(
            get_controls_metadata=AsyncMock(side_effect=AuthenticationError("Bad key"))
        )
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 1

    def test_metadata_client_error(self):
        client = _authed_client(
            get_controls_metadata=AsyncMock(side_effect=PretorianClientError("Timeout"))
        )
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 1

    def test_metadata_long_title_truncated(self):
        long_meta = {
            "ac-02": ControlMetadata(title="C" * 65, family="access-control", type="system")
        }
        client = _authed_client(get_controls_metadata=AsyncMock(return_value=long_meta))
        result = _run_with_mock_client(
            ["frameworks", "metadata", "fedramp-moderate"], client
        )
        assert result.exit_code == 0


# ===========================================================================
# frameworks submit-artifact
# ===========================================================================

_VALID_ARTIFACT_DATA = {
    "framework_id": "fedramp-moderate",
    "control_id": "ac-02",
    "confidence": "high",
    "component": {
        "component_id": "my-app",
        "title": "My Application",
        "description": "Core web application.",
        "type": "software",
        "control_implementations": [
            {
                "control_id": "ac-02",
                "description": "Accounts are managed via IAM.",
                "implementation_status": "implemented",
                "responsible_roles": ["Security Team"],
                "evidence": [],
            }
        ],
    },
}


class TestSubmitArtifact:
    def test_submit_rich_output(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _authed_client(
            submit_artifact=AsyncMock(
                return_value={"artifact_id": "art-123", "url": "https://example.com/art-123"}
            )
        )
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 0
        assert "art-123" in result.output

    def test_submit_json_output(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _authed_client(
            submit_artifact=AsyncMock(return_value={"artifact_id": "art-456"})
        )
        result = _run_with_mock_client(
            ["--json", "frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["artifact_id"] == "art-456"

    def test_submit_not_authenticated(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _unauthed_client()
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 1

    def test_submit_invalid_json_file(self, tmp_path: Path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("this is not json {{{")

        client = _authed_client()
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(bad_file)], client
        )
        assert result.exit_code == 1
        assert "Invalid JSON" in result.output

    def test_submit_invalid_schema(self, tmp_path: Path):
        bad_schema = tmp_path / "schema.json"
        bad_schema.write_text(json.dumps({"framework_id": "fedramp-moderate"}))

        client = _authed_client()
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(bad_schema)], client
        )
        assert result.exit_code == 1
        assert "Failed to parse artifact" in result.output

    def test_submit_authentication_error(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _authed_client(
            submit_artifact=AsyncMock(side_effect=AuthenticationError("Token expired"))
        )
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 1
        assert "Authentication issue" in result.output

    def test_submit_client_error(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _authed_client(
            submit_artifact=AsyncMock(side_effect=PretorianClientError("Validation failed"))
        )
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 1
        assert "Validation failed" in result.output

    def test_submit_without_url(self, tmp_path: Path):
        artifact_file = tmp_path / "artifact.json"
        artifact_file.write_text(json.dumps(_VALID_ARTIFACT_DATA))

        client = _authed_client(
            submit_artifact=AsyncMock(return_value={"artifact_id": "art-789"})
        )
        result = _run_with_mock_client(
            ["frameworks", "submit-artifact", str(artifact_file)], client
        )
        assert result.exit_code == 0
        assert "art-789" in result.output


# ===========================================================================
# _render_ai_guidance (internal helper — exercised via control_get)
# ===========================================================================


class TestRenderAiGuidance:
    """The helper is only reachable through control_get in normal mode."""

    def _control_with_guidance(self, guidance: dict) -> ControlDetail:
        return ControlDetail(
            **{
                "id": "ac-02",
                "title": "Account Management",
                "class": "SP800-53",
                "ai_guidance": guidance,
            }
        )

    def test_renders_str_value(self):
        guidance = {"overview": "Manage accounts with least privilege."}
        ctrl = self._control_with_guidance(guidance)
        client = _authed_client(
            get_control=AsyncMock(return_value=ctrl),
            get_control_references=AsyncMock(return_value=ControlReferences(control_id="ac-02")),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "Manage accounts" in result.output

    def test_renders_list_value(self):
        guidance = {"steps": ["Step 1", "Step 2", "Step 3"]}
        ctrl = self._control_with_guidance(guidance)
        client = _authed_client(
            get_control=AsyncMock(return_value=ctrl),
            get_control_references=AsyncMock(return_value=ControlReferences(control_id="ac-02")),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "Step 1" in result.output

    def test_renders_dict_value(self):
        guidance = {"config": {"key": "value", "another": "item"}}
        ctrl = self._control_with_guidance(guidance)
        client = _authed_client(
            get_control=AsyncMock(return_value=ctrl),
            get_control_references=AsyncMock(return_value=ControlReferences(control_id="ac-02")),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "key" in result.output or "value" in result.output

    def test_renders_other_value_type(self):
        guidance = {"confidence_score": 0.95}
        ctrl = self._control_with_guidance(guidance)
        client = _authed_client(
            get_control=AsyncMock(return_value=ctrl),
            get_control_references=AsyncMock(return_value=ControlReferences(control_id="ac-02")),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        assert "0.95" in result.output

    def test_key_with_underscores_becomes_titled(self):
        guidance = {"my_key_name": "Some value"}
        ctrl = self._control_with_guidance(guidance)
        client = _authed_client(
            get_control=AsyncMock(return_value=ctrl),
            get_control_references=AsyncMock(return_value=ControlReferences(control_id="ac-02")),
        )
        result = _run_with_mock_client(
            ["frameworks", "control", "fedramp-moderate", "ac-02"], client
        )
        assert result.exit_code == 0
        # "my_key_name" -> "My Key Name" appears as panel title or inline heading
        assert "My Key Name" in result.output
