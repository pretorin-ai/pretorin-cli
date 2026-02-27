"""Integration tests for CLI commands.

These tests verify that CLI commands work correctly against the real API.
Requires PRETORIN_API_KEY environment variable to be set.
"""

import asyncio
import json
import os

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app
from pretorin.cli.output import set_json_mode
from pretorin.client import PretorianClient

runner = CliRunner()

# Known test data
KNOWN_FRAMEWORK_ID = "nist-800-53-r5"


def _discover_family_and_control() -> tuple[str, str]:
    """Discover a valid family ID and control ID from the API."""

    async def _fetch() -> tuple[str, str]:
        async with PretorianClient() as client:
            families = await client.list_control_families(KNOWN_FRAMEWORK_ID)
            family_id = families[0].id
            controls = await client.list_controls(KNOWN_FRAMEWORK_ID, family_id)
            control_id = controls[0].id
            return family_id, control_id

    return asyncio.run(_fetch())


@pytest.fixture(autouse=True)
def setup_api_key() -> None:
    """Ensure API key is set for all tests in this module."""
    if not os.environ.get("PRETORIN_API_KEY"):
        pytest.skip("PRETORIN_API_KEY environment variable not set")


@pytest.fixture(autouse=True)
def reset_json_mode() -> None:
    """Reset JSON mode after each test."""
    yield  # type: ignore[misc]
    set_json_mode(False)


@pytest.fixture(scope="module")
def discovered_ids() -> tuple[str, str]:
    """Discover valid family and control IDs from the API."""
    if not os.environ.get("PRETORIN_API_KEY"):
        pytest.skip("PRETORIN_API_KEY environment variable not set")
    return _discover_family_and_control()


@pytest.mark.integration
class TestAuthCommands:
    """Test authentication-related CLI commands."""

    def test_whoami_shows_authenticated(self) -> None:
        """Test that whoami shows authenticated status."""
        result = runner.invoke(app, ["whoami"])
        # Should not fail if authenticated
        assert result.exit_code == 0 or "Not logged in" in result.output

    def test_whoami_json(self) -> None:
        """Test whoami in JSON mode."""
        result = runner.invoke(app, ["--json", "whoami"])
        if result.exit_code == 0:
            data = json.loads(result.output)
            assert "authenticated" in data


@pytest.mark.integration
class TestFrameworkListCommand:
    """Test the frameworks list command."""

    def test_list_frameworks(self) -> None:
        """Test listing all frameworks."""
        result = runner.invoke(app, ["frameworks", "list"])

        assert result.exit_code == 0
        assert "Compliance Frameworks" in result.output or "frameworks" in result.output.lower()
        # Should contain at least one known framework
        assert "nist" in result.output.lower() or "NIST" in result.output

    def test_list_frameworks_json(self) -> None:
        """Test listing frameworks in JSON mode."""
        result = runner.invoke(app, ["--json", "frameworks", "list"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "frameworks" in data
        assert "total" in data


@pytest.mark.integration
class TestFrameworkGetCommand:
    """Test the frameworks get command."""

    def test_get_known_framework(self) -> None:
        """Test getting a known framework."""
        result = runner.invoke(app, ["frameworks", "get", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        assert "800-53" in result.output or "NIST" in result.output

    def test_get_unknown_framework_fails(self) -> None:
        """Test that getting an unknown framework returns an error."""
        result = runner.invoke(app, ["frameworks", "get", "nonexistent-framework-xyz"])

        assert result.exit_code != 0
        assert "couldn't find" in result.output.lower() or "not found" in result.output.lower()

    def test_get_framework_json(self) -> None:
        """Test getting a framework in JSON mode."""
        result = runner.invoke(app, ["--json", "frameworks", "get", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "title" in data


@pytest.mark.integration
class TestFrameworkFamiliesCommand:
    """Test the frameworks families command."""

    def test_list_families(self) -> None:
        """Test listing control families for a framework."""
        result = runner.invoke(app, ["frameworks", "families", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        # Should show some family content
        assert "Control Families" in result.output or "control" in result.output.lower()


@pytest.mark.integration
class TestFrameworkControlsCommand:
    """Test the frameworks controls command."""

    def test_list_controls(self) -> None:
        """Test listing controls for a framework (default shows all)."""
        result = runner.invoke(app, ["frameworks", "controls", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        # Should show some controls
        assert "control" in result.output.lower()

    def test_list_controls_with_family_option(self, discovered_ids: tuple[str, str]) -> None:
        """Test listing controls filtered by family using --family option."""
        family_id, _ = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "controls", KNOWN_FRAMEWORK_ID, "--family", family_id],
        )

        assert result.exit_code == 0
        assert "control" in result.output.lower()

    def test_list_controls_with_family_positional(self, discovered_ids: tuple[str, str]) -> None:
        """Test listing controls filtered by family using positional argument."""
        family_id, _ = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "controls", KNOWN_FRAMEWORK_ID, family_id],
        )

        assert result.exit_code == 0
        assert "control" in result.output.lower()

    def test_list_controls_with_limit(self) -> None:
        """Test listing controls with a limit."""
        result = runner.invoke(
            app,
            ["frameworks", "controls", KNOWN_FRAMEWORK_ID, "--limit", "5"],
        )

        assert result.exit_code == 0


@pytest.mark.integration
class TestControlGetCommand:
    """Test the frameworks control command."""

    def test_get_control(self, discovered_ids: tuple[str, str]) -> None:
        """Test getting a specific control (references shown by default)."""
        _, control_id = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, control_id],
        )

        assert result.exit_code == 0
        assert "Control" in result.output

    def test_get_control_brief(self, discovered_ids: tuple[str, str]) -> None:
        """Test getting a control with --brief (skip references)."""
        _, control_id = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, control_id, "--brief"],
        )

        assert result.exit_code == 0
        assert "Control" in result.output

    def test_get_control_with_references_deprecated(self, discovered_ids: tuple[str, str]) -> None:
        """Test that --references still works (deprecated, hidden)."""
        _, control_id = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, control_id, "--references"],
        )

        assert result.exit_code == 0

    def test_get_unknown_control_fails(self) -> None:
        """Test that getting an unknown control returns an error."""
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, "nonexistent-control-xyz"],
        )

        assert result.exit_code != 0
        assert "couldn't find" in result.output.lower() or "not found" in result.output.lower()

    def test_get_control_json(self, discovered_ids: tuple[str, str]) -> None:
        """Test getting a control in JSON mode."""
        _, control_id = discovered_ids
        result = runner.invoke(
            app,
            ["--json", "frameworks", "control", KNOWN_FRAMEWORK_ID, control_id],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "id" in data
        assert "title" in data


@pytest.mark.integration
class TestDocumentsCommand:
    """Test the frameworks documents command."""

    def test_get_documents(self) -> None:
        """Test getting document requirements for a framework."""
        result = runner.invoke(app, ["frameworks", "documents", "fedramp-moderate"])

        # This may succeed or fail depending on framework availability
        # but should not crash
        assert result.exit_code in (0, 1)


@pytest.mark.integration
class TestFamilyCommand:
    """Test the frameworks family command."""

    def test_get_family(self, discovered_ids: tuple[str, str]) -> None:
        """Test getting a specific control family."""
        family_id, _ = discovered_ids
        result = runner.invoke(
            app,
            ["frameworks", "family", KNOWN_FRAMEWORK_ID, family_id],
        )

        assert result.exit_code == 0
        assert "Family" in result.output or family_id in result.output.lower()

    def test_get_family_json(self, discovered_ids: tuple[str, str]) -> None:
        """Test getting a family in JSON mode."""
        family_id, _ = discovered_ids
        result = runner.invoke(
            app,
            ["--json", "frameworks", "family", KNOWN_FRAMEWORK_ID, family_id],
        )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "title" in data


@pytest.mark.integration
class TestMetadataCommand:
    """Test the frameworks metadata command.

    Note: The /controls/metadata endpoint may not be available on all
    platform deployments. Tests skip gracefully when the endpoint
    returns an error.
    """

    def test_get_metadata(self) -> None:
        """Test getting control metadata for a framework."""
        result = runner.invoke(
            app,
            ["frameworks", "metadata", KNOWN_FRAMEWORK_ID],
        )

        if result.exit_code != 0:
            pytest.skip("metadata endpoint not available on this platform instance")
        assert "metadata" in result.output.lower() or "control" in result.output.lower()

    def test_get_metadata_json(self) -> None:
        """Test getting metadata in JSON mode."""
        result = runner.invoke(
            app,
            ["--json", "frameworks", "metadata", KNOWN_FRAMEWORK_ID],
        )

        if result.exit_code != 0:
            pytest.skip("metadata endpoint not available on this platform instance")
        data = json.loads(result.output)
        assert isinstance(data, dict)
        assert len(data) > 0


@pytest.mark.integration
class TestJsonFlag:
    """Test that the --json flag produces valid JSON across commands."""

    def test_bare_json(self) -> None:
        """Test bare pretorin --json outputs version JSON."""
        result = runner.invoke(app, ["--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data


@pytest.mark.integration
class TestVersionCommand:
    """Test the version command."""

    def test_version(self) -> None:
        """Test that version command works."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should show version number
        assert "0." in result.output or "pretorin" in result.output.lower()
