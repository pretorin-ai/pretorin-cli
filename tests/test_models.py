"""Tests for Pydantic models, especially compliance artifact models."""

import pytest
from pydantic import ValidationError

from pretorin.client.models import (
    ArtifactValidationResult,
    ComplianceArtifact,
    ComponentDefinition,
    Evidence,
    ImplementationStatement,
)


class TestEvidenceModel:
    """Tests for the Evidence model."""

    def test_evidence_minimal(self):
        """Test Evidence with only required fields."""
        evidence = Evidence(description="Test evidence")
        assert evidence.description == "Test evidence"
        assert evidence.file_path is None
        assert evidence.line_numbers is None
        assert evidence.code_snippet is None

    def test_evidence_full(self):
        """Test Evidence with all fields."""
        evidence = Evidence(
            description="User creation function",
            file_path="src/auth/users.py",
            line_numbers="45-72",
            code_snippet="def create_user(): pass",
        )
        assert evidence.description == "User creation function"
        assert evidence.file_path == "src/auth/users.py"
        assert evidence.line_numbers == "45-72"
        assert evidence.code_snippet == "def create_user(): pass"

    def test_evidence_missing_description(self):
        """Test Evidence fails without description."""
        with pytest.raises(ValidationError):
            Evidence()


class TestImplementationStatementModel:
    """Tests for the ImplementationStatement model."""

    def test_implementation_minimal(self):
        """Test ImplementationStatement with required fields."""
        impl = ImplementationStatement(
            control_id="ac-2",
            description="Account management implemented via admin interface.",
            implementation_status="implemented",
        )
        assert impl.control_id == "ac-2"
        assert impl.implementation_status == "implemented"
        assert impl.responsible_roles == ["System Administrator"]
        assert impl.evidence == []

    def test_implementation_full(self):
        """Test ImplementationStatement with all fields."""
        impl = ImplementationStatement(
            control_id="ac-2",
            description="Account management implemented via admin interface.",
            implementation_status="partial",
            responsible_roles=["Security Team", "DevOps"],
            evidence=[Evidence(description="Test evidence")],
            remarks="MFA pending implementation",
        )
        assert impl.implementation_status == "partial"
        assert len(impl.responsible_roles) == 2
        assert len(impl.evidence) == 1
        assert impl.remarks == "MFA pending implementation"

    def test_implementation_invalid_status(self):
        """Test ImplementationStatement fails with invalid status."""
        with pytest.raises(ValidationError):
            ImplementationStatement(
                control_id="ac-2",
                description="Test",
                implementation_status="invalid-status",
            )

    def test_implementation_valid_statuses(self):
        """Test all valid implementation statuses."""
        valid_statuses = ["implemented", "partial", "planned", "not-applicable"]
        for status in valid_statuses:
            impl = ImplementationStatement(
                control_id="ac-2",
                description="Test",
                implementation_status=status,
            )
            assert impl.implementation_status == status


class TestComponentDefinitionModel:
    """Tests for the ComponentDefinition model."""

    def test_component_minimal(self):
        """Test ComponentDefinition with required fields."""
        component = ComponentDefinition(
            component_id="my-app",
            title="My Application",
            description="A web application",
        )
        assert component.component_id == "my-app"
        assert component.title == "My Application"
        assert component.type == "software"  # default
        assert component.control_implementations == []

    def test_component_full(self):
        """Test ComponentDefinition with all fields."""
        component = ComponentDefinition(
            component_id="my-app",
            title="My Application",
            description="A web application",
            type="service",
            control_implementations=[
                ImplementationStatement(
                    control_id="ac-2",
                    description="Test implementation",
                    implementation_status="implemented",
                )
            ],
        )
        assert component.type == "service"
        assert len(component.control_implementations) == 1

    def test_component_valid_types(self):
        """Test all valid component types."""
        valid_types = ["software", "hardware", "service", "policy", "process"]
        for comp_type in valid_types:
            component = ComponentDefinition(
                component_id="test",
                title="Test",
                description="Test",
                type=comp_type,
            )
            assert component.type == comp_type

    def test_component_invalid_type(self):
        """Test ComponentDefinition fails with invalid type."""
        with pytest.raises(ValidationError):
            ComponentDefinition(
                component_id="test",
                title="Test",
                description="Test",
                type="invalid-type",
            )


class TestComplianceArtifactModel:
    """Tests for the ComplianceArtifact model."""

    def test_artifact_minimal(self):
        """Test ComplianceArtifact with required fields."""
        artifact = ComplianceArtifact(
            framework_id="fedramp-moderate",
            control_id="ac-2",
            component=ComponentDefinition(
                component_id="my-app",
                title="My Application",
                description="A web application",
            ),
        )
        assert artifact.framework_id == "fedramp-moderate"
        assert artifact.control_id == "ac-2"
        assert artifact.confidence == "medium"  # default

    def test_artifact_full(self):
        """Test ComplianceArtifact with all fields."""
        artifact = ComplianceArtifact(
            framework_id="fedramp-moderate",
            control_id="ac-2",
            component=ComponentDefinition(
                component_id="my-app",
                title="My Application",
                description="A web application",
                control_implementations=[
                    ImplementationStatement(
                        control_id="ac-2",
                        description="Account management implemented.",
                        implementation_status="implemented",
                        evidence=[
                            Evidence(
                                description="User CRUD operations",
                                file_path="src/users.py",
                            )
                        ],
                    )
                ],
            ),
            confidence="high",
        )
        assert artifact.confidence == "high"
        assert len(artifact.component.control_implementations) == 1

    def test_artifact_valid_confidence_levels(self):
        """Test all valid confidence levels."""
        valid_levels = ["high", "medium", "low"]
        for level in valid_levels:
            artifact = ComplianceArtifact(
                framework_id="test",
                control_id="ac-2",
                component=ComponentDefinition(
                    component_id="test",
                    title="Test",
                    description="Test",
                ),
                confidence=level,
            )
            assert artifact.confidence == level

    def test_artifact_invalid_confidence(self):
        """Test ComplianceArtifact fails with invalid confidence."""
        with pytest.raises(ValidationError):
            ComplianceArtifact(
                framework_id="test",
                control_id="ac-2",
                component=ComponentDefinition(
                    component_id="test",
                    title="Test",
                    description="Test",
                ),
                confidence="invalid",
            )

    def test_artifact_model_dump(self):
        """Test artifact serialization to dict."""
        artifact = ComplianceArtifact(
            framework_id="fedramp-moderate",
            control_id="ac-2",
            component=ComponentDefinition(
                component_id="my-app",
                title="My Application",
                description="A web application",
            ),
        )
        data = artifact.model_dump()
        assert data["framework_id"] == "fedramp-moderate"
        assert data["control_id"] == "ac-2"
        assert data["component"]["component_id"] == "my-app"


class TestArtifactValidationResultModel:
    """Tests for the ArtifactValidationResult model."""

    def test_validation_result_valid(self):
        """Test valid validation result."""
        result = ArtifactValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []
        assert result.warnings == []

    def test_validation_result_invalid(self):
        """Test invalid validation result."""
        result = ArtifactValidationResult(
            valid=False,
            errors=["Missing framework_id", "Missing control_id"],
            warnings=["No evidence provided"],
        )
        assert result.valid is False
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
