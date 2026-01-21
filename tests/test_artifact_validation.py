"""Tests for artifact validation logic."""

import pytest

from pretorin.mcp.server import _validate_artifact_data


class TestValidateArtifactDataRequired:
    """Tests for required field validation."""

    def test_empty_artifact_fails(self):
        """Test that empty artifact fails validation."""
        result = _validate_artifact_data({})
        assert result.valid is False
        assert "Missing required field: framework_id" in result.errors
        assert "Missing required field: control_id" in result.errors
        assert "Missing required field: component" in result.errors

    def test_missing_framework_id(self):
        """Test that missing framework_id is caught."""
        result = _validate_artifact_data({
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
            },
        })
        assert result.valid is False
        assert "Missing required field: framework_id" in result.errors

    def test_missing_control_id(self):
        """Test that missing control_id is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
            },
        })
        assert result.valid is False
        assert "Missing required field: control_id" in result.errors

    def test_missing_component(self):
        """Test that missing component is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
        })
        assert result.valid is False
        assert "Missing required field: component" in result.errors


class TestValidateArtifactDataComponent:
    """Tests for component field validation."""

    def test_missing_component_id(self):
        """Test that missing component_id is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "title": "Test",
                "description": "Test",
            },
        })
        assert result.valid is False
        assert "Missing required field: component.component_id" in result.errors

    def test_missing_component_title(self):
        """Test that missing component title is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "description": "Test",
            },
        })
        assert result.valid is False
        assert "Missing required field: component.title" in result.errors

    def test_missing_component_description(self):
        """Test that missing component description is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
            },
        })
        assert result.valid is False
        assert "Missing required field: component.description" in result.errors

    def test_invalid_component_type(self):
        """Test that invalid component type is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "type": "invalid-type",
            },
        })
        assert result.valid is False
        assert any("Invalid component type" in e for e in result.errors)

    def test_valid_component_types(self):
        """Test that all valid component types pass."""
        valid_types = ["software", "hardware", "service", "policy", "process"]
        for comp_type in valid_types:
            result = _validate_artifact_data({
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
                "component": {
                    "component_id": "test",
                    "title": "Test",
                    "description": "Test",
                    "type": comp_type,
                    "control_implementations": [
                        {
                            "control_id": "ac-2",
                            "description": "Test",
                            "implementation_status": "implemented",
                            "evidence": [{"description": "Test"}],
                        }
                    ],
                },
            })
            assert result.valid is True, f"Type {comp_type} should be valid"


class TestValidateArtifactDataImplementation:
    """Tests for control implementation validation."""

    def test_missing_implementation_control_id(self):
        """Test that missing implementation control_id is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "description": "Test",
                        "implementation_status": "implemented",
                    }
                ],
            },
        })
        assert result.valid is False
        assert any("Missing control_id" in e for e in result.errors)

    def test_missing_implementation_description(self):
        """Test that missing implementation description is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "implementation_status": "implemented",
                    }
                ],
            },
        })
        assert result.valid is False
        assert any("Missing description" in e for e in result.errors)

    def test_missing_implementation_status(self):
        """Test that missing implementation_status is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                    }
                ],
            },
        })
        assert result.valid is False
        assert any("Missing implementation_status" in e for e in result.errors)

    def test_invalid_implementation_status(self):
        """Test that invalid implementation_status is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                        "implementation_status": "invalid-status",
                    }
                ],
            },
        })
        assert result.valid is False
        assert any("Invalid status" in e for e in result.errors)

    def test_valid_implementation_statuses(self):
        """Test that all valid implementation statuses pass."""
        valid_statuses = ["implemented", "partial", "planned", "not-applicable"]
        for status in valid_statuses:
            result = _validate_artifact_data({
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
                "component": {
                    "component_id": "test",
                    "title": "Test",
                    "description": "Test",
                    "control_implementations": [
                        {
                            "control_id": "ac-2",
                            "description": "Test",
                            "implementation_status": status,
                            "evidence": [{"description": "Test"}],
                        }
                    ],
                },
            })
            assert result.valid is True, f"Status {status} should be valid"


class TestValidateArtifactDataEvidence:
    """Tests for evidence validation."""

    def test_missing_evidence_description(self):
        """Test that missing evidence description is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                        "implementation_status": "implemented",
                        "evidence": [
                            {"file_path": "test.py"}  # missing description
                        ],
                    }
                ],
            },
        })
        assert result.valid is False
        assert any("Evidence" in e and "Missing description" in e for e in result.errors)

    def test_valid_evidence(self):
        """Test that valid evidence passes."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                        "implementation_status": "implemented",
                        "evidence": [
                            {
                                "description": "User CRUD operations",
                                "file_path": "src/users.py",
                                "line_numbers": "10-25",
                            }
                        ],
                    }
                ],
            },
        })
        assert result.valid is True


class TestValidateArtifactDataConfidence:
    """Tests for confidence level validation."""

    def test_invalid_confidence(self):
        """Test that invalid confidence is caught."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
            },
            "confidence": "super-high",
        })
        assert result.valid is False
        assert any("Invalid confidence" in e for e in result.errors)

    def test_valid_confidence_levels(self):
        """Test that all valid confidence levels pass."""
        valid_levels = ["high", "medium", "low"]
        for level in valid_levels:
            result = _validate_artifact_data({
                "framework_id": "fedramp-moderate",
                "control_id": "ac-2",
                "component": {
                    "component_id": "test",
                    "title": "Test",
                    "description": "Test",
                    "control_implementations": [
                        {
                            "control_id": "ac-2",
                            "description": "Test",
                            "implementation_status": "implemented",
                            "evidence": [{"description": "Test"}],
                        }
                    ],
                },
                "confidence": level,
            })
            assert result.valid is True, f"Confidence {level} should be valid"

    def test_default_confidence(self):
        """Test that missing confidence uses default."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                        "implementation_status": "implemented",
                        "evidence": [{"description": "Test"}],
                    }
                ],
            },
        })
        assert result.valid is True


class TestValidateArtifactDataWarnings:
    """Tests for validation warnings."""

    def test_no_implementations_warning(self):
        """Test that missing implementations generates warning."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [],
            },
        })
        assert "No control implementations provided" in result.warnings

    def test_no_evidence_warning(self):
        """Test that missing evidence generates warning."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "Test",
                        "implementation_status": "implemented",
                        "evidence": [],
                    }
                ],
            },
        })
        assert any("No evidence provided" in w for w in result.warnings)


class TestValidateArtifactDataFullArtifact:
    """Tests for complete artifact validation."""

    def test_valid_complete_artifact(self):
        """Test that a complete valid artifact passes."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "my-app",
                "title": "My Application",
                "description": "A web application for user management",
                "type": "software",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "User accounts are managed through an admin interface with role-based access control.",
                        "implementation_status": "implemented",
                        "responsible_roles": ["System Administrator", "Security Team"],
                        "evidence": [
                            {
                                "description": "User CRUD operations with role assignment",
                                "file_path": "src/auth/users.py",
                                "line_numbers": "45-120",
                                "code_snippet": "def create_user(username, role): ...",
                            },
                            {
                                "description": "Account deactivation workflow",
                                "file_path": "src/auth/lifecycle.py",
                                "line_numbers": "30-55",
                            },
                        ],
                        "remarks": "MFA is handled by external identity provider",
                    }
                ],
            },
            "confidence": "high",
        })
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_multiple_implementations(self):
        """Test artifact with multiple control implementations."""
        result = _validate_artifact_data({
            "framework_id": "fedramp-moderate",
            "control_id": "ac-2",
            "component": {
                "component_id": "test",
                "title": "Test",
                "description": "Test",
                "control_implementations": [
                    {
                        "control_id": "ac-2",
                        "description": "First implementation",
                        "implementation_status": "implemented",
                        "evidence": [{"description": "Evidence 1"}],
                    },
                    {
                        "control_id": "ac-2",
                        "description": "Second implementation",
                        "implementation_status": "partial",
                        "evidence": [{"description": "Evidence 2"}],
                    },
                ],
            },
        })
        assert result.valid is True
