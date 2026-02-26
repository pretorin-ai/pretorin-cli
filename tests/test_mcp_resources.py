"""Tests for MCP resources."""

import pytest

from pretorin.mcp.server import list_resources, read_resource


class TestListResources:
    """Tests for MCP resource listing."""

    @pytest.mark.asyncio
    async def test_list_resources_returns_list(self):
        """Test that list_resources returns a list."""
        resources = await list_resources()
        assert isinstance(resources, list)

    @pytest.mark.asyncio
    async def test_list_resources_contains_schema(self):
        """Test that schema resource is listed."""
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        assert "analysis://schema" in uris

    @pytest.mark.asyncio
    async def test_list_resources_contains_framework_guides(self):
        """Test that framework guide resources are listed."""
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        assert "analysis://guide/fedramp-moderate" in uris
        assert "analysis://guide/nist-800-53-r5" in uris
        assert "analysis://guide/nist-800-171-r3" in uris

    @pytest.mark.asyncio
    async def test_list_resources_contains_control_prompts(self):
        """Test that control prompt resources are listed."""
        resources = await list_resources()
        uris = [str(r.uri) for r in resources]
        expected_controls = ["ac-02", "au-02", "ia-02", "sc-07", "cm-02"]
        for control in expected_controls:
            assert f"analysis://control/{control}" in uris

    @pytest.mark.asyncio
    async def test_resources_have_names(self):
        """Test that all resources have names."""
        resources = await list_resources()
        for resource in resources:
            assert resource.name is not None
            assert len(resource.name) > 0

    @pytest.mark.asyncio
    async def test_resources_have_descriptions(self):
        """Test that all resources have descriptions."""
        resources = await list_resources()
        for resource in resources:
            assert resource.description is not None
            assert len(resource.description) > 0

    @pytest.mark.asyncio
    async def test_resources_have_mime_types(self):
        """Test that all resources have MIME types."""
        resources = await list_resources()
        for resource in resources:
            assert resource.mimeType == "text/markdown"


class TestReadResourceSchema:
    """Tests for reading the schema resource."""

    @pytest.mark.asyncio
    async def test_read_schema_resource(self):
        """Test reading the schema resource."""
        content = await read_resource("analysis://schema")
        assert isinstance(content, str)
        assert len(content) > 0

    @pytest.mark.asyncio
    async def test_schema_contains_artifact_structure(self):
        """Test that schema describes artifact structure."""
        content = await read_resource("analysis://schema")
        assert "framework_id" in content
        assert "control_id" in content
        assert "component" in content
        assert "confidence" in content

    @pytest.mark.asyncio
    async def test_schema_contains_example(self):
        """Test that schema contains an example."""
        content = await read_resource("analysis://schema")
        assert "json" in content.lower()
        assert "example" in content.lower() or "{" in content


class TestReadResourceGuide:
    """Tests for reading framework guide resources."""

    @pytest.mark.asyncio
    async def test_read_fedramp_guide(self):
        """Test reading FedRAMP guide."""
        content = await read_resource("analysis://guide/fedramp-moderate")
        assert isinstance(content, str)
        assert "FedRAMP" in content

    @pytest.mark.asyncio
    async def test_read_nist_800_53_guide(self):
        """Test reading NIST 800-53 guide."""
        content = await read_resource("analysis://guide/nist-800-53-r5")
        assert isinstance(content, str)
        assert "NIST 800-53" in content

    @pytest.mark.asyncio
    async def test_read_nist_800_171_guide(self):
        """Test reading NIST 800-171 guide."""
        content = await read_resource("analysis://guide/nist-800-171-r3")
        assert isinstance(content, str)
        assert "NIST 800-171" in content

    @pytest.mark.asyncio
    async def test_unknown_framework_raises_error(self):
        """Test that unknown framework raises error."""
        with pytest.raises(ValueError) as exc_info:
            await read_resource("analysis://guide/unknown-framework")
        assert "No analysis guide available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_missing_framework_id_raises_error(self):
        """Test that missing framework ID raises error."""
        with pytest.raises(ValueError) as exc_info:
            await read_resource("analysis://guide/")
        assert "Framework ID required" in str(exc_info.value)


class TestReadResourceControl:
    """Tests for reading control analysis resources."""

    @pytest.mark.asyncio
    async def test_read_ac2_control(self):
        """Test reading AC-02 control prompt."""
        content = await read_resource("analysis://control/ac-02")
        assert isinstance(content, str)
        assert "AC-02" in content
        assert "Account Management" in content

    @pytest.mark.asyncio
    async def test_read_ac2_control_unpadded(self):
        """Test reading AC-2 (unpadded) normalizes to AC-02."""
        content = await read_resource("analysis://control/ac-2")
        assert isinstance(content, str)
        assert "AC-02" in content
        assert "Account Management" in content

    @pytest.mark.asyncio
    async def test_read_au2_control(self):
        """Test reading AU-02 control prompt."""
        content = await read_resource("analysis://control/au-02")
        assert isinstance(content, str)
        assert "AU-02" in content
        assert "Audit" in content

    @pytest.mark.asyncio
    async def test_read_ia2_control(self):
        """Test reading IA-02 control prompt."""
        content = await read_resource("analysis://control/ia-02")
        assert isinstance(content, str)
        assert "IA-02" in content
        assert "Authentication" in content

    @pytest.mark.asyncio
    async def test_read_sc7_control(self):
        """Test reading SC-07 control prompt."""
        content = await read_resource("analysis://control/sc-07")
        assert isinstance(content, str)
        assert "SC-07" in content
        assert "Boundary" in content

    @pytest.mark.asyncio
    async def test_read_cm2_control(self):
        """Test reading CM-02 control prompt."""
        content = await read_resource("analysis://control/cm-02")
        assert isinstance(content, str)
        assert "CM-02" in content
        assert "Configuration" in content

    @pytest.mark.asyncio
    async def test_read_control_with_framework(self):
        """Test reading control with framework prefix."""
        content = await read_resource("analysis://control/fedramp-moderate/ac-02")
        assert isinstance(content, str)
        assert "AC-02" in content
        assert "fedramp-moderate" in content

    @pytest.mark.asyncio
    async def test_unknown_control_returns_generic(self):
        """Test that unknown control returns generic guidance."""
        content = await read_resource("analysis://control/unknown-99")
        assert isinstance(content, str)
        assert "UNKNOWN-99" in content
        assert "No specific analysis guidance" in content

    @pytest.mark.asyncio
    async def test_missing_control_id_raises_error(self):
        """Test that missing control ID raises error."""
        with pytest.raises(ValueError) as exc_info:
            await read_resource("analysis://control/")
        assert "Control ID required" in str(exc_info.value)


class TestReadResourceErrors:
    """Tests for error handling in resource reading."""

    @pytest.mark.asyncio
    async def test_unknown_scheme_raises_error(self):
        """Test that unknown scheme raises error."""
        with pytest.raises(ValueError) as exc_info:
            await read_resource("unknown://schema")
        assert "Unknown resource scheme" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_unknown_resource_type_raises_error(self):
        """Test that unknown resource type raises error."""
        with pytest.raises(ValueError) as exc_info:
            await read_resource("analysis://unknown-type")
        assert "Unknown resource type" in str(exc_info.value)


class TestResourceContentQuality:
    """Tests for the quality of resource content."""

    @pytest.mark.asyncio
    async def test_control_prompts_have_what_to_look_for(self):
        """Test that control prompts include what to look for."""
        controls = ["ac-02", "au-02", "ia-02", "sc-07", "cm-02"]
        for control in controls:
            content = await read_resource(f"analysis://control/{control}")
            assert "What to Look For" in content or "look for" in content.lower()

    @pytest.mark.asyncio
    async def test_control_prompts_have_evidence_examples(self):
        """Test that control prompts include evidence examples."""
        controls = ["ac-02", "au-02", "ia-02", "sc-07", "cm-02"]
        for control in controls:
            content = await read_resource(f"analysis://control/{control}")
            assert "Evidence" in content

    @pytest.mark.asyncio
    async def test_control_prompts_reference_schema(self):
        """Test that control prompts reference the schema resource."""
        controls = ["ac-02", "au-02", "ia-02", "sc-07", "cm-02"]
        for control in controls:
            content = await read_resource(f"analysis://control/{control}")
            assert "analysis://schema" in content

    @pytest.mark.asyncio
    async def test_guides_have_control_families(self):
        """Test that guides discuss control families."""
        guides = ["fedramp-moderate", "nist-800-53-r5", "nist-800-171-r3"]
        for guide in guides:
            content = await read_resource(f"analysis://guide/{guide}")
            # Should mention at least some control families
            families = ["Access Control", "Audit", "Configuration"]
            mentioned = sum(1 for f in families if f in content)
            assert mentioned >= 2, f"Guide {guide} should mention control families"
