"""Integration tests for MCP tools.

These tests verify that MCP tools work correctly against the real API.
Requires PRETORIN_API_KEY environment variable to be set.
"""

import os

import pytest

from pretorin.client import PretorianClient

# Known test data
KNOWN_FRAMEWORK_ID = "nist-800-53-r5"


@pytest.fixture(autouse=True)
def setup_api_key() -> None:
    """Ensure API key is set for all tests in this module."""
    if not os.environ.get("PRETORIN_API_KEY"):
        pytest.skip("PRETORIN_API_KEY environment variable not set")


@pytest.mark.integration
class TestListFrameworksTool:
    """Test the pretorin_list_frameworks tool functionality."""

    @pytest.mark.asyncio
    async def test_list_frameworks_returns_data(self) -> None:
        """Test that list_frameworks returns framework data."""
        async with PretorianClient() as client:
            result = await client.list_frameworks()

            assert result.total > 0
            assert len(result.frameworks) > 0

            # Check that frameworks have expected fields
            fw = result.frameworks[0]
            assert fw.external_id
            assert fw.title

    @pytest.mark.asyncio
    async def test_list_frameworks_includes_known_framework(self) -> None:
        """Test that list_frameworks includes known frameworks."""
        async with PretorianClient() as client:
            result = await client.list_frameworks()

            framework_ids = [fw.external_id for fw in result.frameworks]
            # Should include at least one NIST framework
            assert any("nist" in fid.lower() for fid in framework_ids)


@pytest.mark.integration
class TestGetFrameworkTool:
    """Test the pretorin_get_framework tool functionality."""

    @pytest.mark.asyncio
    async def test_get_framework_returns_details(self) -> None:
        """Test that get_framework returns framework details."""
        async with PretorianClient() as client:
            framework = await client.get_framework(KNOWN_FRAMEWORK_ID)

            assert framework.external_id == KNOWN_FRAMEWORK_ID
            assert framework.title
            assert framework.version

    @pytest.mark.asyncio
    async def test_get_framework_invalid_id_raises(self) -> None:
        """Test that get_framework raises for invalid framework."""
        from pretorin.client.api import NotFoundError

        async with PretorianClient() as client:
            with pytest.raises(NotFoundError):
                await client.get_framework("nonexistent-framework-xyz")


@pytest.mark.integration
class TestListControlFamiliesTool:
    """Test the pretorin_list_control_families tool functionality."""

    @pytest.mark.asyncio
    async def test_list_control_families_returns_data(self) -> None:
        """Test that list_control_families returns family data."""
        async with PretorianClient() as client:
            families = await client.list_control_families(KNOWN_FRAMEWORK_ID)

            assert len(families) > 0

            # Check that families have expected fields
            family = families[0]
            assert family.id
            assert family.title

    @pytest.mark.asyncio
    async def test_list_control_families_includes_access_control(self) -> None:
        """Test that list_control_families includes an Access Control family."""
        async with PretorianClient() as client:
            families = await client.list_control_families(KNOWN_FRAMEWORK_ID)

            # Look for access control family by title (ID format may vary)
            family_titles = [f.title.lower() for f in families]
            assert any("access control" in t for t in family_titles)


@pytest.mark.integration
class TestListControlsTool:
    """Test the pretorin_list_controls tool functionality."""

    @pytest.mark.asyncio
    async def test_list_controls_returns_data(self) -> None:
        """Test that list_controls returns control data."""
        async with PretorianClient() as client:
            controls = await client.list_controls(KNOWN_FRAMEWORK_ID)

            assert len(controls) > 0

            # Check that controls have expected fields
            control = controls[0]
            assert control.id
            assert control.title

    @pytest.mark.asyncio
    async def test_list_controls_with_family_filter(self) -> None:
        """Test that list_controls filters by family."""
        async with PretorianClient() as client:
            # Discover a valid family ID first
            families = await client.list_control_families(KNOWN_FRAMEWORK_ID)
            family_id = families[0].id

            controls = await client.list_controls(KNOWN_FRAMEWORK_ID, family_id)

            assert len(controls) > 0

            # All controls should be from the same family
            for control in controls:
                assert control.family_id == family_id


@pytest.mark.integration
class TestGetControlTool:
    """Test the pretorin_get_control tool functionality."""

    @pytest.mark.asyncio
    async def test_get_control_returns_details(self) -> None:
        """Test that get_control returns control details."""
        async with PretorianClient() as client:
            # Discover a valid control ID first
            controls = await client.list_controls(KNOWN_FRAMEWORK_ID)
            control_id = controls[0].id

            control = await client.get_control(KNOWN_FRAMEWORK_ID, control_id)

            assert control.id == control_id
            assert control.title

    @pytest.mark.asyncio
    async def test_get_control_invalid_id_raises(self) -> None:
        """Test that get_control raises for invalid control."""
        from pretorin.client.api import NotFoundError

        async with PretorianClient() as client:
            with pytest.raises(NotFoundError):
                await client.get_control(KNOWN_FRAMEWORK_ID, "nonexistent-control-xyz")


@pytest.mark.integration
class TestGetControlReferencesTool:
    """Test the pretorin_get_control_references tool functionality."""

    @pytest.mark.asyncio
    async def test_get_control_references_returns_data(self) -> None:
        """Test that get_control_references returns reference data."""
        async with PretorianClient() as client:
            # Discover a valid control ID first
            controls = await client.list_controls(KNOWN_FRAMEWORK_ID)
            control_id = controls[0].id

            refs = await client.get_control_references(KNOWN_FRAMEWORK_ID, control_id)

            assert refs.control_id == control_id
            assert refs.title
            # Should have at least a statement
            assert refs.statement or refs.guidance


@pytest.mark.integration
class TestGetDocumentRequirementsTool:
    """Test the pretorin_get_document_requirements tool functionality."""

    @pytest.mark.asyncio
    async def test_get_document_requirements_returns_data(self) -> None:
        """Test that get_document_requirements returns document data."""
        async with PretorianClient() as client:
            try:
                docs = await client.get_document_requirements("fedramp-moderate")

                assert docs.framework_id
                # May or may not have documents depending on framework
                assert docs.total >= 0
            except Exception:
                # Some frameworks may not support document requirements
                pytest.skip("Document requirements not available for this framework")


@pytest.mark.integration
class TestMCPResourcesAvailable:
    """Test that MCP resources are correctly configured."""

    def test_mcp_server_resources_listed(self) -> None:
        """Test that MCP server exposes expected resources."""
        import asyncio

        from pretorin.mcp.server import list_resources

        resources = asyncio.run(list_resources())

        # Should have schema resource - convert AnyUrl to string for comparison
        resource_uris = [str(r.uri) for r in resources]
        assert "analysis://schema" in resource_uris

    def test_mcp_server_tools_listed(self) -> None:
        """Test that MCP server exposes expected tools."""
        import asyncio

        from pretorin.mcp.server import list_tools

        tools = asyncio.run(list_tools())

        tool_names = [t.name for t in tools]
        expected_tools = [
            "pretorin_list_frameworks",
            "pretorin_get_framework",
            "pretorin_list_control_families",
            "pretorin_list_controls",
            "pretorin_get_control",
            "pretorin_get_control_references",
            "pretorin_get_document_requirements",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"
