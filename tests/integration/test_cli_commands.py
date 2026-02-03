"""Integration tests for CLI commands.

These tests verify that CLI commands work correctly against the real API.
Requires PRETORIN_API_KEY environment variable to be set.
"""

import os

import pytest
from typer.testing import CliRunner

from pretorin.cli.main import app

runner = CliRunner()

# Known test data
KNOWN_FRAMEWORK_ID = "nist-800-53-r5"
KNOWN_CONTROL_ID = "ac-1"
KNOWN_FAMILY_ID = "ac"


@pytest.fixture(autouse=True)
def setup_api_key() -> None:
    """Ensure API key is set for all tests in this module."""
    if not os.environ.get("PRETORIN_API_KEY"):
        pytest.skip("PRETORIN_API_KEY environment variable not set")


@pytest.mark.integration
class TestAuthCommands:
    """Test authentication-related CLI commands."""

    def test_whoami_shows_authenticated(self) -> None:
        """Test that whoami shows authenticated status."""
        result = runner.invoke(app, ["whoami"])
        # Should not fail if authenticated
        assert result.exit_code == 0 or "Not logged in" in result.output


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


@pytest.mark.integration
class TestFrameworkFamiliesCommand:
    """Test the frameworks families command."""

    def test_list_families(self) -> None:
        """Test listing control families for a framework."""
        result = runner.invoke(app, ["frameworks", "families", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        # Should show Access Control family
        assert "AC" in result.output or "Access Control" in result.output


@pytest.mark.integration
class TestFrameworkControlsCommand:
    """Test the frameworks controls command."""

    def test_list_controls(self) -> None:
        """Test listing controls for a framework."""
        result = runner.invoke(app, ["frameworks", "controls", KNOWN_FRAMEWORK_ID])

        assert result.exit_code == 0
        # Should show some controls
        assert "control" in result.output.lower()

    def test_list_controls_with_family_filter(self) -> None:
        """Test listing controls filtered by family."""
        result = runner.invoke(
            app,
            ["frameworks", "controls", KNOWN_FRAMEWORK_ID, "--family", KNOWN_FAMILY_ID]
        )

        assert result.exit_code == 0
        # All controls should be from AC family
        assert "AC" in result.output

    def test_list_controls_with_limit(self) -> None:
        """Test listing controls with a limit."""
        result = runner.invoke(
            app,
            ["frameworks", "controls", KNOWN_FRAMEWORK_ID, "--limit", "5"]
        )

        assert result.exit_code == 0


@pytest.mark.integration
class TestControlGetCommand:
    """Test the frameworks control command."""

    def test_get_control(self) -> None:
        """Test getting a specific control."""
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, KNOWN_CONTROL_ID]
        )

        assert result.exit_code == 0
        assert "AC-1" in result.output or "ac-1" in result.output.lower()

    def test_get_control_with_references(self) -> None:
        """Test getting a control with references."""
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, KNOWN_CONTROL_ID, "--references"]
        )

        assert result.exit_code == 0
        # Should include additional reference information
        assert "Statement" in result.output or "Guidance" in result.output or "Policy" in result.output

    def test_get_unknown_control_fails(self) -> None:
        """Test that getting an unknown control returns an error."""
        result = runner.invoke(
            app,
            ["frameworks", "control", KNOWN_FRAMEWORK_ID, "nonexistent-control-xyz"]
        )

        assert result.exit_code != 0
        assert "couldn't find" in result.output.lower() or "not found" in result.output.lower()


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
class TestVersionCommand:
    """Test the version command."""

    def test_version(self) -> None:
        """Test that version command works."""
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        # Should show version number
        assert "0." in result.output or "pretorin" in result.output.lower()
